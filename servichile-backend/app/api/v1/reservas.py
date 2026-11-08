"""Reservas de cupo del usuario autenticado. Alimentan el score de confiabilidad (nivel 1)."""
import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, ReservaServiceDep
from app.api.schemas import ReservaIn, ReservaOut
from app.services.negocio_service import NegocioNoEncontrado
from app.services.reserva_service import ReservaNoEncontrada, ReservaYaCerrada

router = APIRouter(prefix="/v1/reservas", tags=["Reservas"])


@router.post("", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
def crear_reserva(datos: ReservaIn, usuario: CurrentUserDep, servicio: ReservaServiceDep):
    """Reserva un cupo y devuelve el código QR que el usuario muestra en el comercio."""
    try:
        return servicio.crear(usuario.id, datos.business_id)
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Negocio no encontrado.") from None


@router.get("", response_model=list[ReservaOut])
def listar_reservas(usuario: CurrentUserDep, servicio: ReservaServiceDep):
    return servicio.listar(usuario.id)


@router.delete("/{reserva_id}", response_model=ReservaOut)
def cancelar_reserva(reserva_id: uuid.UUID, usuario: CurrentUserDep, servicio: ReservaServiceDep):
    """Cancela una reserva propia que todavía está activa."""
    try:
        return servicio.cancelar(usuario.id, reserva_id)
    except ReservaNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reserva no encontrada.") from None
    except ReservaYaCerrada:
        raise HTTPException(status.HTTP_409_CONFLICT, "La reserva ya no está activa.") from None
