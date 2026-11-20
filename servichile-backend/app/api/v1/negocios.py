import logging
import os
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
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.api.autorizacion import exige_cuenta_proveedor
from app.configuracion import Configuracion

log = logging.getLogger(__name__)


def _exige_pago_publicacion(settings: Configuracion) -> bool:
    """Pago obligatorio salvo pytest con APP_ENV=test (no basta APP_ENV=test solo)."""
    if os.environ.get("SERVICHILE_SKIP_PAGO_PUBLICACION") == "1":
        return False
    if settings.app_env == "test" and os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    return True

from app.api.dependencias import (
    UsuarioActualDep,
    UsuarioOpcionalDep,
    ServicioNegocioDep,
    ServicioPagoInformeDep,
    ServicioPagoPublicacionDep,
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
    RutEmpresaEnUso,
)
from app.dominio.oferta_negocio import (
    FiltroListado,
    OfertaInvalida,
    concretados_de,
    concretados_minimo,
    contrataciones_de,
    industrias_de,
    monto_de,
    plazo_de,
)

router = APIRouter(prefix="/v1/businesses", tags=["Negocios"])

CategoriaQuery = Annotated[str | None, Query(max_length=30)]

BusquedaQuery = Annotated[str | None, Query(max_length=120)]

NO_ENCONTRADO = "Negocio no encontrado."

NO_TITULAR = "Solo el titular de la empresa puede realizar esta acción."

NO_TITULAR_ELIMINAR = "Solo quien creó la empresa puede eliminarla."

RUT_EN_USO = "Este RUT de empresa ya está registrado."


def _opcion_query(valor: str | None, normalizar) -> str | None:
    try:
        return normalizar(valor)
    except OfertaInvalida as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None


def _catalogo_query(valor: str | None, normalizar) -> str | None:
    if valor is None or not valor.strip():
        return None
    try:
        return normalizar([valor.strip()])[0]
    except OfertaInvalida as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None


@router.get("", response_model=list[NegocioEnMapaSalida])
def listar(
    servicio: ServicioNegocioDep,
    categoria: CategoriaQuery = None,
    q: BusquedaQuery = None,
    industria: Annotated[str | None, Query(max_length=40)] = None,
    contratacion: Annotated[str | None, Query(max_length=40)] = None,
    monto: Annotated[str | None, Query(max_length=20)] = None,
    plazo: Annotated[str | None, Query(max_length=20)] = None,
    concretados: Annotated[str | None, Query(max_length=10)] = None,
):
    return servicio.listar_para_mapa(
        FiltroListado(
            categoria=(categoria or "").strip() or None,
            q=(q or "").strip() or None,
            industria=_catalogo_query(industria, industrias_de),
            contratacion=_catalogo_query(contratacion, contrataciones_de),
            monto=_opcion_query(monto, monto_de),
            plazo=_opcion_query(plazo, plazo_de),
            concretados_min=concretados_minimo(
                _opcion_query(concretados, concretados_de)
            ),
        )
    )


@router.get("/mias", response_model=list[NegocioTitularSalida])
def listar_mias(usuario: UsuarioActualDep, servicio: ServicioNegocioDep):

    return servicio.listar_mios(usuario.id)


