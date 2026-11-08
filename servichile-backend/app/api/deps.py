"""Inyección de dependencias de FastAPI. Las pruebas reemplazan estas funciones con dependency_overrides."""
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.domain.entidades import Usuario
from app.infrastructure.db import get_session
from app.infrastructure.llm import LLMProvider, build_provider
from app.infrastructure.rate_limit import RateLimiter, build_rate_limiter
from app.infrastructure.repositories import (
    ConsultaRepository,
    FragmentoRepository,
    NegocioRepository,
    PasaporteRepository,
    ReservaRepository,
    UsuarioRepository,
)
from app.infrastructure.verificacion import (
    ExtractorFinanciero,
    VerificadorRut,
    build_extractor,
    build_verificador_rut,
)
from app.services.ai_assistant import AiAssistant
from app.services.auth_service import AuthService, CredencialesInvalidas
from app.services.consulta_service import ConsultaService
from app.services.negocio_service import NegocioService
from app.services.pasaporte_service import PasaporteService
from app.services.reserva_service import ReservaService

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def get_llm() -> LLMProvider:
    return build_provider(get_settings())


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return build_rate_limiter(get_settings().redis_url)


def get_fragmento_repo(session: SessionDep) -> FragmentoRepository:
    return FragmentoRepository(session)


def get_auth_service(session: SessionDep, settings: SettingsDep) -> AuthService:
    return AuthService(UsuarioRepository(session), settings)


def get_assistant(
    session: SessionDep,
    settings: SettingsDep,
    llm: Annotated[LLMProvider, Depends(get_llm)],
    fragmentos: Annotated[FragmentoRepository, Depends(get_fragmento_repo)],
) -> AiAssistant:
    return AiAssistant(llm, fragmentos, ConsultaRepository(session), settings)


def get_verificador_rut() -> VerificadorRut:
    return build_verificador_rut(get_settings().rut_verifier)


def get_extractor() -> ExtractorFinanciero:
    return build_extractor(get_settings().pdf_extractor)


def get_pasaporte_service(
    session: SessionDep,
    verificador: Annotated[VerificadorRut, Depends(get_verificador_rut)],
    extractor: Annotated[ExtractorFinanciero, Depends(get_extractor)],
) -> PasaporteService:
    return PasaporteService(
        UsuarioRepository(session),
        ReservaRepository(session),
        PasaporteRepository(session),
        verificador,
        extractor,
    )


def get_reserva_service(session: SessionDep) -> ReservaService:
    return ReservaService(NegocioRepository(session), ReservaRepository(session))


def get_negocio_service(session: SessionDep) -> NegocioService:
    return NegocioService(NegocioRepository(session))


def get_consulta_service(session: SessionDep) -> ConsultaService:
    return ConsultaService(ConsultaRepository(session))


PasaporteServiceDep = Annotated[PasaporteService, Depends(get_pasaporte_service)]
ReservaServiceDep = Annotated[ReservaService, Depends(get_reserva_service)]
NegocioServiceDep = Annotated[NegocioService, Depends(get_negocio_service)]
ConsultaServiceDep = Annotated[ConsultaService, Depends(get_consulta_service)]

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
AssistantDep = Annotated[AiAssistant, Depends(get_assistant)]
CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


def demasiadas_solicitudes() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Demasiados intentos. Espere un minuto e intente de nuevo.",
        headers={"Retry-After": "60"},
    )
