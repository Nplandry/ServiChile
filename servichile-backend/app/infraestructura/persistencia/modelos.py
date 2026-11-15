import uuid

from collections.abc import Iterator

from datetime import datetime

from functools import lru_cache

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)

from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.engine import Engine

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from app.configuracion import get_settings

from app.tiempo import ahora_utc


class Base(DeclarativeBase):

    pass


class Usuario(Base):

    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    email: Mapped[str] = mapped_column(String(254), unique=True)

    nombre: Mapped[str] = mapped_column(String(120))

    password_hash: Mapped[str] = mapped_column(Text)

    activo: Mapped[bool] = mapped_column(default=True)

    rut: Mapped[str | None] = mapped_column(String(12), unique=True)

    rut_verificado: Mapped[bool] = mapped_column(default=False)

    telefono: Mapped[str | None] = mapped_column(String(30))

    biometria_verificada: Mapped[bool] = mapped_column(default=False)

    biometria_verificada_en: Mapped[datetime | None] = mapped_column(default=None)

    antecedentes_verificados: Mapped[bool] = mapped_column(default=False)

    antecedentes_verificados_en: Mapped[datetime | None] = mapped_column(default=None)

    antecedentes_anotaciones: Mapped[bool | None] = mapped_column(default=None)

    antecedentes_score: Mapped[int | None] = mapped_column(Integer, default=None)

    xp: Mapped[int] = mapped_column(Integer, default=0)

    creado_en: Mapped[datetime] = mapped_column(default=ahora_utc)

    perfil: Mapped["Perfil | None"] = relationship(
        back_populates="usuario",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )


class UsuarioXpEvento(Base):

    __tablename__ = "usuario_xp_eventos"

    __table_args__ = (
        UniqueConstraint(
            "usuario_id", "evento", name="usuario_xp_eventos_usuario_evento_key"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE")
    )

    evento: Mapped[str] = mapped_column(String(80))

    puntos: Mapped[int] = mapped_column(Integer)

    creado_en: Mapped[datetime] = mapped_column(default=ahora_utc)


class Perfil(Base):

    __tablename__ = "perfiles"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )

    edad: Mapped[int | None] = mapped_column(SmallInteger)

    tipo_cuenta: Mapped[str | None] = mapped_column(String(20))

    preocupacion: Mapped[str | None] = mapped_column(String(20))

    proposito: Mapped[str | None] = mapped_column(String(20))

    actualizado_en: Mapped[datetime] = mapped_column(
        default=ahora_utc, onupdate=ahora_utc
    )

    usuario: Mapped[Usuario] = relationship(back_populates="perfil")


class BusinessEntity(Base):

    __tablename__ = "business_entities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    nombre: Mapped[str] = mapped_column(String(160))

    categoria: Mapped[str] = mapped_column(String(30))

    latitud: Mapped[float | None] = mapped_column(Float)

    longitud: Mapped[float | None] = mapped_column(Float)

    direccion: Mapped[str | None] = mapped_column(String(200))

    descripcion: Mapped[str | None] = mapped_column(Text)

    imagen_url: Mapped[str | None] = mapped_column(String(500))

    logo_url: Mapped[str | None] = mapped_column(String(500))

    requiere_nivel: Mapped[int] = mapped_column(SmallInteger, default=1)

    external_ref: Mapped[str | None] = mapped_column(String(200), unique=True)

    is_claimed: Mapped[bool] = mapped_column(default=False)

    reclamado_por: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )

    telefono: Mapped[str | None] = mapped_column(String(30))

    sitio_web: Mapped[str | None] = mapped_column(String(200))

    rut_empresa: Mapped[str | None] = mapped_column(String(12), default=None)

    creado_en: Mapped[datetime] = mapped_column(default=ahora_utc)

    metricas: Mapped["BusinessReputationMetrics | None"] = relationship(
        back_populates="negocio",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )


