"""Reservas de cupo del usuario autenticado. Alimentan el score de confiabilidad (nivel 1)."""
from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, ReservaServiceDep
from app.api.schemas import ReservaIn, ReservaOut
from app.services.negocio_service import NegocioNoEncontrado

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
