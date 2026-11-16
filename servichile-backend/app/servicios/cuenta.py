from app.dominio.entidades import Usuario
from app.dominio.errores import ContrasenaIncorrecta
from app.dominio.puertos import (
    AlmacenamientoBiometria,
    AlmacenamientoCedula,
    HasherContrasena,
    RepositorioUsuarios,
)
from app.servicios.negocio import NegocioService

__all__ = ["CuentaService", "ContrasenaIncorrecta"]


class CuentaService:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        negocios: NegocioService,
        hasher: HasherContrasena,
        biometria: AlmacenamientoBiometria | None = None,
        cedula: AlmacenamientoCedula | None = None,
    ) -> None:
        self.usuarios = usuarios
        self.negocios = negocios
        self.hasher = hasher
        self.biometria = biometria
        self.cedula = cedula

    def eliminar(self, usuario: Usuario, password: str) -> None:
        if not self.hasher.verificar(usuario.password_hash, password):
            raise ContrasenaIncorrecta()
        if self.biometria is not None:
            self.biometria.eliminar(usuario.id, usuario.biometria_ruta)
        if self.cedula is not None:
            self.cedula.eliminar(usuario.id, usuario.cedula_ruta)
        self.negocios.eliminar_todos_del_usuario(usuario.id)
        self.usuarios.eliminar(usuario.id)
