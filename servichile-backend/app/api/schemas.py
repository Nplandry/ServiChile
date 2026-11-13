from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
Preocupacion = Literal['embargo', 'seguros', 'telecom', 'otro']
Proposito = Literal['autoinformarse', 'asesorar', 'investigar', 'trabajo']
TipoCuenta = Literal['persona', 'empresa']

class PerfilIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    edad: int | None = Field(default=None, ge=14, le=120)
    tipo_cuenta: TipoCuenta | None = None
    rut: str | None = Field(default=None, min_length=3, max_length=15)
    telefono: str | None = Field(default=None, pattern='^\\+?[0-9 ]{6,30}$')
    preocupacion: Preocupacion | None = None
    proposito: Proposito | None = None

class PerfilRegistroIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tipo_cuenta: TipoCuenta
    edad: int | None = Field(default=None, ge=14, le=120)
    preocupacion: Preocupacion | None = None
    proposito: Proposito | None = None

class PerfilOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rut_verificado: bool = False
    telefono: str | None = None
    nivel_pasaporte: Literal[1] = 1
    estado_pasaporte: Literal['basico', 'pendiente', 'verificado', 'rechazado'] = 'basico'
    score_confiabilidad: float | None = None
    biometria_verificada: bool = False
    biometria_verificada_en: datetime | None = None
    xp: int = Field(default=0, ge=0)
    nivel_xp: int = Field(default=1, ge=1, le=3)
    edad: int | None = None
    tipo_cuenta: TipoCuenta | None = None
    preocupacion: Preocupacion | None = None
    proposito: Proposito | None = None

class BiometriaOut(BaseModel):
    biometria_verificada: bool
    biometria_verificada_en: datetime
    xp: int = Field(default=0, ge=0)
    nivel_xp: int = Field(default=1, ge=1, le=3)
    mensaje: str = 'Verificación biométrica completada. La foto no se almacenó.'

class RegistroIn(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    perfil: PerfilRegistroIn

    @field_validator('nombre')
    @classmethod
    def _strip_nombre(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError('Ingrese su nombre completo.')
        return value

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class TokenOut(BaseModel):
    access_token: str
    token_type: Literal['bearer'] = 'bearer'
    expires_in: int

class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    nombre: str
    creado_en: datetime
    perfil: PerfilOut = Field(default_factory=PerfilOut)

    @field_validator('perfil', mode='before')
    @classmethod
    def _perfil_vacio(cls, value: object) -> object:
        return PerfilOut() if value is None else value

CategoriaNegocio = Literal['tecnologia', 'industria', 'construccion', 'servicios-profesionales', 'logistica']

class NegocioEnMapaOut(BaseModel):
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
    is_verified_profile: bool
    requiere_nivel: Literal[1, 2]
    is_claimed: bool = False

class ObservableCiberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    etiqueta: str
    detalle: str
    score: int = Field(ge=0, le=100)
    peso: str = '3.0%'
    grupo: Literal['ciber', 'operativa'] = 'ciber'

class ReputacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    business_id: UUID
    nombre: str
    categoria: CategoriaNegocio
    is_verified_profile: bool
    estado_perfil: Literal['Perfil Verificado', 'Perfil No Verificado / Índice Básico']
    google_rating_avg: float | None
    google_reviews_count: int
    sentiment_positive_ratio: float | None
    response_time_score: float | None
    indice_transparencia: float
    actualizado_en: datetime
    observables_ciber: list[ObservableCiberOut] = Field(default_factory=list)
    descargo: str = 'Índice algorítmico calculado sobre datos públicos y nivel de verificación. No constituye un juicio sobre la calidad del servicio.'

class NegocioCrearIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nombre: str = Field(min_length=2, max_length=160)
    categoria: CategoriaNegocio
    direccion: str = Field(min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    telefono: str | None = Field(default=None, max_length=30)
    sitio_web: str | None = Field(default=None, max_length=200)
    imagen_url: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    documento_verificacion: str | None = Field(default=None, min_length=3, max_length=120)

    @field_validator('imagen_url', 'logo_url')
    @classmethod
    def url_http(cls, v: str | None) -> str | None:
        if v is None:
            return None
        url = v.strip()
        if not url:
            return None
        if not (url.startswith('http://') or url.startswith('https://')):
            raise ValueError('La URL debe comenzar con http:// o https://')
        return url

class ClaimIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    documento_verificacion: str = Field(min_length=3, max_length=120)
    nombre: str | None = Field(default=None, min_length=2, max_length=160)
    telefono: str | None = Field(default=None, max_length=30)
    sitio_web: str | None = Field(default=None, max_length=200)

class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    business_id: UUID
    is_claimed: bool
    is_verified_profile: bool
    reclamado_por: UUID
    mensaje: str = 'Perfil reclamado. Ahora puede administrar y rectificar la información de su negocio.'

class ReservaIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    business_id: UUID

class ReservaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    business_id: UUID
    estado: Literal['reservada', 'asistido', 'no_show', 'cancelada']
    qr_token: str
    creado_en: datetime

class CheckinIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    qr_token: str = Field(min_length=10, max_length=64)

class EliminarCuentaIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    password: str = Field(min_length=1, max_length=128)

class ReporteOut(BaseModel):
    payload: str
    token: str
    expires_in: int
    expires_at: datetime
    nombre: str
    email: EmailStr
    nivel_pasaporte: Literal[1] = 1
    estado_pasaporte: Literal['basico', 'pendiente', 'verificado', 'rechazado']
    score_confiabilidad: float | None = None
    rut_verificado: bool = False
    xp: int = 0
    nivel_xp: int = Field(default=1, ge=1, le=3)
    tipo_cuenta: TipoCuenta | None = None

class ReporteValidarIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    payload: str = Field(min_length=10, max_length=2048)

class ReporteValidacionOut(BaseModel):
    es_propio: bool
    nombre: str
    nivel_pasaporte: Literal[1] = 1
    estado_pasaporte: Literal['basico', 'pendiente', 'verificado', 'rechazado']
    score_confiabilidad: float | None = None
    rut_verificado: bool = False
    expires_at: datetime
    xp: int = 0
    nivel_xp: int = Field(default=1, ge=1, le=3)
    tipo_cuenta: TipoCuenta | None = None
