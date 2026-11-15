from app.dominio.entidades import Usuario
from app.dominio.errores import ContrasenaIncorrecta
from app.dominio.puertos import HasherContrasena, RepositorioUsuarios
from app.servicios.negocio import NegocioService

__all__ = ["CuentaService", "ContrasenaIncorrecta"]


class CuentaService:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        negocios: NegocioService,
        hasher: HasherContrasena,
    ) -> None:
        self.usuarios = usuarios
        self.negocios = negocios
        self.hasher = hasher

    def eliminar(self, usuario: Usuario, password: str) -> None:
        if not self.hasher.verificar(usuario.password_hash, password):
            raise ContrasenaIncorrecta()
        self.negocios.liberar_todos_del_usuario(usuario.id)
        self.usuarios.eliminar(usuario.id)
