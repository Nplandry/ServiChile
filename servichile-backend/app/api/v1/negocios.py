import uuid

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.authz import exige_cuenta_proveedor

from app.api.deps import CurrentUserDep, NegocioServiceDep, ReservaServiceDep

from app.api.schemas import (
    CheckinIn,
    ClaimIn,
    ClaimOut,
    NegocioCrearIn,
    NegocioEnMapaOut,
    ReputacionOut,
    ReservaOut,
)

from app.domain.errores import (
    NegocioNoEncontrado,
    NegocioYaReclamado,
    NoEsTitularDelNegocio,
    ReservaNoEncontrada,
    ReservaYaCerrada,
)

router = APIRouter(prefix="/v1/businesses", tags=["Negocios"])

CategoriaQuery = Annotated[str | None, Query(max_length=30)]

BusquedaQuery = Annotated[str | None, Query(max_length=120)]

NO_ENCONTRADO = "Negocio no encontrado."

YA_RECLAMADO = (
    "Este perfil ya fue reclamado por otro titular. Contacte a soporte si es un error."
)

NO_TITULAR = "Solo el titular verificado del negocio puede registrar asistencias."

NO_TITULAR_LIBERAR = "Solo el titular de la empresa puede quitarla de su perfil."

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


@router.get("", response_model=list[NegocioEnMapaOut])
def listar(
    servicio: NegocioServiceDep,
    categoria: CategoriaQuery = None,
    q: BusquedaQuery = None,
):

    return servicio.listar_para_mapa(categoria, q)


@router.get("/mias", response_model=list[NegocioEnMapaOut])
def listar_mias(usuario: CurrentUserDep, servicio: NegocioServiceDep):

    return servicio.listar_mios(usuario.id)


@router.post("", response_model=NegocioEnMapaOut, status_code=status.HTTP_201_CREATED)
def crear(datos: NegocioCrearIn, usuario: CurrentUserDep, servicio: NegocioServiceDep):

    exige_cuenta_proveedor(usuario)

    return servicio.crear(
        usuario.id,
        nombre=datos.nombre,
        categoria=datos.categoria,
        direccion=datos.direccion,
        descripcion=datos.descripcion,
        telefono=datos.telefono,
        sitio_web=datos.sitio_web,
        imagen_url=datos.imagen_url,
        logo_url=datos.logo_url,
        documento_verificacion=datos.documento_verificacion,
    )


@router.get("/{business_id}/reputation", response_model=ReputacionOut)
def reputacion(business_id: uuid.UUID, servicio: NegocioServiceDep):

    try:

        return servicio.obtener_reputacion(business_id)

    except NegocioNoEncontrado:

        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None


@router.post("/{business_id}/ciber-scan", response_model=ReputacionOut)
def escanear_ciber(
    business_id: uuid.UUID, usuario: CurrentUserDep, servicio: NegocioServiceDep
):

    try:

        return servicio.escanear_ciber(business_id, usuario.id)

    except NegocioNoEncontrado:

        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None

    except NoEsTitularDelNegocio:

        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR_LIBERAR) from None


@router.post(
    "/{business_id}/claim", response_model=ClaimOut, status_code=status.HTTP_201_CREATED
)
def reclamar(
    business_id: uuid.UUID,
    datos: ClaimIn,
    usuario: CurrentUserDep,
    servicio: NegocioServiceDep,
):

    exige_cuenta_proveedor(usuario)

    try:

        return servicio.reclamar(
            business_id,
            usuario.id,
            datos.nombre,
            datos.telefono,
            datos.sitio_web,
            documento_verificacion=datos.documento_verificacion,
        )

    except NegocioNoEncontrado:

        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None

    except NegocioYaReclamado:

        raise HTTPException(status.HTTP_409_CONFLICT, YA_RECLAMADO) from None


@router.delete("/{business_id}/claim", status_code=status.HTTP_204_NO_CONTENT)
def liberar(
    business_id: uuid.UUID, usuario: CurrentUserDep, servicio: NegocioServiceDep
):

    try:

        servicio.liberar(business_id, usuario.id)

    except NegocioNoEncontrado:

        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None

    except NoEsTitularDelNegocio:

        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR_LIBERAR) from None


@router.post("/{business_id}/checkin", response_model=ReservaOut)
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


@router.post("/{business_id}/reservas/{reserva_id}/no-show", response_model=ReservaOut)
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
