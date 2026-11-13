from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.domain.entidades import Usuario
from app.infrastructure.ciber_sonda import CiberSonda, build_ciber_sonda
from app.infrastructure.db import get_session
from app.infrastructure.rate_limit import RateLimiter, build_rate_limiter
from app.infrastructure.repositories import (
    NegocioRepository,
    ReservaRepository,
    UsuarioRepository,
    XpRepository,
)
from app.infrastructure.verificacion import VerificadorRut, build_verificador_rut
from app.services.auth_service import AuthService, CredencialesInvalidas
from app.services.cuenta_service import CuentaService
from app.services.negocio_service import NegocioService
from app.services.pasaporte_service import PasaporteService
from app.services.reporte_service import ReporteService
from app.services.reserva_service import ReservaService
from app.services.xp_service import XpService

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return build_rate_limiter(get_settings().redis_url)


def get_xp_service(session: SessionDep) -> XpService:
    return XpService(XpRepository(session))


def get_auth_service(session: SessionDep, settings: SettingsDep) -> AuthService:
    return AuthService(UsuarioRepository(session), settings, get_xp_service(session))


def get_verificador_rut() -> VerificadorRut:
    return build_verificador_rut(get_settings().rut_verifier)


def get_pasaporte_service(
    session: SessionDep,
    verificador: Annotated[VerificadorRut, Depends(get_verificador_rut)],
) -> PasaporteService:
    return PasaporteService(
        UsuarioRepository(session),
        ReservaRepository(session),
        verificador,
        get_xp_service(session),
    )


def get_reserva_service(session: SessionDep) -> ReservaService:
    return ReservaService(
        NegocioRepository(session),
        ReservaRepository(session),
        get_xp_service(session),
    )


def get_reporte_service(
    session: SessionDep,
    settings: SettingsDep,
    pasaporte: Annotated[PasaporteService, Depends(get_pasaporte_service)],
) -> ReporteService:
    return ReporteService(UsuarioRepository(session), pasaporte, settings)


@lru_cache
def get_ciber_sonda() -> CiberSonda:
    return build_ciber_sonda(get_settings().ciber_sonda)


def get_negocio_service(
    session: SessionDep,
    sonda: Annotated[CiberSonda, Depends(get_ciber_sonda)],
) -> NegocioService:
    return NegocioService(NegocioRepository(session), sonda)


def get_cuenta_service(
    session: SessionDep,
    negocios: Annotated[NegocioService, Depends(get_negocio_service)],
) -> CuentaService:
    return CuentaService(UsuarioRepository(session), negocios)


PasaporteServiceDep = Annotated[PasaporteService, Depends(get_pasaporte_service)]
ReservaServiceDep = Annotated[ReservaService, Depends(get_reserva_service)]
ReporteServiceDep = Annotated[ReporteService, Depends(get_reporte_service)]
NegocioServiceDep = Annotated[NegocioService, Depends(get_negocio_service)]
CuentaServiceDep = Annotated[CuentaService, Depends(get_cuenta_service)]
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> Usuario:
    if credentials is None:
        raise _no_autorizado()
    try:
        return auth.usuario_desde_token(credentials.credentials)
    except CredencialesInvalidas:
        raise _no_autorizado() from None


def _no_autorizado() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión inválida o expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


def demasiadas_solicitudes() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Demasiados intentos. Espere un minuto e intente de nuevo.",
        headers={"Retry-After": "60"},
    )
