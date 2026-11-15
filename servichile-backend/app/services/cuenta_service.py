from app.domain.entidades import Usuario

from app.domain.errores import ContrasenaIncorrecta

from app.infrastructure.repositories import UsuarioRepository

from app.services.auth_service import verificar_contrasena

from app.services.negocio_service import NegocioService

__all__ = ["CuentaService", "ContrasenaIncorrecta"]


class CuentaService:

    def __init__(self, usuarios: UsuarioRepository, negocios: NegocioService) -> None:

        self.usuarios = usuarios

        self.negocios = negocios

    def eliminar(self, usuario: Usuario, password: str) -> None:

        if not verificar_contrasena(usuario.password_hash, password):

            raise ContrasenaIncorrecta()

        self.negocios.liberar_todos_del_usuario(usuario.id)

        self.usuarios.eliminar(usuario.id)
