from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
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


class Settings(BaseSettings):

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

    rut_verifier: Literal["muestra"] = "muestra"

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

    # Rater empresa (Places + ChileCompra + crawler). En test → scores fijos.
    # Places/ChileCompra: sin key/ticket → muestra; con key/ticket → produccion.
    rater_mode: Literal["muestra", "produccion"] = "muestra"
    rater_budget_seconds: float = Field(default=2.0, ge=0.5, le=30.0)
    # Refresco en background (minutos). 0 = desactivado. En APP_ENV=test no arranca.
    rater_refresh_minutes: float = Field(default=30.0, ge=0.0, le=24 * 60)
    chilecompra_ticket: str = ""
    google_places_api_key: str = ""

    @property
    def chilecompra_mode(self) -> Literal["muestra", "produccion"]:
        return "produccion" if (self.chilecompra_ticket or "").strip() else "muestra"

    @property
    def places_mode(self) -> Literal["muestra", "produccion"]:
        return "produccion" if (self.google_places_api_key or "").strip() else "muestra"

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


@lru_cache
def get_settings() -> Settings:

    return Settings()