@router.post("", response_model=NegocioTitularSalida, status_code=status.HTTP_201_CREATED)
def crear(
    datos: NegocioCrearEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioNegocioDep,
    pagos_pub: ServicioPagoPublicacionDep,
    background_tasks: BackgroundTasks,
):
    from app.configuracion import obtener_configuracion
    from app.dominio.errores import PublicacionSinPago

    exige_cuenta_proveedor(usuario)

    from app.dominio.pago_publicacion import formato_monto_clp

    settings = obtener_configuracion()
    exige_pago = _exige_pago_publicacion(settings)
    buy_order = (datos.buy_order or "").strip() or None
    precio_txt = formato_monto_clp(settings.pagos_publicacion_monto)
    session = servicio.negocios.session

    def _kwargs_crear(*, commit: bool):
        return dict(
            nombre=datos.nombre,
            categoria=datos.categoria,
            direccion=datos.direccion,
            descripcion=datos.descripcion,
            telefono=datos.telefono,
            sitio_web=datos.sitio_web,
            imagen_url=datos.imagen_url,
            logo_url=datos.logo_url,
            rut_empresa=datos.rut_empresa,
            servicios=datos.servicios,
            industrias=datos.industrias,
            contrataciones=datos.contrataciones,
            monto=datos.monto,
            plazo=datos.plazo,
            referencias=datos.referencias,
            commit=commit,
        )

    if exige_pago:
        if not buy_order:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                {
                    "mensaje": (
                        f"Debe pagar la publicación ({precio_txt}) "
                        "antes de crear la ficha."
                    ),
                    "codigo": "publicacion_sin_pago",
                },
            )
        previo = pagos_pub.consultar(usuario, buy_order)
        if not pagos_pub.listo_para_alta(previo.estado, consumido=previo.consumido):
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                {
                    "mensaje": "El pago de publicación no está listo o ya fue usado.",
                    "codigo": "publicacion_sin_pago",
                    "buy_order": buy_order,
                },
            )

    creado = None
    try:
        if buy_order:
            # Una sola TX: reserva + ficha + consumo (sin commit intermedio).
            if exige_pago:
                pagos_pub.reservar_para_alta(
                    usuario.id, buy_order, commit=False
                )
            creado = servicio.crear(usuario.id, **_kwargs_crear(commit=False))
            pagos_pub.consumir_para_publicar(
                usuario.id, buy_order, creado.id, commit=False
            )
            session.commit()
        else:
            creado = servicio.crear(usuario.id, **_kwargs_crear(commit=True))
    except PublicacionSinPago as e:
        session.rollback()
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            {"mensaje": e.mensaje, "codigo": e.codigo},
        ) from None
    except (OfertaInvalida, RutEmpresaEnUso) as error:
        session.rollback()
        if isinstance(error, OfertaInvalida):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
            ) from None
        raise HTTPException(status.HTTP_409_CONFLICT, RUT_EN_USO) from None
    except IntegrityError:
        session.rollback()
        log.exception(
            "IntegrityError en alta de empresa (buy_order=%s)", buy_order
        )
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "mensaje": "No se pudo crear la ficha por un conflicto de datos.",
                "codigo": "alta_conflicto",
            },
        ) from None
    except Exception:
        session.rollback()
        log.exception("Alta de empresa falló (buy_order=%s)", buy_order)
        raise
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
                "escaneo/foto"
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
def reputacion(
    business_id: uuid.UUID,
    servicio: ServicioNegocioDep,
    pagos: ServicioPagoInformeDep,
    usuario: UsuarioOpcionalDep,
):
    """Público: índice + teaser de 3 observables; desglose completo con compra/titular."""
    from app.dominio.transparencia.valoracion import teaser_observables_publico

    try:
        rep = servicio.obtener_reputacion(business_id)
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    out = ReputacionSalida.model_validate(rep)
    if usuario is not None and pagos.tiene_acceso_informe(usuario, business_id):
        return out.model_copy(update={"observables_restantes": 0})
    teaser, restantes = teaser_observables_publico(rep.observables)
    return out.model_copy(
        update={
            "observables": teaser,
            "observables_restantes": restantes,
            "docs_empresa": None,
        }
    )


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
    except RutEmpresaEnUso:
        raise HTTPException(status.HTTP_409_CONFLICT, RUT_EN_USO) from None
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
            servicios=datos.servicios,
            industrias=datos.industrias,
            contrataciones=datos.contrataciones,
            monto=datos.monto,
            plazo=datos.plazo,
            referencias=datos.referencias,
        )
    except OfertaInvalida as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None
    except DocEmpresaInvalido as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO) from None
    except NoEsTitularDelNegocio:
        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR) from None
    except RutEmpresaEnUso:
        raise HTTPException(status.HTTP_409_CONFLICT, RUT_EN_USO) from None
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
