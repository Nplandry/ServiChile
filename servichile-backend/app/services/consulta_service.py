"""Casos de uso del historial de consultas del usuario."""
import uuid

from app.domain.entidades import Consulta
from app.infrastructure.repositories import ConsultaRepository


class ConsultaService:
    def __init__(self, consultas: ConsultaRepository) -> None:
        self.consultas = consultas

    def historial(self, usuario_id: uuid.UUID, limite: int) -> list[Consulta]:
        return self.consultas.listar_por_usuario(usuario_id, limite)
