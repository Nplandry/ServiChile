from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import (
    AssistantDep,
    ConsultaServiceDep,
    CurrentUserDep,
    RateLimiterDep,
    SettingsDep,
    demasiadas_solicitudes,
)
from app.api.schemas import ConsultaIn, ConsultaOut, ConsultaResumen

router = APIRouter(prefix="/v1/consultas", tags=["Consultas IA"])


@router.post("", response_model=ConsultaOut, status_code=status.HTTP_201_CREATED)
def crear_consulta(
    datos: ConsultaIn,
    usuario: CurrentUserDep,
    assistant: AssistantDep,
    limiter: RateLimiterDep,
    settings: SettingsDep,
):
    if not limiter.allow(f"consulta:{usuario.id}", settings.consulta_rate_per_minute):
        raise demasiadas_solicitudes()
    resultado = assistant.responder(usuario.id, datos.pregunta, datos.categoria)
    return ConsultaOut(
        id=resultado.id,
        respuesta=resultado.respuesta,
        fuentes=resultado.fuentes,
        requiere_humano=resultado.requiere_humano,
        creado_en=resultado.creado_en,
    )


@router.get("", response_model=list[ConsultaResumen])
def historial(
    usuario: CurrentUserDep,
    servicio: ConsultaServiceDep,
    limite: Annotated[int, Query(ge=1, le=100)] = 50,
):
    return servicio.historial(usuario.id, limite)
