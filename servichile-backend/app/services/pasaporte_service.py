"""Casos de uso del Pasaporte de Confianza: perfil, RUT y biometría."""
from app.domain.entidades import EstadoPasaporte, Usuario
from app.domain import xp as reglas_xp
from app.domain.pasaporte import (
    RutInvalido,
    estado_pasaporte,
    nivel_pasaporte,
    normalizar_rut,
    score_confiabilidad,
)
from app.infrastructure.repositories import ReservaRepository, UsuarioRepository
from app.infrastructure.verificacion import VerificadorRut
from app.services.perfil_service import aplicar_perfil
from app.services.xp_service import XpService
from app.utils import ahora_utc

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


class BiometriaInvalida(PasaporteError):
    pass


class BiometriaMuyGrande(PasaporteError):
    pass


class PasaporteService:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        reservas: ReservaRepository,
        verificador: VerificadorRut,
        xp: XpService | None = None,
    ) -> None:
        self.usuarios = usuarios
        self.reservas = reservas
        self.verificador = verificador
        self.xp = xp

    def estado(self, usuario: Usuario) -> EstadoPasaporte:
        """Nivel, score de confiabilidad y flags de identidad del usuario."""
        conteo = self.reservas.contar_por_estado(usuario.id)
        xp = self.xp.total(usuario.id) if self.xp is not None else int(usuario.xp or 0)
        return EstadoPasaporte(
            rut_verificado=usuario.rut_verificado,
            telefono=usuario.telefono,
            nivel_pasaporte=nivel_pasaporte(),
            estado_pasaporte=estado_pasaporte(usuario.rut_verificado),
            score_confiabilidad=score_confiabilidad(conteo.get("asistido", 0), conteo.get("no_show", 0)),
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
