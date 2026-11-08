"""Casos de uso del Pasaporte de Confianza: perfil, verificación de RUT y score de arriendo.

Privacidad: el PDF de arriendo vive solo en la memoria de la petición. Del documento
solo se guarda el puntaje y la fecha de verificación.
"""
from app.domain.entidades import EstadoPasaporte, ResultadoDocumento, Usuario
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

# 1 MB. Starlette guarda en disco temporal los archivos mayores a 1 MB, así que este límite
# mantiene el PDF en memoria durante todo el procesamiento.
DOCUMENTO_MAX_BYTES = 1024 * 1024
FIRMA_PDF = b"%PDF-"


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


class PasaporteService:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        reservas: ReservaRepository,
        pasaporte: PasaporteRepository,
        verificador: VerificadorRut,
        extractor: ExtractorFinanciero,
    ) -> None:
        self.usuarios = usuarios
        self.reservas = reservas
        self.pasaporte = pasaporte
        self.verificador = verificador
        self.extractor = extractor

    def estado(self, usuario: Usuario) -> EstadoPasaporte:
        """Nivel, score de confiabilidad y último resultado de arriendo del usuario."""
        conteo = self.reservas.contar_por_estado(usuario.id)
        arriendo = self.pasaporte.ultimo_arriendo(usuario.id)
        verificado = arriendo is not None and arriendo.estado == "verificado"
        return EstadoPasaporte(
            rut_verificado=usuario.rut_verificado,
            telefono=usuario.telefono,
            nivel_pasaporte=nivel_pasaporte(verificado),
            estado_pasaporte=estado_pasaporte(arriendo.estado if arriendo else None),
            score_confiabilidad=score_confiabilidad(conteo.get("asistido", 0), conteo.get("no_show", 0)),
            arriendo=arriendo,
            edad=usuario.perfil.edad if usuario.perfil else None,
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
        return self.usuarios.guardar(usuario)

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
        return ResultadoDocumento(
            estado_verificacion=arriendo.estado,
            score_financiero=arriendo.score,
            actualizado_en=arriendo.verificado_en or arriendo.creado_en,
        )
