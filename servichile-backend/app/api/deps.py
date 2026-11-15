from functools import lru_cache

from typing import Annotated

from fastapi import Depends, HTTPException, status

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.orm import Session

from app.config import Settings, get_settings

from app.domain.entidades import Usuario

from app.infrastructure.chilecompra import ChileCompra, build_chilecompra

from app.infrastructure.ciber_sonda import CiberSonda, build_ciber_sonda

from app.infrastructure.cmf_indice import CmfIndice, build_cmf_indice

from app.infrastructure.cmf_repository import CmfInstitucionRepository

from app.infrastructure.incidentes_scanner import (
    IncidentesScanner,
    build_incidentes_scanner,
)

from app.infrastructure.places_google import PlacesGoogle, build_places_google

from app.infrastructure.sii_apigateway import (
    SiiContribuyentes,
    build_sii_contribuyentes,
)

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
        NegocioRepository(session), ReservaRepository(session), get_xp_service(session)
    )


def get_reporte_service(
    session: SessionDep,
    settings: SettingsDep,
    pasaporte: Annotated[PasaporteService, Depends(get_pasaporte_service)],
) -> ReporteService:

    return ReporteService(UsuarioRepository(session), pasaporte, settings)


@lru_cache
def get_ciber_sonda() -> CiberSonda:

    from app.infrastructure.busqueda_web import build_buscador

    settings = get_settings()

    tavily = (
        settings.tavily_api_key.get_secret_value().strip()
        if settings.tavily_api_key
        else ""
    )

    buscador = build_buscador(tavily_key=tavily or None)

    return build_ciber_sonda(settings.ciber_sonda, buscador=buscador)


def get_chilecompra() -> ChileCompra:

    settings = get_settings()

    mode = settings.chilecompra_mode

    ticket = (
        settings.chilecompra_ticket.get_secret_value()
        if settings.chilecompra_ticket
        else None
    )

    if mode == "off":

        return build_chilecompra(None)

    if mode == "fake":

        return build_chilecompra(ticket, fake=True)

    if mode == "live":

        return build_chilecompra(ticket)

    return build_chilecompra(ticket, fake=False)


def get_sii_contribuyentes() -> SiiContribuyentes:

    settings = get_settings()

    mode = settings.sii_mode

    token = (
        settings.apigateway_token.get_secret_value()
        if settings.apigateway_token
        else None
    )

    if mode == "off":

        return build_sii_contribuyentes(None)

    if mode == "fake":

        return build_sii_contribuyentes(token, fake=True)

    if mode == "live":

        return build_sii_contribuyentes(token)

    return build_sii_contribuyentes(token, fake=False)


def get_cmf_indice(session: SessionDep) -> CmfIndice:

    settings = get_settings()

    mode = settings.cmf_mode

    key = (
        settings.cmf_api_key.get_secret_value().strip() if settings.cmf_api_key else ""
    )

    if mode == "auto":

        mode = "live" if key else "off"

    if mode in ("off", "fake"):

        return build_cmf_indice(None, mode=mode)

    return build_cmf_indice(CmfInstitucionRepository(session), mode="live")


def get_incidentes_scanner() -> IncidentesScanner:

    settings = get_settings()

    mode = settings.incidentes_mode

    tavily = (
        settings.tavily_api_key.get_secret_value().strip()
        if settings.tavily_api_key
        else ""
    )

    if mode == "auto":

        mode = "live" if tavily else "off"

    return build_incidentes_scanner(mode=mode, tavily_key=tavily or None)


def get_places_google() -> PlacesGoogle:

    settings = get_settings()

    mode = settings.places_mode

    key = (
        settings.google_places_api_key.get_secret_value().strip()
        if settings.google_places_api_key
        else ""
    )

    if mode == "off":

        return build_places_google(None)

    if mode == "fake":

        return build_places_google(key, fake=True)

    if mode == "live":

        return build_places_google(key)

    return build_places_google(key, fake=False)


def get_negocio_service(
    session: SessionDep,
    sonda: Annotated[CiberSonda, Depends(get_ciber_sonda)],
    chilecompra: Annotated[ChileCompra, Depends(get_chilecompra)],
    sii: Annotated[SiiContribuyentes, Depends(get_sii_contribuyentes)],
    cmf: Annotated[CmfIndice, Depends(get_cmf_indice)],
    incidentes: Annotated[IncidentesScanner, Depends(get_incidentes_scanner)],
    places: Annotated[PlacesGoogle, Depends(get_places_google)],
) -> NegocioService:

    return NegocioService(
        NegocioRepository(session),
        sonda,
        usuarios=UsuarioRepository(session),
        chilecompra=chilecompra,
        sii=sii,
        cmf=cmf,
        incidentes=incidentes,
        places=places,
    )


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
