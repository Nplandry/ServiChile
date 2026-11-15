from __future__ import annotations

import uuid

from app.dominio.entidades import TokenEmitido, Usuario
from app.dominio.errores import CredencialesInvalidas, EmailYaRegistrado
from app.dominio.puertos import EmisorSesion, HasherContrasena, RepositorioUsuarios
from app.servicios.perfil import aplicar_perfil
from app.servicios.progreso_cliente import XpService


class AuthService:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        hasher: HasherContrasena,
        sesion: EmisorSesion,
        xp: XpService | None = None,
    ) -> None:
        self.usuarios = usuarios
        self.hasher = hasher
        self.sesion = sesion
        self.xp = xp

    def registrar(
        self, email: str, nombre: str, password: str, perfil: dict | None
    ) -> Usuario:
        email = email.lower()
        if self.usuarios.get_by_email(email):
            raise EmailYaRegistrado()
        usuario = self.usuarios.crear(email, nombre, self.hasher.hash(password))
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
        if not self.hasher.verificar(
            usuario.password_hash if usuario else None, password
        ):
            raise CredencialesInvalidas()
        if not usuario or not usuario.activo:
            raise CredencialesInvalidas()
        return self.sesion.emitir(usuario.id)

    def usuario_desde_token(self, token: str) -> Usuario:
        try:
            usuario = self.usuarios.get(self.sesion.sujeto(token))
        except ValueError as error:
            raise CredencialesInvalidas() from error
        if not usuario or not usuario.activo:
            raise CredencialesInvalidas()
        return usuario
