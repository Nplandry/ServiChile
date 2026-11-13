"""Acceso a datos. Los repositorios reciben y devuelven entidades del dominio, nunca modelos ORM.

La conversión entre entidades y modelos SQLAlchemy vive en este archivo, así los servicios
no conocen la forma de las tablas.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entidades import (
    Consulta,
    Fuente,
    Metricas,
    Negocio,
    Perfil,
    Reserva,
    Usuario,
)
from app.infrastructure import db as orm
from app.utils import ahora_utc



def _perfil(p: orm.Perfil | None) -> Perfil | None:
    if p is None:
        return None
    return Perfil(
        edad=p.edad,
        tipo_cuenta=p.tipo_cuenta,
        preocupacion=p.preocupacion,
        proposito=p.proposito,
    )


def _usuario(u: orm.Usuario) -> Usuario:
    return Usuario(
        id=u.id,
        email=u.email,
        nombre=u.nombre,
        password_hash=u.password_hash,
        activo=u.activo,
        rut=u.rut,
        rut_verificado=u.rut_verificado,
        telefono=u.telefono,
        biometria_verificada=bool(u.biometria_verificada),
        biometria_verificada_en=u.biometria_verificada_en,
        xp=int(u.xp or 0),
        creado_en=u.creado_en,
        perfil=_perfil(u.perfil),
    )


def _metricas(m: orm.BusinessReputationMetrics | None) -> Metricas | None:
    if m is None:
        return None
    return Metricas(
        business_id=m.business_id,
        google_rating_avg=m.google_rating_avg,
        google_reviews_count=m.google_reviews_count or 0,
        sentiment_positive_ratio=m.sentiment_positive_ratio,
        response_time_score=m.response_time_score,
        final_score=m.final_score,
        is_verified_profile=m.is_verified_profile,
        actualizado_en=m.actualizado_en,
    )


def _negocio(n: orm.BusinessEntity) -> Negocio:
    return Negocio(
        id=n.id,
        nombre=n.nombre,
        categoria=n.categoria,
        latitud=n.latitud,
        longitud=n.longitud,
        direccion=n.direccion,
        descripcion=n.descripcion,
        imagen_url=n.imagen_url,
        logo_url=n.logo_url,
        requiere_nivel=n.requiere_nivel,
        is_claimed=n.is_claimed,
        reclamado_por=n.reclamado_por,
        telefono=n.telefono,
        sitio_web=n.sitio_web,
        metricas=_metricas(n.metricas),
    )


def _reserva(r: orm.Reserva) -> Reserva:
    return Reserva(
        id=r.id,
        usuario_id=r.usuario_id,
        business_id=r.business_id,
        estado=r.estado,
        qr_token=r.qr_token,
        creado_en=r.creado_en,
        actualizado_en=r.actualizado_en,
    )


def _consulta(c: orm.Consulta) -> Consulta:
    return Consulta(
        id=c.id,
        usuario_id=c.usuario_id,
        categoria=c.categoria,
        pregunta_redactada=c.pregunta_redactada,
        respuesta=c.respuesta,
        fuentes=list(c.fuentes or []),
        requiere_humano=c.requiere_humano,
        creado_en=c.creado_en,
    )


class UsuarioRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> Usuario | None:
        u = self.session.scalar(select(orm.Usuario).where(orm.Usuario.email == email))
        return _usuario(u) if u else None

    def get(self, usuario_id: uuid.UUID) -> Usuario | None:
        u = self.session.get(orm.Usuario, usuario_id)
        return _usuario(u) if u else None

    def get_by_rut(self, rut: str) -> Usuario | None:
        u = self.session.scalar(select(orm.Usuario).where(orm.Usuario.rut == rut))
        return _usuario(u) if u else None

    def crear(self, email: str, nombre: str, password_hash: str) -> Usuario:
        """Crea la entidad en memoria. Se persiste con guardar()."""
        return Usuario(id=uuid.uuid4(), email=email, nombre=nombre, password_hash=password_hash)

    def eliminar(self, usuario_id: uuid.UUID) -> None:
        """Borra el usuario. Perfil, reservas, consultas y verificaciones se borran en cascada."""
        u = self.session.get(orm.Usuario, usuario_id)
        if u is not None:
            self.session.delete(u)
            self.session.commit()

    def guardar(self, usuario: Usuario) -> Usuario:
        """Inserta o actualiza el usuario y su perfil."""
        u = self.session.get(orm.Usuario, usuario.id)
        if u is None:
            u = orm.Usuario(id=usuario.id)
            self.session.add(u)
        u.email = usuario.email
        u.nombre = usuario.nombre
        u.password_hash = usuario.password_hash
        u.activo = usuario.activo
        u.rut = usuario.rut
        u.rut_verificado = usuario.rut_verificado
        u.telefono = usuario.telefono
        u.biometria_verificada = usuario.biometria_verificada
        u.biometria_verificada_en = usuario.biometria_verificada_en
        u.xp = int(usuario.xp or 0)
        if usuario.perfil is not None:
            if u.perfil is None:
                u.perfil = orm.Perfil(usuario_id=usuario.id)
            u.perfil.edad = usuario.perfil.edad
            u.perfil.tipo_cuenta = usuario.perfil.tipo_cuenta
            u.perfil.preocupacion = usuario.perfil.preocupacion
            u.perfil.proposito = usuario.perfil.proposito
        self.session.commit()
        self.session.refresh(u)
        return _usuario(u)


class XpRepository:
    """Otorga XP de forma idempotente: un (usuario, evento) solo premia una vez."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def otorgar(self, usuario_id: uuid.UUID, evento: str, puntos: int) -> int:
        """Devuelve los puntos sumados (0 si el evento ya existía)."""
        if puntos <= 0:
            return 0
        ya = self.session.scalar(
            select(orm.UsuarioXpEvento.id).where(
                orm.UsuarioXpEvento.usuario_id == usuario_id,
                orm.UsuarioXpEvento.evento == evento,
            )
        )
        if ya is not None:
            return 0
        self.session.add(
            orm.UsuarioXpEvento(usuario_id=usuario_id, evento=evento, puntos=puntos)
        )
        u = self.session.get(orm.Usuario, usuario_id)
        if u is None:
            return 0
        u.xp = int(u.xp or 0) + puntos
        self.session.commit()
        return puntos

    def total(self, usuario_id: uuid.UUID) -> int:
        u = self.session.get(orm.Usuario, usuario_id)
        return int(u.xp or 0) if u else 0


