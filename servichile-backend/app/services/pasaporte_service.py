"""Casos de uso del Pasaporte de Confianza: perfil, verificación de RUT y score de arriendo.

Privacidad: el PDF de arriendo vive solo en la memoria de la petición. Del documento
solo se guarda el puntaje y la fecha de verificación.
"""
from app.domain.entidades import EstadoPasaporte, ResultadoDocumento, Usuario
from app.domain import xp as reglas_xp
from app.domain.pasaporte import (
    ExtraccionFallida,
    RutInvalido,
    estado_pasaporte,
    nivel_pasaporte,
    normalizar_rut,
    score_arriendo,
    score_confiabilidad,
)
from app.infrastructure.repositories import PasaporteRepository, ReservaRepository, UsuarioRepository
from app.infrastructure.verificacion import ExtractorFinanciero, VerificadorRut
from app.services.perfil_service import aplicar_perfil
from app.services.xp_service import XpService
from app.utils import ahora_utc

# 1 MB. Starlette guarda en disco temporal los archivos mayores a 1 MB, así que este límite
# mantiene el PDF en memoria durante todo el procesamiento.
DOCUMENTO_MAX_BYTES = 1024 * 1024
FIRMA_PDF = b"%PDF-"
# Selfie biométrica: se valida en memoria y se descarta; nunca se persiste.
BIOMETRIA_MAX_BYTES = 5 * 1024 * 1024
_FIRMAS_IMAGEN = (
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"RIFF", "webp"),  # RIFF....WEBP
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
)


class PasaporteError(Exception):
    """Error de negocio con mensaje para el usuario. La API lo traduce a un código HTTP."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class RutRechazado(PasaporteError):
    pass


class RutEnUso(PasaporteError):
    pass


class RutYaVerificado(PasaporteError):
    pass


class DocumentoInvalido(PasaporteError):
    pass


class DocumentoMuyGrande(PasaporteError):
    pass


class BiometriaInvalida(PasaporteError):
    pass


class BiometriaMuyGrande(PasaporteError):
    pass


class PasaporteService:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        reservas: ReservaRepository,
        pasaporte: PasaporteRepository,
        verificador: VerificadorRut,
        extractor: ExtractorFinanciero,
        xp: XpService | None = None,
    ) -> None:
        self.usuarios = usuarios
        self.reservas = reservas
        self.pasaporte = pasaporte
        self.verificador = verificador
        self.extractor = extractor
        self.xp = xp

    def estado(self, usuario: Usuario) -> EstadoPasaporte:
        """Nivel, score de confiabilidad y último resultado de arriendo del usuario."""
        conteo = self.reservas.contar_por_estado(usuario.id)
        arriendo = self.pasaporte.ultimo_arriendo(usuario.id)
        verificado = arriendo is not None and arriendo.estado == "verificado"
        xp = self.xp.total(usuario.id) if self.xp is not None else int(usuario.xp or 0)
        return EstadoPasaporte(
            rut_verificado=usuario.rut_verificado,
            telefono=usuario.telefono,
            nivel_pasaporte=nivel_pasaporte(verificado),
            estado_pasaporte=estado_pasaporte(arriendo.estado if arriendo else None),
            score_confiabilidad=score_confiabilidad(conteo.get("asistido", 0), conteo.get("no_show", 0)),
            arriendo=arriendo,
            edad=usuario.perfil.edad if usuario.perfil else None,
            tipo_cuenta=usuario.perfil.tipo_cuenta if usuario.perfil else None,
            biometria_verificada=usuario.biometria_verificada,
            biometria_verificada_en=usuario.biometria_verificada_en,
            xp=xp,
            nivel_xp=reglas_xp.nivel_por_xp(xp),
        )

    def actualizar_perfil(self, usuario: Usuario, cambios: dict) -> Usuario:
        """Aplica solo los campos recibidos. Un RUT se verifica antes de guardarse."""
        if "rut" in cambios:
            if cambios["rut"] is None:
                raise RutRechazado("El RUT no se puede borrar una vez enviado.")
            self._verificar_rut(usuario, cambios["rut"])
        if "telefono" in cambios:
            usuario.telefono = cambios["telefono"]
        aplicar_perfil(usuario, cambios)
        usuario = self.usuarios.guardar(usuario)
        if self.xp is not None:
            if usuario.rut_verificado:
                self.xp.por_rut(usuario.id)
            self.xp.por_perfil_basico(usuario)
            usuario.xp = self.xp.total(usuario.id)
        return usuario

    def _verificar_rut(self, usuario: Usuario, texto: str) -> None:
        try:
            rut = normalizar_rut(texto)
        except RutInvalido as error:
            raise RutRechazado(str(error)) from None
        if usuario.rut_verificado:
            if usuario.rut == rut:
                return
            raise RutYaVerificado("El RUT ya fue verificado y no se puede cambiar.")
        otro = self.usuarios.get_by_rut(rut)
        if otro is not None and otro.id != usuario.id:
            raise RutEnUso("Este RUT ya está registrado en otra cuenta.")
        if not self.verificador.existe_y_activo(rut):
            raise RutRechazado("No se pudo verificar el RUT.")
        usuario.rut = rut
        usuario.rut_verificado = True

    def procesar_documento(self, usuario: Usuario, contenido: bytes) -> ResultadoDocumento:
        """Lee el PDF en memoria, calcula el score de arriendo y guarda solo el resultado."""
        if len(contenido) > DOCUMENTO_MAX_BYTES:
            raise DocumentoMuyGrande("El documento supera el tamaño máximo de 1 MB.")
        if not contenido.startswith(FIRMA_PDF):
            raise DocumentoInvalido("El archivo debe ser un PDF.")
        try:
            metricas = self.extractor.extraer(contenido)
        except ExtraccionFallida:
            raise DocumentoInvalido("No se pudo leer el documento. Suba un PDF con texto, no una imagen.") from None

        arriendo = self.pasaporte.registrar_verificacion(
            usuario.id, estado="verificado", score=score_arriendo(metricas)
        )
        if self.xp is not None:
            self.xp.por_documento_arriendo(usuario.id)
        return ResultadoDocumento(
            estado_verificacion=arriendo.estado,
            score_financiero=arriendo.score,
            actualizado_en=arriendo.verificado_en or arriendo.creado_en,
        )

    def procesar_biometria(self, usuario: Usuario, contenido: bytes) -> Usuario:
        """Acepta cualquier imagen válida, marca biometría OK y descarta los bytes."""
        if len(contenido) > BIOMETRIA_MAX_BYTES:
            raise BiometriaMuyGrande("La foto supera el tamaño máximo de 5 MB.")
        if not self._parece_imagen(contenido):
            raise BiometriaInvalida("Suba una foto (JPEG, PNG, WebP o GIF).")
        # Zero-retention: no se guarda la imagen; solo el resultado.
        usuario.biometria_verificada = True
        usuario.biometria_verificada_en = ahora_utc()
        usuario = self.usuarios.guardar(usuario)
        if self.xp is not None:
            self.xp.por_biometria(usuario.id)
            usuario.xp = self.xp.total(usuario.id)
        return usuario

    def _parece_imagen(self, contenido: bytes) -> bool:
        if not contenido or len(contenido) < 12:
            return False
        for firma, tipo in _FIRMAS_IMAGEN:
            if contenido.startswith(firma):
                if tipo == "webp":
                    return contenido[8:12] == b"WEBP"
                return True
        return False
