import uuid

from collections.abc import Iterator

from datetime import date, datetime

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

    biometria_ruta: Mapped[str | None] = mapped_column(String(260), default=None)

    biometria_sha256: Mapped[str | None] = mapped_column(String(64), default=None)

    biometria_bytes: Mapped[int | None] = mapped_column(Integer, default=None)

    biometria_ancho: Mapped[int | None] = mapped_column(Integer, default=None)

    biometria_alto: Mapped[int | None] = mapped_column(Integer, default=None)

    biometria_content_type: Mapped[str | None] = mapped_column(String(40), default=None)

    biometria_retener_hasta: Mapped[datetime | None] = mapped_column(default=None)

    cedula_verificada: Mapped[bool] = mapped_column(default=False)

    cedula_verificada_en: Mapped[datetime | None] = mapped_column(default=None)

    cedula_ruta: Mapped[str | None] = mapped_column(String(260), default=None)

    cedula_sha256: Mapped[str | None] = mapped_column(String(64), default=None)

    cedula_bytes: Mapped[int | None] = mapped_column(Integer, default=None)

    cedula_ancho: Mapped[int | None] = mapped_column(Integer, default=None)

    cedula_alto: Mapped[int | None] = mapped_column(Integer, default=None)

    cedula_content_type: Mapped[str | None] = mapped_column(String(40), default=None)

    cedula_retener_hasta: Mapped[datetime | None] = mapped_column(default=None)

    cedula_score: Mapped[int | None] = mapped_column(Integer, default=None)

    cedula_rut_ocr: Mapped[str | None] = mapped_column(String(12), default=None)

    antecedentes_verificados: Mapped[bool] = mapped_column(default=False)

    antecedentes_verificados_en: Mapped[datetime | None] = mapped_column(default=None)

    antecedentes_anotaciones: Mapped[bool | None] = mapped_column(default=None)

    antecedentes_score: Mapped[int | None] = mapped_column(Integer, default=None)

    antecedentes_pades: Mapped[bool] = mapped_column(default=False)

    antecedentes_entidad_emisora: Mapped[str | None] = mapped_column(default=None)

    antecedentes_fecha_emision: Mapped[date | None] = mapped_column(default=None)

    antecedentes_sha256: Mapped[str | None] = mapped_column(default=None)

    antecedentes_glosa: Mapped[str | None] = mapped_column(default=None)

    aval_verificado: Mapped[bool] = mapped_column(default=False)

    aval_verificado_en: Mapped[datetime | None] = mapped_column(default=None)

    aval_score: Mapped[int | None] = mapped_column(Integer, default=None)

    aval_tipo: Mapped[str | None] = mapped_column(String(20), default=None)

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

    docs_empresa: Mapped[dict | None] = mapped_column(JSONB, default=dict)

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

    final_score: Mapped[float] = mapped_column(Float, default=0.0)

    rater_escaneado_en: Mapped[datetime | None] = mapped_column(default=None)

    observables: Mapped[list | None] = mapped_column(JSONB, default=None)

    actualizado_en: Mapped[datetime] = mapped_column(
        default=ahora_utc, onupdate=ahora_utc
    )

    negocio: Mapped[BusinessEntity] = relationship(back_populates="metricas")


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


class PadesDocumentHash(Base):
    __tablename__ = "pades_document_hashes"

    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    scope: Mapped[str] = mapped_column(String(40))
    tipo: Mapped[str | None] = mapped_column(String(64), default=None)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), default=None
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("business_entities.id", ondelete="SET NULL"), default=None
    )
    creado_en: Mapped[datetime] = mapped_column(default=ahora_utc)


@lru_cache
def get_engine() -> Engine:

    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:

    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:

    session = get_sessionmaker()()

    try:

        yield session

    finally:

        session.close()
