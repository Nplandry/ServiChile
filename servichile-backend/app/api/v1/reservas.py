import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.dependencias import CurrentUserDep, PasaporteServiceDep, ReservaServiceDep

from app.api.esquemas import ReservaIn, ReservaOut

from app.dominio.errores import (
    NegocioNoEncontrado,
    NivelInsuficiente,
    ReservaNoEncontrada,
    ReservaYaCerrada,
)

router = APIRouter(prefix="/v1/reservas", tags=["Reservas"])


@router.post("", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
def crear_reserva(
    datos: ReservaIn,
    usuario: CurrentUserDep,
    servicio: ReservaServiceDep,
    pasaporte: PasaporteServiceDep,
):

    nivel = pasaporte.estado(usuario).nivel_pasaporte

    try:

        return servicio.crear(usuario.id, datos.business_id, nivel)

    except NegocioNoEncontrado:

        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Negocio no encontrado."
        ) from None

    except NivelInsuficiente as e:

        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Este lugar pide nivel {e.requiere}. Suba su nivel de confianza para continuar.",
        ) from None


@router.get("", response_model=list[ReservaOut])
def listar_reservas(usuario: CurrentUserDep, servicio: ReservaServiceDep):

    return servicio.listar(usuario.id)


@router.delete("/{reserva_id}", response_model=ReservaOut)
def cancelar_reserva(
    reserva_id: uuid.UUID, usuario: CurrentUserDep, servicio: ReservaServiceDep
):

    try:

        return servicio.cancelar(usuario.id, reserva_id)

    except ReservaNoEncontrada:

        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Reserva no encontrada."
        ) from None

    except ReservaYaCerrada:

        raise HTTPException(
            status.HTTP_409_CONFLICT, "La reserva ya no está activa."
        ) from None
