"""DTOs de entrada y salida de la API."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Categoria = Literal["embargo-falso", "seguros", "portabilidad"]
Preocupacion = Literal["embargo", "seguros", "telecom", "otro"]
Proposito = Literal["autoinformarse", "asesorar", "investigar", "trabajo"]


# Perfil del usuario. Todos opcionales. Ver Pasaporte de Confianza en README.
class PerfilIn(BaseModel):
    """Entrada de PATCH /v1/perfil. Solo cambian los campos enviados."""

    model_config = ConfigDict(extra="forbid")

    edad: int | None = Field(default=None, ge=14, le=120)
    # RUT con dígito verificador. Se valida con módulo 11 y luego con el verificador externo.
    rut: str | None = Field(default=None, min_length=3, max_length=15)
    telefono: str | None = Field(default=None, pattern=r"^\+?[0-9 ]{6,30}$")
    # DEPRECADOS: se aceptan durante la transición y se eliminan en una migración posterior.
    preocupacion: Preocupacion | None = None
    proposito: Proposito | None = None


class PerfilRegistroIn(BaseModel):
    """Perfil opcional al crear la cuenta. Solo acepta datos básicos; el RUT se verifica después."""

    model_config = ConfigDict(extra="forbid")

    edad: int | None = Field(default=None, ge=14, le=120)
    # DEPRECADOS: se aceptan durante la transición y se eliminan en una migración posterior.
    preocupacion: Preocupacion | None = None
    proposito: Proposito | None = None


class InmobiliariaScoring(BaseModel):
    """Resultado del Nivel 2 (arriendo). Solo puntaje y fecha: el PDF nunca se guarda."""

    estado_verificacion: Literal["pendiente", "verificado", "rechazado"]
    score_financiero: int | None = Field(default=None, ge=0, le=1000)
    actualizado_en: datetime


class PerfilOut(BaseModel):
    """Estado del usuario dentro del Pasaporte de Confianza."""

    model_config = ConfigDict(from_attributes=True)

    rut_verificado: bool = False
    telefono: str | None = None
    nivel_pasaporte: Literal[1, 2] = 1
    estado_pasaporte: Literal["basico", "pendiente", "verificado", "rechazado"] = "basico"
    # Nivel 1: asistencias / reservas cerradas x 100. Null si aún no hay reservas cerradas.
    score_confiabilidad: float | None = None
    # Nivel 2: null si el usuario nunca subió documentos de arriendo.
    inmobiliaria_scoring: InmobiliariaScoring | None = None
    edad: int | None = None
    # DEPRECADOS: null durante la transición.
    preocupacion: Preocupacion | None = None
    proposito: Proposito | None = None


class RegistroIn(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    perfil: PerfilRegistroIn | None = None

    @field_validator("nombre")
    @classmethod
    def _strip_nombre(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Ingrese su nombre completo.")
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    nombre: str
    creado_en: datetime
    perfil: PerfilOut = Field(default_factory=PerfilOut)

    @field_validator("perfil", mode="before")
    @classmethod
    def _perfil_vacio(cls, value: object) -> object:
        # Usuarios sin fila en perfiles devuelven un perfil vacío, no null: el frontend no distingue casos
        return PerfilOut() if value is None else value


class ConsultaIn(BaseModel):
    pregunta: str = Field(min_length=5, max_length=2000)
    categoria: Categoria | None = None


class Fuente(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    n: int
    titulo: str
    url: str | None
    pagina: int | None


class ConsultaOut(BaseModel):
    id: UUID
    respuesta: str
    fuentes: list[Fuente]
    requiere_humano: bool
    creado_en: datetime


class ConsultaResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    categoria: str | None
    pregunta_redactada: str
    requiere_humano: bool
    creado_en: datetime


# Categorías de comercio del directorio. Ampliar según convenios/zonas.
CategoriaNegocio = Literal[
    "gimnasio", "clinica-dental", "comercio", "restaurante", "automotriz", "arriendo", "evento", "otro"
]


class NegocioEnMapaOut(BaseModel):
    """Datos mínimos para pintar un negocio en el marketplace geolocalizado.

    Incluye el Índice de Transparencia precalculado para no recalcular por cada pin.
    No expone datos crudos de reseñas (blindaje legal, ver reputacion.py).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    categoria: CategoriaNegocio
    latitud: float | None
    longitud: float | None
    direccion: str | None
    descripcion: str | None
    indice_transparencia: float
    is_verified_profile: bool
    # Nivel de pasaporte requerido para la acción (p. ej. arriendos o eventos VIP piden nivel 2).
    requiere_nivel: Literal[1, 2]


class ReputacionOut(BaseModel):
    """Indicadores estadísticos agregados y el Índice de Transparencia.

    Blindaje legal: solo métricas públicas y el índice algorítmico. Nunca se
    exponen textos de reseñas ni juicios de valor sobre la calidad del servicio.
    """

    model_config = ConfigDict(from_attributes=True)

    business_id: UUID
    nombre: str
    categoria: CategoriaNegocio
    is_verified_profile: bool
    estado_perfil: Literal["Perfil Verificado", "Perfil No Verificado / Índice Básico"]
    google_rating_avg: float | None
    google_reviews_count: int
    sentiment_positive_ratio: float | None
    response_time_score: float | None
    indice_transparencia: float
    actualizado_en: datetime
    # Texto fijo que recuerda la naturaleza del índice (anti-difamación).
    descargo: str = (
        "Índice algorítmico calculado sobre datos públicos y nivel de verificación. "
        "No constituye un juicio sobre la calidad del servicio."
    )


class ClaimIn(BaseModel):
    """Solicitud del dueño para reclamar su perfil (Derecho a Réplica)."""

    model_config = ConfigDict(extra="forbid")

    # Documento de verificación de identidad/titularidad (p. ej. RUT de la empresa).
    documento_verificacion: str = Field(min_length=3, max_length=120)
    # Datos oficiales que el dueño quiere rectificar al reclamar (opcionales).
    nombre: str | None = Field(default=None, min_length=2, max_length=160)
    telefono: str | None = Field(default=None, max_length=30)
    sitio_web: str | None = Field(default=None, max_length=200)


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: UUID
    is_claimed: bool
    is_verified_profile: bool
    reclamado_por: UUID
    mensaje: str = (
        "Perfil reclamado. Ahora puede administrar y rectificar la información de su negocio."
    )


class ReservaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: UUID


class ReservaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    estado: Literal["reservada", "asistido", "no_show", "cancelada"]
    qr_token: str
    creado_en: datetime


class CheckinIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qr_token: str = Field(min_length=10, max_length=64)
