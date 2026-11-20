from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.dominio.biometria import (
    BIOMETRIA_JPEG_QUALITY_DEFAULT,
    BIOMETRIA_MAX_LADO_DEFAULT,
    BIOMETRIA_RETENCION_DIAS_DEFAULT,
)
from app.dominio.cedula import (
    CEDULA_JPEG_QUALITY_DEFAULT,
    CEDULA_MAX_LADO_DEFAULT,
    CEDULA_RETENCION_DIAS_DEFAULT,
)


class Configuracion(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["local", "test", "production"] = "local"

    database_url: str = (
        "postgresql+psycopg://servichile:servichile@localhost:5432/servichile"
    )

    jwt_secret: SecretStr = Field(min_length=32)

    jwt_expires_minutes: int = Field(default=60, ge=5, le=1440)

    reporte_expires_minutes: int = Field(default=15, ge=1, le=120)

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5500"]

    # Se deriva al cargar (no configurar en .env salvo override de depuración).
    rut_verifier: Literal["muestra", "estricto", "chilecompra"] = "estricto"

    redis_url: str | None = None

    login_rate_per_minute: int = 5

    login_ip_rate_per_minute: int = 20

    trust_proxy: bool = False

    # Selfie biométrica: filesystem local (no nube) + metadata en Postgres.
    biometria_dir: str = "var/biometria"

    biometria_retencion_dias: int = Field(
        default=BIOMETRIA_RETENCION_DIAS_DEFAULT, ge=1, le=3650
    )

    biometria_max_lado: int = Field(default=BIOMETRIA_MAX_LADO_DEFAULT, ge=64, le=2048)

    biometria_jpeg_quality: int = Field(
        default=BIOMETRIA_JPEG_QUALITY_DEFAULT, ge=40, le=95
    )

    def biometria_raiz(self) -> Path:
        ruta = Path(self.biometria_dir)
        if not ruta.is_absolute():
            ruta = Path.cwd() / ruta
        return ruta

    # Cédula: foto frontal en disco local + OCR Tesseract (sin LLM).
    cedula_dir: str = "var/cedulas"

    cedula_retencion_dias: int = Field(
        default=CEDULA_RETENCION_DIAS_DEFAULT, ge=1, le=3650
    )

    cedula_max_lado: int = Field(default=CEDULA_MAX_LADO_DEFAULT, ge=400, le=4000)

    cedula_jpeg_quality: int = Field(
        default=CEDULA_JPEG_QUALITY_DEFAULT, ge=50, le=95
    )

    cedula_ocr: Literal["tesseract"] = "tesseract"

    # PAdES: bóveda CA Chile (pem maestro). En tests se puede apuntar a un PEM temporal.
    pades_ca_pem: str = "app/infraestructura/certs/ca_chile.pem"

    # Evaluador fijo en producción: sin GOOGLE_PLACES_API_KEY / CHILECOMPRA_TICKET
    # se simulan solo esas fuentes (HINTS_FIJOS). El rastreador_web no requiere key.
    # 4s: rastreador_web (home + rutas legales) + Places + ChileCompra en paralelo.
    rater_budget_seconds: float = Field(default=4.0, ge=0.5, le=30.0)
    # Refresco en segundo plano (minutos). 0 = desactivado. En APP_ENV=test no arranca.
    rater_refresh_minutes: float = Field(default=30.0, ge=0.0, le=24 * 60)
    chilecompra_ticket: str = ""
    google_places_api_key: str = ""

    # Correo de salida de ServiChile. El destinatario es el correo del registro.
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_usuario: str = ""
    smtp_clave: SecretStr = SecretStr("")
    smtp_desde: str = ""

    # Webpay Plus. En local/test se permiten defaults de integración Transbank.
    # En production deben ser credenciales reales (fail-fast si no).
    public_frontend_url: str = "http://localhost:5500/index.html"
    transbank_commerce_code: str = "597055555532"
    transbank_api_key: SecretStr = SecretStr(
        "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"
    )
    transbank_host: str = "https://webpay3gint.transbank.cl"
    pagos_informe_monto: int = Field(default=9990, ge=50, le=10_000_000)
    pagos_publicacion_monto: int = Field(default=8990, ge=50, le=10_000_000)
    pagos_reclamo_email: str = "pagos@servichile.cl"
    pagos_reclamo_whatsapp: str = "+56912345678"
    # Polling TBK de pendientes sin retorno del navegador. 0 = desactivado.
    # En APP_ENV=test no arranca. Min edad: no tocar órdenes aún en checkout.
    pagos_reconciliar_seconds: float = Field(default=120.0, ge=0.0, le=3600.0)
    pagos_reconciliar_min_edad_seg: int = Field(default=180, ge=60, le=7200)
    # Sello de impresión del PDF. Vacío → usa jwt_secret (compat).
    print_token_secret: SecretStr | None = None

    def pades_ca_ruta(self) -> Path:
        ruta = Path(self.pades_ca_pem)
        if not ruta.is_absolute():
            ruta = Path.cwd() / ruta
        return ruta

    def cedula_raiz(self) -> Path:
        ruta = Path(self.cedula_dir)
        if not ruta.is_absolute():
            ruta = Path.cwd() / ruta
        return ruta

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:

        if isinstance(value, str):

            return [o.strip() for o in value.split(",") if o.strip()]

        return value

    @model_validator(mode="after")
    def _derivar_rut_verifier(self) -> Self:
        """test→muestra; con ticket ChileCompra→chilecompra; si no→estricto."""
        if self.app_env == "test":
            self.rut_verifier = "muestra"
        elif (self.chilecompra_ticket or "").strip():
            self.rut_verifier = "chilecompra"
        else:
            self.rut_verifier = "estricto"
        return self

    def secreto_print_token(self) -> str:
        if self.print_token_secret is not None:
            val = self.print_token_secret.get_secret_value().strip()
            if val:
                return val
        return self.jwt_secret.get_secret_value()

    @staticmethod
    def _es_origen_local(valor: str) -> bool:
        v = (valor or "").strip().lower()
        return (
            "://localhost" in v
            or "://127.0.0.1" in v
            or v.startswith("localhost")
            or v.startswith("127.0.0.1")
        )

    @model_validator(mode="after")
    def _exigir_transbank_prod(self) -> Self:
        if self.app_env != "production":
            return self
        host = (self.transbank_host or "").strip().lower()
        commerce = (self.transbank_commerce_code or "").strip()
        api_key = self.transbank_api_key.get_secret_value().strip()
        test_commerce = "597055555532"
        test_key = (
            "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"
        )
        if not host or not commerce or not api_key:
            raise ValueError(
                "En production debe configurar TRANSBANK_HOST, "
                "TRANSBANK_COMMERCE_CODE y TRANSBANK_API_KEY."
            )
        if "webpay3gint" in host:
            raise ValueError(
                "TRANSBANK_HOST de integración (webpay3gint) no permitido "
                "en production. Use el host de producción Transbank."
            )
        if commerce == test_commerce or api_key == test_key:
            raise ValueError(
                "Credenciales Transbank de integración (TEST) no permitidas "
                "en production."
            )
        return self

    @model_validator(mode="after")
    def _exigir_front_prod(self) -> Self:
        if self.app_env != "production":
            return self
        front = (self.public_frontend_url or "").strip()
        if not front or self._es_origen_local(front):
            raise ValueError(
                "En production debe configurar PUBLIC_FRONTEND_URL con el "
                "origen real del front (no localhost/127.0.0.1)."
            )
        origenes = list(self.cors_origins or [])
        if not origenes:
            raise ValueError(
                "En production debe configurar CORS_ORIGINS con al menos "
                "un origen real."
            )
        locales = [o for o in origenes if self._es_origen_local(str(o))]
        if locales:
            raise ValueError(
                "En production CORS_ORIGINS no puede incluir localhost/"
                f"127.0.0.1: {', '.join(locales)}"
            )
        return self

    @model_validator(mode="after")
    def _exigir_redis_y_print_prod(self) -> Self:
        if self.app_env != "production":
            return self
        if not (self.redis_url or "").strip():
            raise ValueError(
                "En production debe configurar REDIS_URL para rate limits "
                "compartidos entre réplicas."
            )
        if self.print_token_secret is None or not self.print_token_secret.get_secret_value().strip():
            raise ValueError(
                "En production debe configurar PRINT_TOKEN_SECRET "
                "(distinto del JWT) para el sello del PDF."
            )
        print_sec = self.print_token_secret.get_secret_value().strip()
        if print_sec == self.jwt_secret.get_secret_value():
            raise ValueError(
                "PRINT_TOKEN_SECRET no puede ser igual a JWT_SECRET en production."
            )
        if len(print_sec) < 32:
            raise ValueError(
                "PRINT_TOKEN_SECRET debe tener al menos 32 caracteres."
            )
        return self


@lru_cache
def obtener_configuracion() -> Configuracion:

    return Configuracion()