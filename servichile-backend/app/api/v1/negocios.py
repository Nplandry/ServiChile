"""Endpoints del Índice de Transparencia de negocios.

GET /v1/businesses/{id}/reputation es público: devuelve solo indicadores
estadísticos agregados y el índice algorítmico, nunca textos de reseñas.
POST /v1/businesses/{id}/claim requiere sesión: el dueño reclama su perfil.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

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
from app.services.negocio_service import (
    NegocioNoEncontrado,
    NegocioYaReclamado,
    NoEsTitularDelNegocio as NegocioNoEsTitular,
)
from app.services.reserva_service import (
    NoEsTitularDelNegocio,
    ReservaNoEncontrada,
    ReservaYaCerrada,
)

router = APIRouter(prefix="/v1/businesses", tags=["Negocios"])

CategoriaQuery = Annotated[str | None, Query(max_length=30)]
BusquedaQuery = Annotated[str | None, Query(max_length=120)]

NO_ENCONTRADO = "Negocio no encontrado."
YA_RECLAMADO = "Este perfil ya fue reclamado por otro titular. Contacte a soporte si es un error."
NO_TITULAR = "Solo el titular verificado del negocio puede registrar asistencias."
NO_TITULAR_LIBERAR = "Solo el titular de la empresa puede quitarla de su perfil."
SOLO_EMPRESA = "Solo una cuenta empresa puede crear o reclamar fichas en el marketplace."
RESERVA_NO_ENCONTRADA = "Reserva no encontrada en este negocio."
RESERVA_CERRADA = "La reserva ya tiene asistencia o no-show registrado."


def _exige_cuenta_empresa(usuario) -> None:
    tipo = usuario.perfil.tipo_cuenta if usuario.perfil else None
    if tipo != "empresa":
        raise HTTPException(status.HTTP_403_FORBIDDEN, SOLO_EMPRESA)


@router.get("", response_model=list[NegocioEnMapaOut])
def listar(servicio: NegocioServiceDep, categoria: CategoriaQuery = None, q: BusquedaQuery = None):
    """Negocios del marketplace geolocalizado. Público. Filtra por categoría y texto."""
    return servicio.listar_para_mapa(categoria, q)


@router.get("/mias", response_model=list[NegocioEnMapaOut])
def listar_mias(usuario: CurrentUserDep, servicio: NegocioServiceDep):
    """Empresas reclamadas por el usuario autenticado."""
    return servicio.listar_mios(usuario.id)


@router.post("", response_model=NegocioEnMapaOut, status_code=status.HTTP_201_CREATED)
def crear(datos: NegocioCrearIn, usuario: CurrentUserDep, servicio: NegocioServiceDep):
    """Crea una empresa nueva en el marketplace y la reclama automáticamente."""
    _exige_cuenta_empresa(usuario)
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
    )


@router.get("/{business_id}/reputation", response_model=ReputacionOut)
def reputacion(business_id: uuid.UUID, servicio: NegocioServiceDep):
    """Indicadores estadísticos e Índice de Transparencia. Acceso público."""
    try:
        return servicio.obtener_reputacion(business_id)
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None


@router.post("/{business_id}/claim", response_model=ClaimOut, status_code=status.HTTP_201_CREATED)
def reclamar(
    business_id: uuid.UUID,
    datos: ClaimIn,
    usuario: CurrentUserDep,
    servicio: NegocioServiceDep,
):
    """Derecho a Réplica: el dueño reclama y verifica su perfil. Requiere sesión empresa."""
    _exige_cuenta_empresa(usuario)
    try:
        return servicio.reclamar(business_id, usuario.id, datos.nombre, datos.telefono, datos.sitio_web)
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NegocioYaReclamado:
        raise HTTPException(status.HTTP_409_CONFLICT, YA_RECLAMADO) from None


@router.delete("/{business_id}/claim", status_code=status.HTTP_204_NO_CONTENT)
def liberar(business_id: uuid.UUID, usuario: CurrentUserDep, servicio: NegocioServiceDep):
    """Quita la empresa asociada del perfil. La ficha permanece en el marketplace sin titular."""
    try:
        servicio.liberar(business_id, usuario.id)
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NegocioNoEsTitular:
        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR_LIBERAR) from None


@router.post("/{business_id}/checkin", response_model=ReservaOut)
def registrar_asistencia(
    business_id: uuid.UUID,
    datos: CheckinIn,
    usuario: CurrentUserDep,
    servicio: ReservaServiceDep,
):
    """El dueño escanea el QR del usuario y registra asistencia. Solo para el titular del negocio."""
    try:
        return servicio.registrar_asistencia(business_id, usuario.id, datos.qr_token)
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NoEsTitularDelNegocio:
        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR) from None
    except ReservaNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, RESERVA_NO_ENCONTRADA) from None
    except ReservaYaCerrada:
        raise HTTPException(status.HTTP_409_CONFLICT, RESERVA_CERRADA) from None


@router.post("/{business_id}/reservas/{reserva_id}/no-show", response_model=ReservaOut)
def registrar_no_show(
    business_id: uuid.UUID,
    reserva_id: uuid.UUID,
    usuario: CurrentUserDep,
    servicio: ReservaServiceDep,
):
    """El dueño marca una reserva como no-show. Solo para el titular del negocio."""
    try:
        return servicio.registrar_no_show(business_id, usuario.id, reserva_id)
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NoEsTitularDelNegocio:
        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR) from None
    except ReservaNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, RESERVA_NO_ENCONTRADA) from None
    except ReservaYaCerrada:
        raise HTTPException(status.HTTP_409_CONFLICT, RESERVA_CERRADA) from None
