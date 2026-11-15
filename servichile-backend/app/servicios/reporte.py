from __future__ import annotations

from urllib.parse import unquote

from app.dominio.entidades import ReporteEmitido, ReporteValidado, Usuario
from app.dominio.errores import ReporteInvalido
from app.dominio.puertos import EmisorReporte, RepositorioUsuarios
from app.servicios.pasaporte import PasaporteService

_PREFIJO_PAYLOAD = "servichile://reporte/"


class ReporteService:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        pasaporte: PasaporteService,
        emisor: EmisorReporte,
    ) -> None:
        self.usuarios = usuarios
        self.pasaporte = pasaporte
        self.emisor = emisor

    def emitir(self, usuario: Usuario) -> ReporteEmitido:
        firmado = self.emisor.emitir(usuario.id)
        estado = self.pasaporte.estado(usuario)
        return ReporteEmitido(
            payload=_PREFIJO_PAYLOAD + firmado.token,
            token=firmado.token,
            expires_in=firmado.expires_in,
            expires_at=firmado.expires_at,
            nombre=usuario.nombre,
            email=usuario.email,
            nivel_pasaporte=estado.nivel_pasaporte,
            estado_pasaporte=estado.estado_pasaporte,
            score_confiabilidad=estado.score_confiabilidad,
            rut_verificado=estado.rut_verificado,
            xp=estado.xp,
            nivel_xp=estado.nivel_xp,
            tipo_cuenta=estado.tipo_cuenta,
            antecedentes_verificados=estado.antecedentes_verificados,
            antecedentes_anotaciones=estado.antecedentes_anotaciones,
        )

    def validar(self, escaneado_por: Usuario, payload: str) -> ReporteValidado:
        leido = self.emisor.leer(self._extraer_token(payload))
        titular = self.usuarios.get(leido.usuario_id)
        if titular is None or not titular.activo:
            raise ReporteInvalido("No se encontró al titular de este reporte.")
        estado = self.pasaporte.estado(titular)
        return ReporteValidado(
            es_propio=titular.id == escaneado_por.id,
            nombre=titular.nombre,
            nivel_pasaporte=estado.nivel_pasaporte,
            estado_pasaporte=estado.estado_pasaporte,
            score_confiabilidad=estado.score_confiabilidad,
            rut_verificado=estado.rut_verificado,
            expires_at=leido.expires_at,
            xp=estado.xp,
            nivel_xp=estado.nivel_xp,
            tipo_cuenta=estado.tipo_cuenta,
            antecedentes_verificados=estado.antecedentes_verificados,
            antecedentes_anotaciones=estado.antecedentes_anotaciones,
        )

    def _extraer_token(self, payload: str) -> str:
        texto = unquote((payload or "").strip())
        if not texto:
            raise ReporteInvalido("No se recibió ningún código QR de reporte.")
        if texto.startswith(_PREFIJO_PAYLOAD):
            return texto[len(_PREFIJO_PAYLOAD) :].strip()
        if texto.count(".") == 2:
            return texto
        raise ReporteInvalido(
            "El código escaneado no es un QR de reporte de ServiChile."
        )
