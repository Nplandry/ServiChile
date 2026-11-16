import uuid

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.api.autorizacion import exige_cuenta_proveedor

from app.api.dependencias import (
    CurrentUserDep,
    NegocioServiceDep,
    RateLimiterDep,
    demasiadas_solicitudes,
)

from app.api.esquemas import (
    DocEmpresaOut,
    NegocioActualizarIn,
    NegocioCrearIn,
    NegocioEnMapaOut,
    NegocioRutIn,
    NegocioTitularOut,
    ReputacionOut,
)
from app.api.mapeos import to_doc_empresa_out

from app.dominio.docs_empresa import DOCS_EMPRESA_MAX_BYTES, TIPOS_PDF
from app.dominio.errores import (
    DocEmpresaInvalido,
    DocEmpresaMuyGrande,
    NegocioNoEncontrado,
    NoEsTitularDelNegocio,
    RaterIndisponible,
)

router = APIRouter(prefix="/v1/businesses", tags=["Negocios"])

CategoriaQuery = Annotated[str | None, Query(max_length=30)]

BusquedaQuery = Annotated[str | None, Query(max_length=120)]

NO_ENCONTRADO = "Negocio no encontrado."

NO_TITULAR = "Solo el titular de la empresa puede realizar esta acción."

NO_TITULAR_ELIMINAR = "Solo quien creó la empresa puede eliminarla."


@router.get("", response_model=list[NegocioEnMapaOut])
def listar(
    servicio: NegocioServiceDep,
    categoria: CategoriaQuery = None,
    q: BusquedaQuery = None,
):

    return servicio.listar_para_mapa(categoria, q)


@router.get("/mias", response_model=list[NegocioTitularOut])
def listar_mias(usuario: CurrentUserDep, servicio: NegocioServiceDep):

    return servicio.listar_mios(usuario.id)


@router.post("", response_model=NegocioTitularOut, status_code=status.HTTP_201_CREATED)
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
        rut_empresa=datos.rut_empresa,
    )


DOCS_EMPRESA_POR_MINUTO = 10


@router.post(
    "/{business_id}/documentos/{tipo}",
    response_model=DocEmpresaOut,
    status_code=status.HTTP_201_CREATED,
)
async def verificar_doc_empresa(
    business_id: uuid.UUID,
    tipo: str,
    usuario: CurrentUserDep,
    servicio: NegocioServiceDep,
    limiter: RateLimiterDep,
    archivo: Annotated[
        UploadFile,
        File(
            description=(
                "PDF textual del documento legal de empresa; no se admite "
                "escaneo/foto; no se almacena"
            )
        ),
    ],
    nombre_archivo: Annotated[str | None, Form()] = None,
):
    exige_cuenta_proveedor(usuario)
    tipo_norm = (tipo or "").strip().lower()
    if tipo_norm not in TIPOS_PDF:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Tipo PDF inválido. Documentos Grupo 1/2: "
            + ", ".join(sorted(TIPOS_PDF)),
        )
    if not limiter.allow(
        f"docs_empresa:{usuario.id}:{business_id}", DOCS_EMPRESA_POR_MINUTO
    ):
        raise demasiadas_solicitudes()

    contenido = await archivo.read(DOCS_EMPRESA_MAX_BYTES + 1)
    nombre = (nombre_archivo or archivo.filename or "").strip() or None
    try:
        actualizado, resultado = await run_in_threadpool(
            servicio.procesar_doc_empresa,
            business_id,
            usuario.id,
            tipo_norm,
            contenido,
            nombre,
        )
    except DocEmpresaMuyGrande as error:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, error.mensaje) from None
    except DocEmpresaInvalido as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NoEsTitularDelNegocio:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el titular de la empresa puede cargar documentos legales.",
        ) from None
    finally:
        del contenido

    return to_doc_empresa_out(
        servicio.respuesta_doc_empresa(actualizado, tipo_norm, resultado)
    )


@router.get("/{business_id}/reputation", response_model=ReputacionOut)
def reputacion(business_id: uuid.UUID, servicio: NegocioServiceDep):

    try:

        return servicio.obtener_reputacion(business_id)

    except NegocioNoEncontrado:

        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None


RATER_REFRESH_POR_MINUTO = 5


@router.post("/{business_id}/rater-refresh", response_model=ReputacionOut)
def rater_refresh(
    business_id: uuid.UUID,
    usuario: CurrentUserDep,
    servicio: NegocioServiceDep,
    limiter: RateLimiterDep,
):
    """Re-evalúa Places / crawler / ChileCompra y persiste el índice."""
    exige_cuenta_proveedor(usuario)
    if not limiter.allow(
        f"rater_refresh:{usuario.id}:{business_id}", RATER_REFRESH_POR_MINUTO
    ):
        raise demasiadas_solicitudes()
    try:
        return servicio.refrescar_indice_titular(business_id, usuario.id)
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NoEsTitularDelNegocio:
        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR) from None
    except RaterIndisponible as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, error.mensaje
        ) from None


@router.patch("/{business_id}/rut", response_model=NegocioTitularOut)
def actualizar_rut(
    business_id: uuid.UUID,
    datos: NegocioRutIn,
    usuario: CurrentUserDep,
    servicio: NegocioServiceDep,
):
    exige_cuenta_proveedor(usuario)
    try:
        return servicio.actualizar_rut_empresa(
            business_id, usuario.id, datos.rut_empresa
        )
    except DocEmpresaInvalido as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NoEsTitularDelNegocio:
        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR) from None


@router.patch("/{business_id}", response_model=NegocioTitularOut)
def actualizar(
    business_id: uuid.UUID,
    datos: NegocioActualizarIn,
    usuario: CurrentUserDep,
    servicio: NegocioServiceDep,
):
    exige_cuenta_proveedor(usuario)
    try:
        return servicio.actualizar(
            business_id,
            usuario.id,
            nombre=datos.nombre,
            categoria=datos.categoria,
            direccion=datos.direccion,
            descripcion=datos.descripcion,
            telefono=datos.telefono,
            sitio_web=datos.sitio_web,
            imagen_url=datos.imagen_url,
            logo_url=datos.logo_url,
            rut_empresa=datos.rut_empresa,
        )
    except DocEmpresaInvalido as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NoEsTitularDelNegocio:
        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR) from None


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    business_id: uuid.UUID, usuario: CurrentUserDep, servicio: NegocioServiceDep
):

    try:

        servicio.eliminar(business_id, usuario.id)

    except NegocioNoEncontrado:

        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None

    except NoEsTitularDelNegocio:

        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR_ELIMINAR) from None
