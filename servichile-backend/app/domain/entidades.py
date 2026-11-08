"""Entidades y resultados del dominio. Dataclasses puras: sin SQLAlchemy, Pydantic ni FastAPI.

Los repositorios convierten los modelos ORM a estas entidades, y los servicios solo
trabajan con ellas. La API convierte los resultados a schemas de respuesta.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Perfil:
    edad: int | None = None
    # DEPRECADOS: se guardan durante la transición y no se devuelven por la API.
    preocupacion: str | None = None
    proposito: str | None = None


@dataclass
class Usuario:
    id: uuid.UUID
    email: str
    nombre: str
    password_hash: str
    activo: bool = True
    rut: str | None = None
    rut_verificado: bool = False
    telefono: str | None = None
    creado_en: datetime | None = None
    perfil: Perfil | None = None


@dataclass
class Metricas:
    business_id: uuid.UUID
    google_rating_avg: float | None = None
    google_reviews_count: int = 0
    sentiment_positive_ratio: float | None = None
    response_time_score: float | None = None
    final_score: float = 0.0
    is_verified_profile: bool = False
    actualizado_en: datetime | None = None


@dataclass
class Negocio:
    id: uuid.UUID
    nombre: str
    categoria: str
    latitud: float | None = None
    longitud: float | None = None
    direccion: str | None = None
    descripcion: str | None = None
    requiere_nivel: int = 1
    is_claimed: bool = False
    reclamado_por: uuid.UUID | None = None
    telefono: str | None = None
    sitio_web: str | None = None
    metricas: Metricas | None = None


@dataclass
class Reserva:
    id: uuid.UUID
    usuario_id: uuid.UUID
    business_id: uuid.UUID
    estado: str
    qr_token: str
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None


@dataclass
class VerificacionArriendo:
    id: uuid.UUID
    usuario_id: uuid.UUID
    estado: str
    score: int | None
    verificado_en: datetime | None
    creado_en: datetime | None


@dataclass
class Fuente:
    n: int
    titulo: str
    url: str | None
    pagina: int | None


@dataclass
class Consulta:
    id: uuid.UUID
    usuario_id: uuid.UUID
    categoria: str | None
    pregunta_redactada: str
    respuesta: str
    fuentes: list[dict] = field(default_factory=list)
    requiere_humano: bool = False
    creado_en: datetime | None = None



@dataclass
class EstadoPasaporte:
    rut_verificado: bool
    telefono: str | None
    nivel_pasaporte: int
    estado_pasaporte: str
    score_confiabilidad: float | None
    arriendo: VerificacionArriendo | None
    edad: int | None


@dataclass
class ResultadoDocumento:
    estado_verificacion: str
    score_financiero: int | None
    actualizado_en: datetime


@dataclass
class Reputacion:
    business_id: uuid.UUID
    nombre: str
    categoria: str
    is_verified_profile: bool
    estado_perfil: str
    google_rating_avg: float | None
    google_reviews_count: int
    sentiment_positive_ratio: float | None
    response_time_score: float | None
    indice_transparencia: float
    actualizado_en: datetime | None


@dataclass
class ResultadoReclamo:
    business_id: uuid.UUID
    is_claimed: bool
    is_verified_profile: bool
    reclamado_por: uuid.UUID


@dataclass
class NegocioEnMapa:
    id: uuid.UUID
    nombre: str
    categoria: str
    latitud: float | None
    longitud: float | None
    direccion: str | None
    descripcion: str | None
    indice_transparencia: float
    is_verified_profile: bool
    requiere_nivel: int


@dataclass
class ResultadoConsulta:
    id: uuid.UUID
    respuesta: str
    fuentes: list[Fuente]
    requiere_humano: bool
    creado_en: datetime | None


@dataclass
class TokenEmitido:
    access_token: str
    expires_in: int