class BusinessReputationMetrics(Base):

    __tablename__ = "business_reputation_metrics"

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_entities.id", ondelete="CASCADE"), primary_key=True
    )

    google_rating_avg: Mapped[float | None] = mapped_column(Float)

    google_reviews_count: Mapped[int] = mapped_column(Integer, default=0)

    google_place_nombre: Mapped[str | None] = mapped_column(String(200), default=None)

    sentiment_positive_ratio: Mapped[float | None] = mapped_column(Float)

    response_time_score: Mapped[float | None] = mapped_column(Float)

    final_score: Mapped[float] = mapped_column(Float, default=1.0)

    is_verified_profile: Mapped[bool] = mapped_column(default=False)

    score_ssl_tls: Mapped[float | None] = mapped_column(Float, default=None)

    score_email_auth: Mapped[float | None] = mapped_column(Float, default=None)

    score_puertos: Mapped[float | None] = mapped_column(Float, default=None)

    score_headers_http: Mapped[float | None] = mapped_column(Float, default=None)

    score_stack_vulnerable: Mapped[float | None] = mapped_column(Float, default=None)

    score_blacklist: Mapped[float | None] = mapped_column(Float, default=None)

    score_dnssec: Mapped[float | None] = mapped_column(Float, default=None)

    score_subdominios: Mapped[float | None] = mapped_column(Float, default=None)

    score_whois: Mapped[float | None] = mapped_column(Float, default=None)

    score_uptime: Mapped[float | None] = mapped_column(Float, default=None)

    score_cookies: Mapped[float | None] = mapped_column(Float, default=None)

    score_politica_privacidad: Mapped[float | None] = mapped_column(Float, default=None)

    score_terminos: Mapped[float | None] = mapped_column(Float, default=None)

    score_sla: Mapped[float | None] = mapped_column(Float, default=None)

    docs_legales_razones: Mapped[dict | None] = mapped_column(JSONB, default=None)

    score_mercado_publico: Mapped[float | None] = mapped_column(Float, default=None)

    score_sii: Mapped[float | None] = mapped_column(Float, default=None)

    score_cmf: Mapped[float | None] = mapped_column(Float, default=None)

    score_incidentes: Mapped[float | None] = mapped_column(Float, default=None)

    incidentes_razones: Mapped[list | None] = mapped_column(JSONB, default=None)

    ciber_escaneado_en: Mapped[datetime | None] = mapped_column(default=None)

    actualizado_en: Mapped[datetime] = mapped_column(
        default=ahora_utc, onupdate=ahora_utc
    )

    negocio: Mapped[BusinessEntity] = relationship(back_populates="metricas")


class CmfInstitucion(Base):

    __tablename__ = "cmf_instituciones"

    rut: Mapped[str] = mapped_column(String(12), primary_key=True)

    codigo: Mapped[str] = mapped_column(String(8))

    nombre: Mapped[str] = mapped_column(String(200), default="")

    direccion: Mapped[str | None] = mapped_column(String(300), default=None)

    web: Mapped[str | None] = mapped_column(String(200), default=None)

    sucursales: Mapped[int | None] = mapped_column(Integer, default=None)

    empleados: Mapped[int | None] = mapped_column(Integer, default=None)


class CmfIndiceMeta(Base):

    __tablename__ = "cmf_indice_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    sincronizado_en: Mapped[datetime | None] = mapped_column(default=None)

    filas: Mapped[int] = mapped_column(Integer, default=0)

    fuente: Mapped[str | None] = mapped_column(String(200), default=None)


class Reserva(Base):

    __tablename__ = "reservas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE")
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_entities.id", ondelete="CASCADE")
    )

    estado: Mapped[str] = mapped_column(String(20), default="reservada")

    qr_token: Mapped[str] = mapped_column(String(64), unique=True)

    creado_en: Mapped[datetime] = mapped_column(default=ahora_utc)

    actualizado_en: Mapped[datetime] = mapped_column(
        default=ahora_utc, onupdate=ahora_utc
    )


@lru_cache
def get_engine() -> Engine:

    return create_engine(get_settings().database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:

    session = sessionmaker(bind=get_engine(), expire_on_commit=False)()

    try:

        yield session

    finally:

        session.close()
