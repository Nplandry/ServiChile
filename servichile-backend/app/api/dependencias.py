"""Ensambla la aplicación: crea servicios y les inyecta repositorios.

Los routers no tocan la base. Piden un servicio aquí (por ejemplo
``NegocioServiceDep``) y FastAPI lo construye con las implementaciones concretas.
"""

from functools import lru_cache

from typing import Annotated

from fastapi import Depends, HTTPException, status

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.orm import Session

from app.configuracion import Settings, get_settings

from app.dominio.entidades import Usuario

from app.dominio.errores import CredencialesInvalidas

from app.dominio.puertos import (
    AnalizadorAntecedentes,
    EmisorReporte,
    EmisorSesion,
    HasherContrasena,
    VerificadorIdentidad,
)

from app.infraestructura.pdf_antecedentes import AnalizadorPdfAntecedentes

from app.infraestructura.persistencia.modelos import get_session

from app.infraestructura.limite_solicitudes import RateLimiter, build_rate_limiter

from app.infraestructura.persistencia.repositorios import (
    NegocioRepository,
    ReservaRepository,
    UsuarioRepository,
    XpRepository,
)

from app.infraestructura.seguridad.hasher import HasherArgon2

from app.infraestructura.seguridad.jwt_reporte import JwtReporte

from app.infraestructura.seguridad.jwt_sesion import JwtSesion

from app.infraestructura.verificacion import build_verificador_rut

from app.servicios.autenticacion import AuthService

from app.servicios.cuenta import CuentaService

from app.servicios.negocio import NegocioService

from app.servicios.pasaporte import PasaporteService

from app.servicios.reporte import ReporteService

from app.servicios.reserva import ReservaService

from app.servicios.progreso_cliente import XpService

SessionDep = Annotated[Session, Depends(get_session)]

SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def get_rate_limiter() -> RateLimiter:

    return build_rate_limiter(get_settings().redis_url)


def get_xp_service(session: SessionDep) -> XpService:

    return XpService(XpRepository(session))


@lru_cache
def get_hasher() -> HasherContrasena:

    return HasherArgon2()


@lru_cache
def get_emisor_sesion() -> EmisorSesion:

    settings = get_settings()

    return JwtSesion(
        settings.jwt_secret.get_secret_value(), settings.jwt_expires_minutes
    )


@lru_cache
def get_emisor_reporte() -> EmisorReporte:

    settings = get_settings()

    return JwtReporte(
        settings.jwt_secret.get_secret_value(), settings.reporte_expires_minutes
    )


def get_auth_service(
    session: SessionDep,
    hasher: Annotated[HasherContrasena, Depends(get_hasher)],
    sesion: Annotated[EmisorSesion, Depends(get_emisor_sesion)],
) -> AuthService:

    return AuthService(
        UsuarioRepository(session), hasher, sesion, get_xp_service(session)
    )


def get_verificador_rut() -> VerificadorIdentidad:

    return build_verificador_rut(get_settings().rut_verifier)


@lru_cache
def get_analizador_antecedentes() -> AnalizadorAntecedentes:

    return AnalizadorPdfAntecedentes()


def get_pasaporte_service(
    session: SessionDep,
    verificador: Annotated[VerificadorIdentidad, Depends(get_verificador_rut)],
    analizador: Annotated[AnalizadorAntecedentes, Depends(get_analizador_antecedentes)],
) -> PasaporteService:

    return PasaporteService(
        UsuarioRepository(session),
        ReservaRepository(session),
        verificador,
        get_xp_service(session),
        analizador,
    )

def get_negocio_service(session: SessionDep) -> NegocioService:

    return NegocioService(NegocioRepository(session))


def get_reserva_service(session: SessionDep) -> ReservaService:

    return ReservaService(
        NegocioRepository(session),
        ReservaRepository(session),
        get_xp_service(session),
    )


def get_reporte_service(
    session: SessionDep,
    emisor: Annotated[EmisorReporte, Depends(get_emisor_reporte)],
) -> ReporteService:

    return ReporteService(
        UsuarioRepository(session),
        PasaporteService(
            UsuarioRepository(session),
            ReservaRepository(session),
            get_verificador_rut(),
            get_xp_service(session),
        ),
        emisor,
    )


def get_cuenta_service(
    session: SessionDep,
    negocios: Annotated[NegocioService, Depends(get_negocio_service)],
    hasher: Annotated[HasherContrasena, Depends(get_hasher)],
) -> CuentaService:

    return CuentaService(UsuarioRepository(session), negocios, hasher)


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
