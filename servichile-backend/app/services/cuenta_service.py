"""Casos de uso de la cuenta del usuario: eliminarla."""
from app.domain.entidades import Usuario
from app.infrastructure.repositories import NegocioRepository, UsuarioRepository
from app.services.auth_service import verificar_contrasena
from app.services.negocio_service import recalcular_score


class ContrasenaIncorrecta(Exception):
    pass


class CuentaService:
    def __init__(self, usuarios: UsuarioRepository, negocios: NegocioRepository) -> None:
        self.usuarios = usuarios
        self.negocios = negocios

    def eliminar(self, usuario: Usuario, password: str) -> None:
        """Borra la cuenta y sus datos. Los negocios que reclamó vuelven a quedar sin reclamar."""
        if not verificar_contrasena(usuario.password_hash, password):
            raise ContrasenaIncorrecta()
        for negocio in self.negocios.listar_reclamados_por(usuario.id):
            negocio.is_claimed = False
            negocio.reclamado_por = None
            if negocio.metricas is not None:
                negocio.metricas.is_verified_profile = False
                negocio.metricas.final_score = recalcular_score(negocio.metricas)
            self.negocios.guardar(negocio)
        self.usuarios.eliminar(usuario.id)
