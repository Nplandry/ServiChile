import uuid

from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from starlette.concurrency import run_in_threadpool

from app.api.autorizacion import exige_cuenta_proveedor

from app.api.dependencias import (
    UsuarioActualDep,
    ServicioNegocioDep,
    LimiteSolicitudesDep,
    demasiadas_solicitudes,
)
from app.ensamblado.evaluador import encolar_evaluador

from app.api.esquemas import (
    DocEmpresaSalida,
    NegocioActualizarEntrada,
    NegocioCrearEntrada,
    NegocioEnMapaSalida,
    NegocioRutEntrada,
    NegocioTitularSalida,
    ReputacionSalida,
)
from app.api.mapeos import to_doc_empresa_out

from app.dominio.docs_empresa import DOCS_EMPRESA_MAX_BYTES, TIPOS_PDF
from app.dominio.errores import (
    DocEmpresaInvalido,
    DocEmpresaMuyGrande,
    NegocioNoEncontrado,
    NoEsTitularDelNegocio,
    EvaluadorIndisponible,
)

router = APIRouter(prefix="/v1/businesses", tags=["Negocios"])

CategoriaQuery = Annotated[str | None, Query(max_length=30)]

BusquedaQuery = Annotated[str | None, Query(max_length=120)]

NO_ENCONTRADO = "Negocio no encontrado."

NO_TITULAR = "Solo el titular de la empresa puede realizar esta acción."

NO_TITULAR_ELIMINAR = "Solo quien creó la empresa puede eliminarla."


@router.get("", response_model=list[NegocioEnMapaSalida])
def listar(
    servicio: ServicioNegocioDep,
    categoria: CategoriaQuery = None,
    q: BusquedaQuery = None,
):

    return servicio.listar_para_mapa(categoria, q)


@router.get("/mias", response_model=list[NegocioTitularSalida])
def listar_mias(usuario: UsuarioActualDep, servicio: ServicioNegocioDep):

    return servicio.listar_mios(usuario.id)


@router.post("", response_model=NegocioTitularSalida, status_code=status.HTTP_201_CREATED)
def crear(
    datos: NegocioCrearEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioNegocioDep,
    background_tasks: BackgroundTasks,
):

    exige_cuenta_proveedor(usuario)

    creado = servicio.crear(
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
    return encolar_evaluador(background_tasks, creado.id, servicio=servicio) or creado


DOCS_EMPRESA_POR_MINUTO = 10


@router.post(
    "/{business_id}/documentos/{tipo}",
    response_model=DocEmpresaSalida,
    status_code=status.HTTP_201_CREATED,
)
async def verificar_doc_empresa(
    business_id: uuid.UUID,
    tipo: str,
    usuario: UsuarioActualDep,
    servicio: ServicioNegocioDep,
    limiter: LimiteSolicitudesDep,
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
    if not limiter.permitir(
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


@router.delete(
    "/{business_id}/documentos/{tipo}",
    response_model=DocEmpresaSalida,
)
def revocar_doc_empresa(
    business_id: uuid.UUID,
    tipo: str,
    usuario: UsuarioActualDep,
    servicio: ServicioNegocioDep,
):
    """Revoca un documento verificado (el titular debe revalidar subiendo otro PDF)."""
    exige_cuenta_proveedor(usuario)
    tipo_norm = (tipo or "").strip().lower()
    if tipo_norm not in TIPOS_PDF:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Tipo PDF inválido. Documentos Grupo 1/2: "
            + ", ".join(sorted(TIPOS_PDF)),
        )
    try:
        actualizado = servicio.revocar_doc_empresa(
            business_id, usuario.id, tipo_norm
        )
    except DocEmpresaInvalido as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NoEsTitularDelNegocio:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el titular de la empresa puede revocar documentos legales.",
        ) from None

    return to_doc_empresa_out(
        servicio.respuesta_doc_revocado(actualizado, tipo_norm)
    )


@router.get("/{business_id}/reputation", response_model=ReputacionSalida)
def reputacion(business_id: uuid.UUID, servicio: ServicioNegocioDep):

    try:

        return servicio.obtener_reputacion(business_id)

    except NegocioNoEncontrado:

        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None


REFRESCO_EVALUADOR_POR_MINUTO = 5


@router.post("/{business_id}/rater-refresh", response_model=ReputacionSalida)
def refrescar_evaluador(
    business_id: uuid.UUID,
    usuario: UsuarioActualDep,
    servicio: ServicioNegocioDep,
    limiter: LimiteSolicitudesDep,
):
    """Re-evalúa Places / rastreador_web / ChileCompra y persiste el índice."""
    exige_cuenta_proveedor(usuario)
    if not limiter.permitir(
        f"refresco_evaluador:{usuario.id}:{business_id}", REFRESCO_EVALUADOR_POR_MINUTO
    ):
        raise demasiadas_solicitudes()
    try:
        return servicio.refrescar_indice_titular(business_id, usuario.id)
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NoEsTitularDelNegocio:
        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR) from None
    except EvaluadorIndisponible as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, error.mensaje
        ) from None


@router.patch("/{business_id}/rut", response_model=NegocioTitularSalida)
def actualizar_rut(
    business_id: uuid.UUID,
    datos: NegocioRutEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioNegocioDep,
    background_tasks: BackgroundTasks,
):
    exige_cuenta_proveedor(usuario)
    try:
        titular, pendiente = servicio.actualizar_rut_empresa(
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
    if pendiente:
        return encolar_evaluador(background_tasks, business_id, servicio=servicio) or titular
    return titular


@router.patch("/{business_id}", response_model=NegocioTitularSalida)
def actualizar(
    business_id: uuid.UUID,
    datos: NegocioActualizarEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioNegocioDep,
    background_tasks: BackgroundTasks,
):
    exige_cuenta_proveedor(usuario)
    try:
        titular, pendiente = servicio.actualizar(
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
    if pendiente:
        return encolar_evaluador(background_tasks, business_id, servicio=servicio) or titular
    return titular


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    business_id: uuid.UUID, usuario: UsuarioActualDep, servicio: ServicioNegocioDep
):

    try:

        servicio.eliminar(business_id, usuario.id)

    except NegocioNoEncontrado:

        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None

    except NoEsTitularDelNegocio:

        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR_ELIMINAR) from None
