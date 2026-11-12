from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import (
    AuthServiceDep,
    CuentaServiceDep,
    CurrentUserDep,
    PasaporteServiceDep,
    RateLimiterDep,
    SettingsDep,
    demasiadas_solicitudes,
)
from app.api.mapeos import to_usuario_out
from app.api.schemas import EliminarCuentaIn, LoginIn, RegistroIn, TokenOut, UsuarioOut
from app.services.auth_service import CredencialesInvalidas, EmailYaRegistrado
from app.services.cuenta_service import ContrasenaIncorrecta

router = APIRouter(prefix="/v1/auth", tags=["Autenticación"])

CREDENCIALES_INCORRECTAS = "Correo o contraseña incorrectos."


def _ip(request: Request, settings) -> str:
    # Detrás de Cloud Run, la IP del cliente es la última entrada de X-Forwarded-For (la agrega el proxy de Google).
    # La primera entrada la escribe el cliente y puede falsificarse, por eso no se usa.
    if settings.trust_proxy:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[-1].strip()
    return request.client.host if request.client else "desconocida"


def _limitar_intento(request: Request, accion: str, email: str, limiter, settings) -> None:
    # Límite por correo (protege una cuenta) y por IP (protege contra barridos de muchos correos)
    if not limiter.allow(f"{accion}-correo:{email}", settings.login_rate_per_minute):
        raise demasiadas_solicitudes()
    if not limiter.allow(f"{accion}-ip:{_ip(request, settings)}", settings.login_ip_rate_per_minute):
        raise demasiadas_solicitudes()


@router.post("/registro", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def registro(
    datos: RegistroIn,
    request: Request,
    auth: AuthServiceDep,
    pasaporte: PasaporteServiceDep,
    limiter: RateLimiterDep,
    settings: SettingsDep,
):
    _limitar_intento(request, "registro", datos.email.lower(), limiter, settings)
    perfil = datos.perfil.model_dump(exclude_unset=True)
    try:
        usuario = auth.registrar(datos.email, datos.nombre, datos.password, perfil)
    except EmailYaRegistrado:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este correo ya está registrado. Inicie sesión.") from None
    return to_usuario_out(usuario, pasaporte.estado(usuario))


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, request: Request, auth: AuthServiceDep, limiter: RateLimiterDep, settings: SettingsDep):
    _limitar_intento(request, "login", datos.email.lower(), limiter, settings)
    try:
        token = auth.login(datos.email, datos.password)
    except CredencialesInvalidas:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, CREDENCIALES_INCORRECTAS) from None
    return TokenOut(access_token=token.access_token, expires_in=token.expires_in)


@router.get("/yo", response_model=UsuarioOut)
def yo(usuario: CurrentUserDep, pasaporte: PasaporteServiceDep):
    return to_usuario_out(usuario, pasaporte.estado(usuario))


@router.delete("/yo", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuenta(datos: EliminarCuentaIn, usuario: CurrentUserDep, cuenta: CuentaServiceDep):
    """Borra la cuenta y sus datos. Requiere la contraseña actual."""
    try:
        cuenta.eliminar(usuario, datos.password)
    except ContrasenaIncorrecta:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La contraseña no coincide.") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
