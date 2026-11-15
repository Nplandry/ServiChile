import secrets

import uuid

from app.domain.entidades import Reserva

from app.domain.errores import (
    NegocioNoEncontrado,
    NivelInsuficiente,
    NoEsTitularDelNegocio,
    ReservaNoEncontrada,
    ReservaYaCerrada,
)

from app.domain.puertos import RepositorioNegocios, RepositorioReservas

from app.services.progreso_cliente import XpService

__all__ = [
    "ReservaService",
    "ReservaNoEncontrada",
    "ReservaYaCerrada",
    "NoEsTitularDelNegocio",
    "NivelInsuficiente",
]


class ReservaService:

    def __init__(
        self,
        negocios: RepositorioNegocios,
        reservas: RepositorioReservas,
        xp: XpService | None = None,
    ) -> None:

        self.negocios = negocios

        self.reservas = reservas

        self.xp = xp

    def crear(
        self, usuario_id: uuid.UUID, business_id: uuid.UUID, nivel_usuario: int = 1
    ) -> Reserva:

        negocio = self.negocios.get(business_id)

        if negocio is None:

            raise NegocioNoEncontrado()

        pide = negocio.requiere_nivel or 1

        if pide > nivel_usuario:

            raise NivelInsuficiente(pide)

        return self.reservas.crear(usuario_id, business_id, secrets.token_urlsafe(24))

    def listar(self, usuario_id: uuid.UUID) -> list[Reserva]:

        return self.reservas.listar_por_usuario(usuario_id)

    def cancelar(self, usuario_id: uuid.UUID, reserva_id: uuid.UUID) -> Reserva:

        reserva = self.reservas.get(reserva_id)

        if reserva is None or reserva.usuario_id != usuario_id:

            raise ReservaNoEncontrada()

        return self._cerrar(reserva, "cancelada")

    def registrar_asistencia(
        self, business_id: uuid.UUID, usuario_id: uuid.UUID, qr_token: str
    ) -> Reserva:

        self._verificar_titular(business_id, usuario_id)

        reserva = self.reservas.get_por_qr(business_id, qr_token)

        if reserva is None:

            raise ReservaNoEncontrada()

        return self._cerrar(reserva, "asistido")

    def registrar_no_show(
        self, business_id: uuid.UUID, usuario_id: uuid.UUID, reserva_id: uuid.UUID
    ) -> Reserva:

        self._verificar_titular(business_id, usuario_id)

        reserva = self.reservas.get(reserva_id)

        if reserva is None or reserva.business_id != business_id:

            raise ReservaNoEncontrada()

        return self._cerrar(reserva, "no_show")

    def _verificar_titular(self, business_id: uuid.UUID, usuario_id: uuid.UUID) -> None:

        negocio = self.negocios.get(business_id)

        if negocio is None:

            raise NegocioNoEncontrado()

        if not negocio.is_claimed or negocio.reclamado_por != usuario_id:

            raise NoEsTitularDelNegocio()

    def _cerrar(self, reserva: Reserva, estado: str) -> Reserva:

        if reserva.estado != "reservada":

            raise ReservaYaCerrada()

        reserva.estado = estado

        reserva = self.reservas.guardar(reserva)

        if estado == "asistido" and self.xp is not None:

            self.xp.por_asistencia(reserva.usuario_id, reserva.id)

        return reserva
