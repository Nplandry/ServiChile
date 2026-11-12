"""Mi QR: carnet de identidad escaneable y validador para cualquier usuario autenticado."""
from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, MiQrServiceDep, RateLimiterDep, demasiadas_solicitudes
from app.api.schemas import MiQrOut, MiQrValidacionOut, MiQrValidarIn
from app.services.mi_qr_service import MiQrInvalido

router = APIRouter(prefix="/v1/mi-qr", tags=["Mi QR"])

VALIDAR_POR_MINUTO = 30


@router.get("", response_model=MiQrOut)
def emitir_mi_qr(usuario: CurrentUserDep, servicio: MiQrServiceDep):
    """Devuelve el payload del carnet propio (código renovable de corta vida)."""
    emitido = servicio.emitir(usuario)
    return MiQrOut(
        payload=emitido.payload,
        token=emitido.token,
        expires_in=emitido.expires_in,
        expires_at=emitido.expires_at,
        nombre=emitido.nombre,
        email=emitido.email,
        nivel_pasaporte=emitido.nivel_pasaporte,  # type: ignore[arg-type]
        estado_pasaporte=emitido.estado_pasaporte,  # type: ignore[arg-type]
        score_confiabilidad=emitido.score_confiabilidad,
        rut_verificado=emitido.rut_verificado,
        xp=emitido.xp,
        nivel_xp=emitido.nivel_xp,
    )


@router.post("/validar", response_model=MiQrValidacionOut)
def validar_mi_qr(
    datos: MiQrValidarIn,
    usuario: CurrentUserDep,
    servicio: MiQrServiceDep,
    limiter: RateLimiterDep,
):
    """Cualquier usuario autenticado valida el QR de otra persona (o el propio)."""
    if not limiter.allow(f"mi-qr-validar:{usuario.id}", VALIDAR_POR_MINUTO):
        raise demasiadas_solicitudes()
    try:
        validado = servicio.validar(usuario, datos.payload)
    except MiQrInvalido as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje) from None
    return MiQrValidacionOut(
        es_propio=validado.es_propio,
        nombre=validado.nombre,
        nivel_pasaporte=validado.nivel_pasaporte,  # type: ignore[arg-type]
        estado_pasaporte=validado.estado_pasaporte,  # type: ignore[arg-type]
        score_confiabilidad=validado.score_confiabilidad,
        rut_verificado=validado.rut_verificado,
        expires_at=validado.expires_at,
        xp=validado.xp,
        nivel_xp=validado.nivel_xp,
    )
