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


@lru_cache
def obtener_configuracion() -> Configuracion:

    return Configuracion()