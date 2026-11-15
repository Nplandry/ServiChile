from __future__ import annotations

import uuid

from datetime import timedelta

import jwt

from argon2 import PasswordHasher

from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import Settings

from app.domain.entidades import TokenEmitido, Usuario

from app.infrastructure.repositories import UsuarioRepository

from app.services.perfil_service import aplicar_perfil

from app.services.xp_service import XpService

from app.utils import ahora_utc

_hasher = PasswordHasher()

_DUMMY_HASH = _hasher.hash("servichile-dummy-password")

_ALGORITHM = "HS256"


class EmailYaRegistrado(Exception):

    pass


class CredencialesInvalidas(Exception):

    pass


def verificar_contrasena(password_hash: str, password: str) -> bool:

    try:

        _hasher.verify(password_hash, password)

    except (VerifyMismatchError, InvalidHashError):

        return False

    return True


class AuthService:

    def __init__(
        self,
        usuarios: UsuarioRepository,
        settings: Settings,
        xp: XpService | None = None,
    ) -> None:

        self.usuarios = usuarios

        self.settings = settings

        self.xp = xp

    def registrar(
        self, email: str, nombre: str, password: str, perfil: dict | None
    ) -> Usuario:

        email = email.lower()

        if self.usuarios.get_by_email(email):

            raise EmailYaRegistrado()

        usuario = self.usuarios.crear(email, nombre, _hasher.hash(password))

        if perfil:

            aplicar_perfil(usuario, perfil)

        usuario = self.usuarios.guardar(usuario)

        if self.xp is not None:

            self.xp.por_registro(usuario.id)

            self.xp.por_perfil_basico(usuario)

            usuario.xp = self.xp.total(usuario.id)

        return usuario

    def login(self, email: str, password: str) -> TokenEmitido:

        usuario = self.usuarios.get_by_email(email.lower())

        try:

            _hasher.verify(usuario.password_hash if usuario else _DUMMY_HASH, password)

        except (VerifyMismatchError, InvalidHashError):

            raise CredencialesInvalidas() from None

        if not usuario or not usuario.activo:

            raise CredencialesInvalidas()

        return self._emitir_token(usuario)

    def usuario_desde_token(self, token: str) -> Usuario:

        try:

            payload = jwt.decode(
                token,
                self.settings.jwt_secret.get_secret_value(),
                algorithms=[_ALGORITHM],
                options={"require": ["sub", "exp"]},
            )

            usuario = self.usuarios.get(uuid.UUID(payload["sub"]))

        except (jwt.PyJWTError, ValueError):

            raise CredencialesInvalidas() from None

        if not usuario or not usuario.activo:

            raise CredencialesInvalidas()

        return usuario

    def _emitir_token(self, usuario: Usuario) -> TokenEmitido:

        expira = timedelta(minutes=self.settings.jwt_expires_minutes)

        ahora = ahora_utc()

        token = jwt.encode(
            {"sub": str(usuario.id), "iat": ahora, "exp": ahora + expira},
            self.settings.jwt_secret.get_secret_value(),
            algorithm=_ALGORITHM,
        )

        return TokenEmitido(access_token=token, expires_in=int(expira.total_seconds()))
