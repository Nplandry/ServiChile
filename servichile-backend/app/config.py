from functools import lru_cache

from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator

from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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

    ciber_sonda: Literal["fake", "live"] = "fake"

    chilecompra_ticket: SecretStr | None = None

    chilecompra_mode: Literal["auto", "fake", "live", "off"] = "auto"

    apigateway_token: SecretStr | None = None

    sii_mode: Literal["auto", "fake", "live", "off"] = "auto"

    cmf_api_key: SecretStr | None = None

    cmf_mode: Literal["auto", "fake", "live", "off"] = "auto"

    incidentes_mode: Literal["auto", "fake", "live", "off"] = "auto"

    tavily_api_key: SecretStr | None = None

    google_places_api_key: SecretStr | None = None

    places_mode: Literal["auto", "fake", "live", "off"] = "auto"

    rut_verifier: Literal["fake"] = "fake"

    redis_url: str | None = None

    login_rate_per_minute: int = 5

    login_ip_rate_per_minute: int = 20

    trust_proxy: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:

        if isinstance(value, str):

            return [o.strip() for o in value.split(",") if o.strip()]

        return value


@lru_cache
def get_settings() -> Settings:

    return Settings()
