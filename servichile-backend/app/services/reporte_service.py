from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote

import jwt

from app.config import Settings
from app.domain.entidades import ReporteEmitido, ReporteValidado, Usuario
from app.infrastructure.repositories import UsuarioRepository
from app.services.pasaporte_service import PasaporteService
from app.utils import ahora_utc

_ALGORITHM = "HS256"
_PROPOSITO = "reporte"
_PREFIJO_PAYLOAD = "servichile://reporte/"


class ReporteInvalido(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class ReporteService:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        pasaporte: PasaporteService,
        settings: Settings,
    ) -> None:
        self.usuarios = usuarios
        self.pasaporte = pasaporte
        self.settings = settings

    def emitir(self, usuario: Usuario) -> ReporteEmitido:
        ahora = ahora_utc()
        expira = timedelta(minutes=self.settings.reporte_expires_minutes)
        expires_at = ahora + expira
        token = jwt.encode(
            {
                "sub": str(usuario.id),
                "pur": _PROPOSITO,
                "iat": ahora,
                "exp": expires_at,
            },
            self.settings.jwt_secret.get_secret_value(),
            algorithm=_ALGORITHM,
        )
        estado = self.pasaporte.estado(usuario)
        return ReporteEmitido(
            payload=_PREFIJO_PAYLOAD + token,
            token=token,
            expires_in=int(expira.total_seconds()),
            expires_at=expires_at,
            nombre=usuario.nombre,
            email=usuario.email,
            nivel_pasaporte=estado.nivel_pasaporte,
            estado_pasaporte=estado.estado_pasaporte,
            score_confiabilidad=estado.score_confiabilidad,
            rut_verificado=estado.rut_verificado,
            xp=estado.xp,
            nivel_xp=estado.nivel_xp,
            tipo_cuenta=estado.tipo_cuenta,
        )

    def validar(self, escaneado_por: Usuario, payload: str) -> ReporteValidado:
        token = self._extraer_token(payload)
        try:
            datos = jwt.decode(
                token,
                self.settings.jwt_secret.get_secret_value(),
                algorithms=[_ALGORITHM],
                options={"require": ["sub", "exp", "pur"]},
            )
        except jwt.ExpiredSignatureError as error:
            raise ReporteInvalido(
                "Este QR del reporte ya expiró. Pida al titular que lo renueve."
            ) from error
        except jwt.PyJWTError as error:
            raise ReporteInvalido("QR de reporte inválido o alterado.") from error
        if datos.get("pur") != _PROPOSITO:
            raise ReporteInvalido("Este código no es un reporte firmado de ServiChile.")
        try:
            titular_id = uuid.UUID(str(datos["sub"]))
        except (ValueError, TypeError) as error:
            raise ReporteInvalido("QR de reporte inválido o alterado.") from error
        titular = self.usuarios.get(titular_id)
        if titular is None or not titular.activo:
            raise ReporteInvalido("No se encontró al titular de este reporte.")
        estado = self.pasaporte.estado(titular)
        expires_at = ahora_utc()
        exp = datos.get("exp")
        if isinstance(exp, (int, float)):
            expires_at = datetime.fromtimestamp(exp, tz=UTC)
        return ReporteValidado(
            es_propio=titular.id == escaneado_por.id,
            nombre=titular.nombre,
            nivel_pasaporte=estado.nivel_pasaporte,
            estado_pasaporte=estado.estado_pasaporte,
            score_confiabilidad=estado.score_confiabilidad,
            rut_verificado=estado.rut_verificado,
            expires_at=expires_at,
            xp=estado.xp,
            nivel_xp=estado.nivel_xp,
            tipo_cuenta=estado.tipo_cuenta,
        )

    def _extraer_token(self, payload: str) -> str:
        texto = unquote((payload or "").strip())
        if not texto:
            raise ReporteInvalido("No se recibió ningún código QR de reporte.")
        if texto.startswith(_PREFIJO_PAYLOAD):
            return texto[len(_PREFIJO_PAYLOAD) :].strip()
        if texto.count(".") == 2:
            return texto
        raise ReporteInvalido("El código escaneado no es un QR de reporte de ServiChile.")