@dataclass(frozen=True)
class FragmentoRecuperado:
    contenido: str
    titulo: str
    url: str | None
    pagina: int | None
    distancia: float


class FragmentoRepository:
    """Búsqueda vectorial con pgvector (distancia coseno)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def buscar(
        self, embedding: list[float], k: int, max_distancia: float, categoria: str | None
    ) -> list[FragmentoRecuperado]:
        distancia = orm.Fragmento.embedding.cosine_distance(embedding).label("distancia")
        stmt = (
            select(orm.Fragmento.contenido, orm.Fragmento.pagina, orm.Documento.titulo,
                   orm.Documento.url_fuente, distancia)
            .join(orm.Documento, orm.Documento.id == orm.Fragmento.documento_id)
            .order_by(distancia)
            .limit(k)
        )
        if categoria:
            # Documentos sin categoría aplican a todos los casos
            stmt = stmt.where((orm.Documento.categoria == categoria) | (orm.Documento.categoria.is_(None)))
        rows = self.session.execute(stmt).all()
        return [
            FragmentoRecuperado(r.contenido, r.titulo, r.url_fuente, r.pagina, float(r.distancia))
            for r in rows
            if r.distancia <= max_distancia
        ]


class ConsultaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def crear(
        self,
        usuario_id: uuid.UUID,
        categoria: str | None,
        pregunta_redactada: str,
        respuesta: str,
        fuentes: list[Fuente],
        requiere_humano: bool,
    ) -> Consulta:
        c = orm.Consulta(
            usuario_id=usuario_id,
            categoria=categoria,
            pregunta_redactada=pregunta_redactada,
            respuesta=respuesta,
            fuentes=[{"n": f.n, "titulo": f.titulo, "url": f.url, "pagina": f.pagina} for f in fuentes],
            requiere_humano=requiere_humano,
        )
        self.session.add(c)
        self.session.commit()
        self.session.refresh(c)
        return _consulta(c)

    def listar_por_usuario(self, usuario_id: uuid.UUID, limite: int = 50) -> list[Consulta]:
        stmt = (
            select(orm.Consulta)
            .where(orm.Consulta.usuario_id == usuario_id)
            .order_by(orm.Consulta.creado_en.desc())
            .limit(limite)
        )
        return [_consulta(c) for c in self.session.scalars(stmt)]


class NegocioRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, business_id: uuid.UUID) -> Negocio | None:
        n = self.session.get(orm.BusinessEntity, business_id)
        return _negocio(n) if n else None

    def listar(self, categoria: str | None = None, q: str | None = None, limite: int = 100) -> list[Negocio]:
        """Lista negocios para el marketplace, filtrando por categoría y texto (nombre o dirección)."""
        stmt = select(orm.BusinessEntity).order_by(orm.BusinessEntity.nombre)
        if categoria:
            stmt = stmt.where(orm.BusinessEntity.categoria == categoria)
        if q:
            patron = f"%{q.strip()}%"
            stmt = stmt.where(
                orm.BusinessEntity.nombre.ilike(patron) | orm.BusinessEntity.direccion.ilike(patron)
            )
        return [_negocio(n) for n in self.session.scalars(stmt.limit(limite))]

    def listar_reclamados_por(self, usuario_id: uuid.UUID) -> list[Negocio]:
        stmt = select(orm.BusinessEntity).where(orm.BusinessEntity.reclamado_por == usuario_id)
        return [_negocio(n) for n in self.session.scalars(stmt)]

    def guardar(self, negocio: Negocio) -> Negocio:
        """Inserta o actualiza el negocio y sus métricas."""
        n = self.session.get(orm.BusinessEntity, negocio.id)
        if n is None:
            n = orm.BusinessEntity(id=negocio.id)
            self.session.add(n)
        n.nombre = negocio.nombre
        n.categoria = negocio.categoria
        n.latitud = negocio.latitud
        n.longitud = negocio.longitud
        n.direccion = negocio.direccion
        n.descripcion = negocio.descripcion
        n.imagen_url = negocio.imagen_url
        n.logo_url = negocio.logo_url
        n.requiere_nivel = negocio.requiere_nivel
        n.is_claimed = negocio.is_claimed
        n.reclamado_por = negocio.reclamado_por
        n.telefono = negocio.telefono
        n.sitio_web = negocio.sitio_web
        if negocio.metricas is not None:
            m = negocio.metricas
            if n.metricas is None:
                n.metricas = orm.BusinessReputationMetrics(business_id=negocio.id, actualizado_en=ahora_utc())
            n.metricas.google_rating_avg = m.google_rating_avg
            n.metricas.google_reviews_count = m.google_reviews_count
            n.metricas.sentiment_positive_ratio = m.sentiment_positive_ratio
            n.metricas.response_time_score = m.response_time_score
            n.metricas.final_score = m.final_score
            n.metricas.is_verified_profile = m.is_verified_profile
        self.session.commit()
        self.session.refresh(n)
        return _negocio(n)


class ReservaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def crear(self, usuario_id: uuid.UUID, business_id: uuid.UUID, qr_token: str) -> Reserva:
        r = orm.Reserva(usuario_id=usuario_id, business_id=business_id, estado="reservada", qr_token=qr_token)
        self.session.add(r)
        self.session.commit()
        self.session.refresh(r)
        return _reserva(r)

    def get(self, reserva_id: uuid.UUID) -> Reserva | None:
        r = self.session.get(orm.Reserva, reserva_id)
        return _reserva(r) if r else None

    def get_por_qr(self, business_id: uuid.UUID, qr_token: str) -> Reserva | None:
        stmt = select(orm.Reserva).where(orm.Reserva.business_id == business_id, orm.Reserva.qr_token == qr_token)
        r = self.session.scalar(stmt)
        return _reserva(r) if r else None

    def listar_por_usuario(self, usuario_id: uuid.UUID) -> list[Reserva]:
        stmt = select(orm.Reserva).where(orm.Reserva.usuario_id == usuario_id).order_by(orm.Reserva.creado_en.desc())
        return [_reserva(r) for r in self.session.scalars(stmt)]

    def contar_por_estado(self, usuario_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(orm.Reserva.estado, func.count())
            .where(orm.Reserva.usuario_id == usuario_id)
            .group_by(orm.Reserva.estado)
        )
        return {estado: cantidad for estado, cantidad in self.session.execute(stmt).all()}

    def guardar(self, reserva: Reserva) -> Reserva:
        r = self.session.get(orm.Reserva, reserva.id)
        r.estado = reserva.estado
        self.session.commit()
        self.session.refresh(r)
        return _reserva(r)


