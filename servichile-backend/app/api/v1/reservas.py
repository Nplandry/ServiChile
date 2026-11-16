import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.dependencias import (
    CurrentUserDep,
    PasaporteServiceDep,
    ReservaServiceDep,
)

from app.api.esquemas import CheckinIn, ReservaIn, ReservaOut

from app.dominio.errores import (
    NegocioNoEncontrado,
    NivelInsuficiente,
    NoEsTitularDelNegocio,
    ReservaNoEncontrada,
    ReservaYaCerrada,
)

router = APIRouter(prefix="/v1/reservas", tags=["Reservas"])

# Misma URL histórica bajo /v1/businesses… (titular); vive en el módulo de reservas.
titular_router = APIRouter(
    prefix="/v1/businesses", tags=["Reservas · titular"]
)

NO_ENCONTRADO = "Negocio no encontrado."
NO_TITULAR = "Solo el titular verificado del negocio puede registrar asistencias."
RESERVA_NO_ENCONTRADA = "Reserva no encontrada en este negocio."
RESERVA_CERRADA = "La reserva ya tiene asistencia o no-show registrado."


def _http_titular_reserva(exc: Exception) -> HTTPException:
    if isinstance(exc, NegocioNoEncontrado):
        return HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO)
    if isinstance(exc, NoEsTitularDelNegocio):
        return HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR)
    if isinstance(exc, ReservaNoEncontrada):
        return HTTPException(status.HTTP_404_NOT_FOUND, RESERVA_NO_ENCONTRADA)
    if isinstance(exc, ReservaYaCerrada):
        return HTTPException(status.HTTP_409_CONFLICT, RESERVA_CERRADA)
    raise exc


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


@titular_router.post("/{business_id}/checkin", response_model=ReservaOut)
def registrar_asistencia(
    business_id: uuid.UUID,
    datos: CheckinIn,
    usuario: CurrentUserDep,
    servicio: ReservaServiceDep,
):
    try:
        return servicio.registrar_asistencia(business_id, usuario.id, datos.qr_token)
    except (
        NegocioNoEncontrado,
        NoEsTitularDelNegocio,
        ReservaNoEncontrada,
        ReservaYaCerrada,
    ) as exc:
        raise _http_titular_reserva(exc) from None


@titular_router.post(
    "/{business_id}/reservas/{reserva_id}/no-show", response_model=ReservaOut
)
def registrar_no_show(
    business_id: uuid.UUID,
    reserva_id: uuid.UUID,
    usuario: CurrentUserDep,
    servicio: ReservaServiceDep,
):
    try:
        return servicio.registrar_no_show(business_id, usuario.id, reserva_id)
    except (
        NegocioNoEncontrado,
        NoEsTitularDelNegocio,
        ReservaNoEncontrada,
        ReservaYaCerrada,
    ) as exc:
        raise _http_titular_reserva(exc) from None
