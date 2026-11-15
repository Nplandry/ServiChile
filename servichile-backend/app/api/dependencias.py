"""Ensambla la aplicación: crea servicios y les inyecta repositorios y APIs.

Los routers no tocan la base ni ChileCompra/CMF/SII. Piden un servicio
aquí (por ejemplo ``NegocioServiceDep``) y FastAPI lo construye con
las implementaciones concretas.
"""

from functools import lru_cache

from typing import Annotated

from fastapi import Depends, HTTPException, status

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.orm import Session

from app.configuracion import Settings, get_settings

from app.domain.entidades import Usuario

from app.domain.errores import CredencialesInvalidas

from app.domain.puertos import (
    ProveedorCmf,
    ProveedorIncidentes,
    ProveedorMercadoPublico,
    ProveedorPlaces,
    ProveedorSii,
    SondaCiber,
    VerificadorIdentidad,
)

from app.infrastructure.pdf_antecedentes import AnalizadorPdfAntecedentes

from app.infrastructure.chilecompra import build_chilecompra

from app.infrastructure.ciber_sonda import build_ciber_sonda

from app.infrastructure.cmf.indice import build_cmf_indice

from app.infrastructure.cmf.repositorio import CmfInstitucionRepository

from app.infrastructure.escaner_incidentes import build_incidentes_scanner

from app.infrastructure.lugares_google import build_places_google

from app.infrastructure.sii import build_sii_contribuyentes

from app.infrastructure.persistencia.modelos import get_session

from app.infrastructure.limite_solicitudes import RateLimiter, build_rate_limiter

from app.infrastructure.persistencia.repositorios import (
    NegocioRepository,
    ReservaRepository,
    UsuarioRepository,
    XpRepository,
)

from app.infrastructure.verificacion import build_verificador_rut

from app.services.autenticacion import AuthService

from app.services.cuenta import CuentaService

from app.services.negocio import NegocioService

from app.services.pasaporte import PasaporteService

from app.services.reporte import ReporteService

from app.services.reserva import ReservaService

from app.services.progreso_cliente import XpService

SessionDep = Annotated[Session, Depends(get_session)]

SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def get_rate_limiter() -> RateLimiter:

    return build_rate_limiter(get_settings().redis_url)


def get_xp_service(session: SessionDep) -> XpService:

    return XpService(XpRepository(session))


def get_auth_service(session: SessionDep, settings: SettingsDep) -> AuthService:

    return AuthService(UsuarioRepository(session), settings, get_xp_service(session))


def get_verificador_rut() -> VerificadorIdentidad:

    return build_verificador_rut(get_settings().rut_verifier)


def get_pasaporte_service(
    session: SessionDep,
    verificador: Annotated[VerificadorIdentidad, Depends(get_verificador_rut)],
) -> PasaporteService:

    return PasaporteService(
        UsuarioRepository(session),
        ReservaRepository(session),
        verificador,
        get_xp_service(session),
        AnalizadorPdfAntecedentes(),
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
def get_ciber_sonda() -> SondaCiber:

    from app.infrastructure.busqueda_web import build_buscador

    settings = get_settings()

    tavily = (
        settings.tavily_api_key.get_secret_value().strip()
        if settings.tavily_api_key
        else ""
    )

    buscador = build_buscador(tavily_key=tavily or None)

    return build_ciber_sonda(settings.ciber_sonda, buscador=buscador)


def get_chilecompra() -> ProveedorMercadoPublico:

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


def get_sii_contribuyentes() -> ProveedorSii:

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


def get_cmf_indice(session: SessionDep) -> ProveedorCmf:

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


def get_incidentes_scanner() -> ProveedorIncidentes:

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


def get_places_google() -> ProveedorPlaces:

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
    sonda: Annotated[SondaCiber, Depends(get_ciber_sonda)],
    chilecompra: Annotated[ProveedorMercadoPublico, Depends(get_chilecompra)],
    sii: Annotated[ProveedorSii, Depends(get_sii_contribuyentes)],
    cmf: Annotated[ProveedorCmf, Depends(get_cmf_indice)],
    incidentes: Annotated[ProveedorIncidentes, Depends(get_incidentes_scanner)],
    places: Annotated[ProveedorPlaces, Depends(get_places_google)],
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
