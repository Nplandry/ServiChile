"""Esquemas de negocios, docs empresa y reputación."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.esquemas.comunes import CategoriaNegocio, telefono_opcional

class NegocioEnMapaOut(BaseModel):
    """Listado público: sin RUT, teléfono, sitio ni docs."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    nombre: str

    categoria: CategoriaNegocio

    latitud: float | None

    longitud: float | None

    direccion: str | None

    descripcion: str | None

    imagen_url: str

    logo_url: str | None = None

    logo_texto: str

    cta_texto: str

    indice_transparencia: float

    requiere_nivel: Literal[1, 2]

    is_claimed: bool = False

    indice_pct: int = Field(default=0, ge=0, le=100)


class NegocioTitularOut(NegocioEnMapaOut):
    """Alta /mias / PATCH: datos de contacto y docs del titular."""

    docs_empresa: dict[str, "DocEmpresaMetaOut"] | None = None

    rut_empresa: str | None = None

    telefono: str | None = None

    sitio_web: str | None = None


class NegocioRutIn(BaseModel):

    model_config = ConfigDict(extra="forbid")

    rut_empresa: str = Field(min_length=3, max_length=20)


class NegocioActualizarIn(BaseModel):

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=160)

    categoria: CategoriaNegocio

    direccion: str = Field(min_length=3, max_length=200)

    descripcion: str | None = Field(default=None, max_length=2000)

    telefono: str | None = Field(default=None, max_length=30)

    sitio_web: str | None = Field(default=None, max_length=200)

    imagen_url: str | None = Field(default=None, max_length=500)

    logo_url: str | None = Field(default=None, max_length=500)

    rut_empresa: str | None = Field(
        default=None, min_length=3, max_length=20
    )

    @field_validator("telefono")
    @classmethod
    def _telefono_negocio_act(cls, value: str | None) -> str | None:
        return telefono_opcional(value)

    @field_validator("imagen_url", "logo_url")
    @classmethod
    def url_http_act(cls, v: str | None) -> str | None:
        if v is None:
            return None
        url = v.strip()
        if not url:
            return None
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("La URL debe comenzar con http:// o https://")
        return url


class DocEmpresaFlagOut(BaseModel):
    """Flags públicos de un documento (sin hashes ni glosas)."""

    verificado: bool = False
    verificado_en: str | None = None


class DocEmpresaMetaOut(BaseModel):
    """Metadatos de un documento de empresa (titular / post-upload)."""

    model_config = ConfigDict(extra="allow")

    verificado: bool = False
    verificado_en: str | None = None
    score: int | None = None
    senales: list[str] = Field(default_factory=list)
    verificado_criptograficamente: bool | None = None
    entidad_emisora: str | None = None
    fecha_emision: str | None = None
    sha256_hash: str | None = None
    glosa: str | None = None
    rut_detectado: str | None = None
    grupo: str | None = None
    documento_tipo: str | None = None

    @field_validator("grupo", mode="before")
    @classmethod
    def _grupo_a_texto(cls, value: object) -> str | None:
        if value is None:
            return None
        return str(value)


class DocEmpresaOut(BaseModel):

    business_id: UUID

    tipo: str

    verificado: bool

    score: int | None = None

    senales: list[str] = Field(default_factory=list)

    docs_empresa: dict[str, DocEmpresaMetaOut] = Field(default_factory=dict)

    indice_transparencia: float = 0.0

    indice_pct: int = Field(default=0, ge=0, le=100)

    docs_verificados: int = 0

    docs_total: int = 0

    verificado_criptograficamente: bool = False

    entidad_emisora: str | None = None

    fecha_emision: str | None = None

    sha256_hash: str | None = None

    glosa: str | None = None

    motivo: str = "Documento de empresa validado. El PDF no se almacenó."


class ObservableSenalOut(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: str

    etiqueta: str

    detalle: str

    score: int = Field(ge=0, le=100)

    peso: str = "3.0%"

    grupo: Literal["ciber", "operativa", "contractual", "legal", "documentos"] = (
        "operativa"
    )

    razones: list[str] = Field(default_factory=list)


class ReputacionOut(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    business_id: UUID

    nombre: str

    categoria: CategoriaNegocio

    google_rating_avg: float | None

    google_reviews_count: int

    indice_transparencia: float

    indice_pct: int = Field(default=0, ge=0, le=100)

    docs_verificados: int = 0

    docs_total: int = 0

    docs_empresa: dict[str, DocEmpresaFlagOut] | None = None

    actualizado_en: datetime

    observables: list[ObservableSenalOut] = Field(default_factory=list)

    descargo: str = (
        "Índice global a partir de señales públicas (ficha, sitio, "
        "compras públicas, etc.). No constituye un juicio sobre la calidad del servicio."
    )


class NegocioCrearIn(BaseModel):

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=160)

    categoria: CategoriaNegocio

    direccion: str = Field(min_length=3, max_length=200)

    descripcion: str | None = Field(default=None, max_length=2000)

    telefono: str | None = Field(default=None, max_length=30)

    sitio_web: str | None = Field(default=None, max_length=200)

    imagen_url: str | None = Field(default=None, max_length=500)

    logo_url: str | None = Field(default=None, max_length=500)

    rut_empresa: str | None = Field(
        default=None, min_length=3, max_length=20
    )

    @field_validator("telefono")
    @classmethod
    def _telefono_negocio(cls, value: str | None) -> str | None:

        return telefono_opcional(value)

    @field_validator("imagen_url", "logo_url")
    @classmethod
    def url_http(cls, v: str | None) -> str | None:

        if v is None:

            return None

        url = v.strip()

        if not url:

            return None

        if not (url.startswith("http://") or url.startswith("https://")):

            raise ValueError("La URL debe comenzar con http:// o https://")

        return url


