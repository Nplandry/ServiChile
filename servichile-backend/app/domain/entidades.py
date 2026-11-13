from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Perfil:
    edad: int | None = None
    tipo_cuenta: str | None = None
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
    biometria_verificada: bool = False
    biometria_verificada_en: datetime | None = None
    xp: int = 0
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
    score_ssl_tls: float | None = None
    score_email_auth: float | None = None
    score_puertos: float | None = None
    score_headers_http: float | None = None
    score_stack_vulnerable: float | None = None
    score_blacklist: float | None = None
    score_dnssec: float | None = None
    score_subdominios: float | None = None
    score_whois: float | None = None
    score_uptime: float | None = None
    ciber_escaneado_en: datetime | None = None
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
    imagen_url: str | None = None
    logo_url: str | None = None
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
class EstadoPasaporte:
    rut_verificado: bool
    telefono: str | None
    nivel_pasaporte: int
    estado_pasaporte: str
    score_confiabilidad: float | None
    edad: int | None
    tipo_cuenta: str | None = None
    biometria_verificada: bool = False
    biometria_verificada_en: datetime | None = None
    xp: int = 0
    nivel_xp: int = 1

@dataclass
class ObservableCiber:
    id: str
    etiqueta: str
    detalle: str
    score: int
    peso: str
    grupo: str

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
    observables_ciber: list[ObservableCiber] = field(default_factory=list)

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
    imagen_url: str
    logo_url: str | None
    logo_texto: str
    cta_texto: str
    indice_transparencia: float
    is_verified_profile: bool
    requiere_nivel: int
    is_claimed: bool = False

@dataclass
class TokenEmitido:
    access_token: str
    expires_in: int

@dataclass
class ReporteEmitido:
    payload: str
    token: str
    expires_in: int
    expires_at: datetime
    nombre: str
    email: str
    nivel_pasaporte: int
    estado_pasaporte: str
    score_confiabilidad: float | None
    rut_verificado: bool
    xp: int = 0
    nivel_xp: int = 1
    tipo_cuenta: str | None = None

@dataclass
class ReporteValidado:
    es_propio: bool
    nombre: str
    nivel_pasaporte: int
    estado_pasaporte: str
    score_confiabilidad: float | None
    rut_verificado: bool
    expires_at: datetime
    xp: int = 0
    nivel_xp: int = 1
    tipo_cuenta: str | None = None
