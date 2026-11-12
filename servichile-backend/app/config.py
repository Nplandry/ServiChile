"""Configuración leída desde variables de entorno (o archivo .env en desarrollo)."""
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"

    database_url: str = "postgresql+psycopg://servichile:servichile@localhost:5432/servichile"

    jwt_secret: SecretStr = Field(min_length=32)
    jwt_expires_minutes: int = Field(default=60, ge=5, le=1440)
    # Mi QR: token de identidad de corta vida (firmado, distinto del JWT de sesión).
    mi_qr_expires_minutes: int = Field(default=15, ge=1, le=120)

    # CORS: orígenes del frontend separados por coma
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5500"]

    # Proveedor de IA: "gemini" usa Vertex AI, "fake" responde sin llamar a ningún modelo
    llm_provider: Literal["gemini", "fake"] = "fake"
    # Verificador de RUT y extractor de PDF. "fake" no llama a ningún servicio externo.
    # Cuando existan los proveedores reales, se agregan aquí y se construyen en deps.py.
    rut_verifier: Literal["fake"] = "fake"
    pdf_extractor: Literal["fake"] = "fake"
    gcp_project: str | None = None
    gcp_proyectos_prohibidos: Annotated[list[str], NoDecode] = []
    gcp_location: str = "southamerica-east1"
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_max_distance: float = Field(default=0.5, gt=0, le=2)

    # Rate limiting: vacío usa memoria del proceso (solo desarrollo)
    redis_url: str | None = None
    login_rate_per_minute: int = 5
    login_ip_rate_per_minute: int = 20
    consulta_rate_per_minute: int = 10
    # true solo detrás de un proxy de confianza (Cloud Run). Si es true sin proxy, cualquiera puede falsear la IP.
    trust_proxy: bool = False

    @field_validator("cors_origins", "gcp_proyectos_prohibidos", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
