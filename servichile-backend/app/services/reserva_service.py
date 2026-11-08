"""Reservas de cupo (nivel 1 del Pasaporte).

El usuario reserva y recibe un código QR. Solo el dueño verificado de un comercio puede
marcar asistencia o no-show en sus reservas. Un comercio sin reclamar no tiene quien
registre asistencia.
"""
import secrets
import uuid

from app.domain.entidades import Reserva
from app.infrastructure.repositories import NegocioRepository, ReservaRepository
from app.services.negocio_service import NegocioNoEncontrado


class ReservaNoEncontrada(Exception):
    pass


class ReservaYaCerrada(Exception):
    pass


class NoEsTitularDelNegocio(Exception):
    pass


class ReservaService:
    def __init__(self, negocios: NegocioRepository, reservas: ReservaRepository) -> None:
        self.negocios = negocios
        self.reservas = reservas

    def crear(self, usuario_id: uuid.UUID, business_id: uuid.UUID) -> Reserva:
        if self.negocios.get(business_id) is None:
            raise NegocioNoEncontrado()
        # El token del QR lo genera el servicio (regla de negocio); el repositorio persiste.
        return self.reservas.crear(usuario_id, business_id, secrets.token_urlsafe(24))

    def listar(self, usuario_id: uuid.UUID) -> list[Reserva]:
        return self.reservas.listar_por_usuario(usuario_id)

    def registrar_asistencia(self, business_id: uuid.UUID, usuario_id: uuid.UUID, qr_token: str) -> Reserva:
        self._verificar_titular(business_id, usuario_id)
        reserva = self.reservas.get_por_qr(business_id, qr_token)
        if reserva is None:
            raise ReservaNoEncontrada()
        return self._cerrar(reserva, "asistido")

    def registrar_no_show(self, business_id: uuid.UUID, usuario_id: uuid.UUID, reserva_id: uuid.UUID) -> Reserva:
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
        return self.reservas.guardar(reserva)
