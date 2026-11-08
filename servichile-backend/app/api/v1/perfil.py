"""Perfil y Pasaporte de Confianza del usuario autenticado."""
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUserDep, PasaporteServiceDep, RateLimiterDep, demasiadas_solicitudes
from app.api.mapeos import to_perfil_out
from app.api.schemas import InmobiliariaScoring, PerfilIn, PerfilOut
from app.services.pasaporte_service import (
    DOCUMENTO_MAX_BYTES,
    DocumentoInvalido,
    DocumentoMuyGrande,
    RutEnUso,
    RutRechazado,
    RutYaVerificado,
)

router = APIRouter(prefix="/v1/perfil", tags=["Perfil"])

DOCUMENTOS_POR_MINUTO = 5


@router.get("", response_model=PerfilOut)
def ver_perfil(usuario: CurrentUserDep, servicio: PasaporteServiceDep):
    return to_perfil_out(servicio.estado(usuario))


@router.patch("", response_model=PerfilOut)
def actualizar_perfil(datos: PerfilIn, usuario: CurrentUserDep, servicio: PasaporteServiceDep):
    """Actualiza solo los campos enviados. Envíe un campo como null para borrarlo (no aplica al RUT)."""
    cambios = datos.model_dump(exclude_unset=True)
    try:
        actualizado = servicio.actualizar_perfil(usuario, cambios)
    except RutRechazado as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje) from None
    except (RutEnUso, RutYaVerificado) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, error.mensaje) from None
    return to_perfil_out(servicio.estado(actualizado))


@router.post("/documentos", response_model=InmobiliariaScoring, status_code=status.HTTP_201_CREATED)
async def subir_documento(
    usuario: CurrentUserDep,
    servicio: PasaporteServiceDep,
    limiter: RateLimiterDep,
    archivo: Annotated[UploadFile, File(description="PDF de liquidaciones o Dicom, máximo 1 MB")],
):
    """Nivel 2: calcula el score de arriendo. El PDF se procesa en memoria y no se guarda."""
    if not limiter.allow(f"documento:{usuario.id}", DOCUMENTOS_POR_MINUTO):
        raise demasiadas_solicitudes()
    contenido = await archivo.read(DOCUMENTO_MAX_BYTES + 1)
    try:
        resultado = await run_in_threadpool(servicio.procesar_documento, usuario, contenido)
    except DocumentoMuyGrande as error:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, error.mensaje) from None
    except DocumentoInvalido as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje) from None
    finally:
        # Se descarta el contenido en cuanto termina la petición.
        del contenido
    return InmobiliariaScoring(
        estado_verificacion=resultado.estado_verificacion,
        score_financiero=resultado.score_financiero,
        actualizado_en=resultado.actualizado_en,
    )
