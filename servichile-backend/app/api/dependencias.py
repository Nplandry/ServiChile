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
    AlmacenamientoBiometria,
    AlmacenamientoCedula,
    AnalizadorAntecedentes,
    AnalizadorAval,
    AnalizadorCedula,
    AnalizadorDocEmpresa,
    EmisorReporte,
    EmisorSesion,
    HasherContrasena,
    VerificadorIdentidad,
)

from app.infraestructura.biometria_fs import AlmacenamientoBiometriaLocal

from app.infraestructura.cedula_fs import AlmacenamientoCedulaLocal

from app.infraestructura.cedula_ocr import AnalizadorCedulaOcr, LectorOcrTesseract
from app.infraestructura.cedula_vision import ComparadorRostrosOpenCv

from app.infraestructura.pdf_antecedentes import AnalizadorPdfAntecedentes
from app.infraestructura.pdf_aval import AnalizadorPdfAval
from app.infraestructura.pdf_docs_empresa import AnalizadorPdfDocEmpresa

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

from app.ensamblado.rater import armar_negocio_service

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
    settings = get_settings()
    return AnalizadorPdfAntecedentes(str(settings.pades_ca_ruta()))


@lru_cache
def get_almacenamiento_biometria() -> AlmacenamientoBiometria:
    settings = get_settings()
    return AlmacenamientoBiometriaLocal(
        settings.biometria_raiz(),
        max_lado=settings.biometria_max_lado,
        jpeg_quality=settings.biometria_jpeg_quality,
    )


@lru_cache
def get_almacenamiento_cedula() -> AlmacenamientoCedula:
    settings = get_settings()
    return AlmacenamientoCedulaLocal(
        settings.cedula_raiz(),
        max_lado=settings.cedula_max_lado,
        jpeg_quality=settings.cedula_jpeg_quality,
    )


@lru_cache
def get_analizador_cedula() -> AnalizadorCedula:
    return AnalizadorCedulaOcr(LectorOcrTesseract(), ComparadorRostrosOpenCv())


@lru_cache
def get_analizador_aval() -> AnalizadorAval:
    return AnalizadorPdfAval()


@lru_cache
def get_analizador_docs_empresa() -> AnalizadorDocEmpresa:
    settings = get_settings()
    return AnalizadorPdfDocEmpresa(str(settings.pades_ca_ruta()))


def get_pasaporte_service(
    session: SessionDep,
    verificador: Annotated[VerificadorIdentidad, Depends(get_verificador_rut)],
    analizador: Annotated[AnalizadorAntecedentes, Depends(get_analizador_antecedentes)],
    biometria: Annotated[
        AlmacenamientoBiometria, Depends(get_almacenamiento_biometria)
    ],
    cedula: Annotated[AlmacenamientoCedula, Depends(get_almacenamiento_cedula)],
    analizador_cedula: Annotated[AnalizadorCedula, Depends(get_analizador_cedula)],
    analizador_aval: Annotated[AnalizadorAval, Depends(get_analizador_aval)],
    settings: SettingsDep,
) -> PasaporteService:

    return PasaporteService(
        UsuarioRepository(session),
        ReservaRepository(session),
        verificador,
        get_xp_service(session),
        analizador,
        biometria,
        biometria_retencion_dias=settings.biometria_retencion_dias,
        cedula=cedula,
        analizador_cedula=analizador_cedula,
        cedula_retencion_dias=settings.cedula_retencion_dias,
        analizador_aval=analizador_aval,
    )


def get_negocio_service(
    session: SessionDep,
    analizador_docs: Annotated[
        AnalizadorDocEmpresa, Depends(get_analizador_docs_empresa)
    ],
) -> NegocioService:
    return armar_negocio_service(session, analizador_docs)


def get_reserva_service(session: SessionDep) -> ReservaService:

    return ReservaService(
        NegocioRepository(session),
        ReservaRepository(session),
        get_xp_service(session),
    )


def get_reporte_service(
    session: SessionDep,
    pasaporte: Annotated[PasaporteService, Depends(get_pasaporte_service)],
    emisor: Annotated[EmisorReporte, Depends(get_emisor_reporte)],
) -> ReporteService:

    return ReporteService(UsuarioRepository(session), pasaporte, emisor)


def get_cuenta_service(
    session: SessionDep,
    negocios: Annotated[NegocioService, Depends(get_negocio_service)],
    hasher: Annotated[HasherContrasena, Depends(get_hasher)],
    biometria: Annotated[
        AlmacenamientoBiometria, Depends(get_almacenamiento_biometria)
    ],
    cedula: Annotated[AlmacenamientoCedula, Depends(get_almacenamiento_cedula)],
) -> CuentaService:

    return CuentaService(
        UsuarioRepository(session), negocios, hasher, biometria, cedula
    )


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
