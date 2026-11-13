"""Emisión y validación del carnet QR de identidad (Mi QR).

El QR no es el JWT de sesión: es un token firmado de corta vida con propósito
`mi_qr`. Cualquier usuario autenticado puede validar el QR de otra persona y
ver solo datos públicos de confianza (sin correo ni RUT).
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from urllib.parse import unquote

import jwt

from app.config import Settings
from app.domain.entidades import MiQrEmitido, MiQrValidado, Usuario
from app.infrastructure.repositories import UsuarioRepository
from app.services.pasaporte_service import PasaporteService
from app.utils import ahora_utc

_ALGORITHM = "HS256"
_PROPOSITO = "mi_qr"
_PREFIJO_PAYLOAD = "servichile://mi-qr/"


class MiQrInvalido(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class MiQrService:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        pasaporte: PasaporteService,
        settings: Settings,
    ) -> None:
        self.usuarios = usuarios
        self.pasaporte = pasaporte
        self.settings = settings

    def emitir(self, usuario: Usuario) -> MiQrEmitido:
        """Genera un payload escaneable y el carnet del titular autenticado."""
        ahora = ahora_utc()
        expira = timedelta(minutes=self.settings.mi_qr_expires_minutes)
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
        return MiQrEmitido(
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

    def validar(self, escaneado_por: Usuario, payload: str) -> MiQrValidado:
        """Valida un QR escaneado y devuelve el carnet público del titular."""
        token = self._extraer_token(payload)
        try:
            datos = jwt.decode(
                token,
                self.settings.jwt_secret.get_secret_value(),
                algorithms=[_ALGORITHM],
                options={"require": ["sub", "exp", "pur"]},
            )
        except jwt.ExpiredSignatureError as error:
            raise MiQrInvalido("Este QR ya expiró. Pida al titular que lo renueve.") from error
        except jwt.PyJWTError as error:
            raise MiQrInvalido("QR inválido o alterado.") from error

        if datos.get("pur") != _PROPOSITO:
            raise MiQrInvalido("Este código no es un carnet Mi QR de ServiChile.")

        try:
            titular_id = uuid.UUID(str(datos["sub"]))
        except (ValueError, TypeError) as error:
            raise MiQrInvalido("QR inválido o alterado.") from error

        titular = self.usuarios.get(titular_id)
        if titular is None or not titular.activo:
            raise MiQrInvalido("No se encontró al titular de este QR.")

        estado = self.pasaporte.estado(titular)
        expires_at = ahora_utc()
        exp = datos.get("exp")
        if isinstance(exp, (int, float)):
            from datetime import UTC, datetime

            expires_at = datetime.fromtimestamp(exp, tz=UTC)

        return MiQrValidado(
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
            raise MiQrInvalido("No se recibió ningún código QR.")
        if texto.startswith(_PREFIJO_PAYLOAD):
            return texto[len(_PREFIJO_PAYLOAD) :].strip()
        # Acepta el JWT crudo por si el lector no entrega el esquema URI.
        if texto.count(".") == 2:
            return texto
        raise MiQrInvalido("El código escaneado no es un Mi QR de ServiChile.")
