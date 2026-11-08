"""Conexión a PostgreSQL y modelos ORM. La fuente de verdad del esquema es db/init_script.sql."""
import uuid
from collections.abc import Iterator
from datetime import date, datetime
from functools import lru_cache

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Float, ForeignKey, Integer, SmallInteger, String, Text, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.config import get_settings
from app.utils import ahora_utc

EMBEDDING_DIM = get_settings().embedding_dim


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(default=True)
    # Pasaporte de Confianza. El RUT se guarda normalizado, p. ej. "12345678-K".
    rut: Mapped[str | None] = mapped_column(String(12), unique=True)
    rut_verificado: Mapped[bool] = mapped_column(default=False)
    telefono: Mapped[str | None] = mapped_column(String(30))
    creado_en: Mapped[datetime] = mapped_column(default=ahora_utc)

    perfil: Mapped["Perfil | None"] = relationship(
        back_populates="usuario", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )


class Perfil(Base):
    __tablename__ = "perfiles"

    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    edad: Mapped[int | None] = mapped_column(SmallInteger)
    preocupacion: Mapped[str | None] = mapped_column(String(20))
    proposito: Mapped[str | None] = mapped_column(String(20))
    actualizado_en: Mapped[datetime] = mapped_column(default=ahora_utc, onupdate=ahora_utc)

    usuario: Mapped[Usuario] = relationship(back_populates="perfil")


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    titulo: Mapped[str] = mapped_column(String(300))
    url_fuente: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str | None] = mapped_column(String(40))
    publicado_en: Mapped[date | None]
    hash_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    cargado_en: Mapped[datetime] = mapped_column(default=ahora_utc)


class Fragmento(Base):
    __tablename__ = "fragmentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documentos.id", ondelete="CASCADE"))
    pagina: Mapped[int | None]
    orden: Mapped[int]
    contenido: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))


class Consulta(Base):
    __tablename__ = "consultas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    categoria: Mapped[str | None] = mapped_column(String(40))
    pregunta_redactada: Mapped[str] = mapped_column(Text)
    respuesta: Mapped[str] = mapped_column(Text)
    fuentes: Mapped[list] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=list)
    requiere_humano: Mapped[bool] = mapped_column(default=False)
    creado_en: Mapped[datetime] = mapped_column(default=ahora_utc)


class BusinessEntity(Base):
    """Datos estáticos de un comercio del directorio de transparencia."""

    __tablename__ = "business_entities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(160))
    categoria: Mapped[str] = mapped_column(String(30))
    latitud: Mapped[float | None] = mapped_column(Float)
    longitud: Mapped[float | None] = mapped_column(Float)
    direccion: Mapped[str | None] = mapped_column(String(200))
    descripcion: Mapped[str | None] = mapped_column(Text)
    # Nivel de Pasaporte requerido para la acción (1 básico, 2 verificado: arriendos y eventos VIP).
    requiere_nivel: Mapped[int] = mapped_column(SmallInteger, default=1)
    # Fuente externa (p. ej. place_id de Google Maps) para la ingesta periódica.
    external_ref: Mapped[str | None] = mapped_column(String(200), unique=True)
    # Perfil reclamado por su dueño (Derecho a Réplica).
    is_claimed: Mapped[bool] = mapped_column(default=False)
    # Usuario de la plataforma que reclamó y administra el perfil.
    reclamado_por: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    telefono: Mapped[str | None] = mapped_column(String(30))
    sitio_web: Mapped[str | None] = mapped_column(String(200))
    creado_en: Mapped[datetime] = mapped_column(default=ahora_utc)

    metricas: Mapped["BusinessReputationMetrics | None"] = relationship(
        back_populates="negocio", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )


class BusinessReputationMetrics(Base):
    """Métricas cuantitativas recolectadas y el Índice de Transparencia calculado.

    No almacena texto de reseñas: solo estadísticas agregadas (blindaje legal).
    """

    __tablename__ = "business_reputation_metrics"

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_entities.id", ondelete="CASCADE"), primary_key=True
    )
    google_rating_avg: Mapped[float | None] = mapped_column(Float)
    google_reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    # Proporción de sentimiento positivo extraída por NLP (0.0 a 1.0), opcional.
    sentiment_positive_ratio: Mapped[float | None] = mapped_column(Float)
    # Métrica interna de la plataforma (tiempo de respuesta en chat/citas), 0.0 a 1.0.
    response_time_score: Mapped[float | None] = mapped_column(Float)
    # Puntaje final ponderado de 1.0 a 10.0, recalculado por el worker.
    final_score: Mapped[float] = mapped_column(Float, default=1.0)
    is_verified_profile: Mapped[bool] = mapped_column(default=False)
    actualizado_en: Mapped[datetime] = mapped_column(default=ahora_utc, onupdate=ahora_utc)

    negocio: Mapped[BusinessEntity] = relationship(back_populates="metricas")


class Reserva(Base):
    """Reserva de cupo en un comercio. Su estado lo cambia el dueño al escanear el QR o marcar no-show."""

    __tablename__ = "reservas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("business_entities.id", ondelete="CASCADE"))
    estado: Mapped[str] = mapped_column(String(20), default="reservada")
    qr_token: Mapped[str] = mapped_column(String(64), unique=True)
    creado_en: Mapped[datetime] = mapped_column(default=ahora_utc)
    actualizado_en: Mapped[datetime] = mapped_column(default=ahora_utc, onupdate=ahora_utc)


class PasaporteArriendo(Base):
    """Resultado de la verificación de arriendo. Solo guarda puntaje y fecha, nunca el PDF."""

    __tablename__ = "pasaporte_arriendo"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    estado: Mapped[str] = mapped_column(String(20))
    score: Mapped[int | None] = mapped_column(SmallInteger)
    verificado_en: Mapped[datetime | None]
    creado_en: Mapped[datetime] = mapped_column(default=ahora_utc)


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    session = sessionmaker(bind=get_engine(), expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
