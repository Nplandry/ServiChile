import uuid

from sqlalchemy import func, select

from sqlalchemy.orm import Session, joinedload

from app.dominio.docs_empresa import docs_empresa_a_raw
from app.dominio.entidades import Negocio, Trabajo, Usuario
from app.infraestructura.persistencia import modelos as orm
from app.infraestructura.persistencia.mapeo import (
    _negocio,
    _negocio_lista,
    _opciones_lista,
    _trabajo,
    _usuario,
)
from app.tiempo import ahora_utc


class RepositorioUsuario:

    def __init__(self, session: Session) -> None:

        self.session = session

    def registrar_hash_pades(
        self,
        sha256: str,
        *,
        scope: str,
        tipo: str | None = None,
        usuario_id: uuid.UUID | None = None,
        business_id: uuid.UUID | None = None,
    ) -> bool:
        return registrar_hash_pades(
            self.session,
            sha256,
            scope=scope,
            tipo=tipo,
            usuario_id=usuario_id,
            business_id=business_id,
        )

    def obtener_por_email(self, email: str) -> Usuario | None:

        u = self.session.scalar(select(orm.Usuario).where(orm.Usuario.email == email))

        return _usuario(u) if u else None

    def obtener(self, usuario_id: uuid.UUID) -> Usuario | None:

        u = self.session.get(orm.Usuario, usuario_id)

        return _usuario(u) if u else None

    def obtener_por_rut(self, rut: str) -> Usuario | None:

        u = self.session.scalar(select(orm.Usuario).where(orm.Usuario.rut == rut))

        return _usuario(u) if u else None

    def crear(self, email: str, nombre: str, hash_contrasena: str) -> Usuario:

        return Usuario(
            id=uuid.uuid4(), email=email, nombre=nombre, password_hash=hash_contrasena
        )

    def eliminar(self, usuario_id: uuid.UUID) -> None:

        u = self.session.get(orm.Usuario, usuario_id)

        if u is not None:

            self.session.delete(u)

            self.session.commit()

    def guardar(self, usuario: Usuario) -> Usuario:

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

        u.biometria_ruta = usuario.biometria_ruta

        u.biometria_sha256 = usuario.biometria_sha256

        u.biometria_bytes = usuario.biometria_bytes

        u.biometria_ancho = usuario.biometria_ancho

        u.biometria_alto = usuario.biometria_alto

        u.biometria_content_type = usuario.biometria_content_type

        u.biometria_retener_hasta = usuario.biometria_retener_hasta

        u.cedula_verificada = bool(usuario.cedula_verificada)

        u.cedula_verificada_en = usuario.cedula_verificada_en

        u.cedula_ruta = usuario.cedula_ruta

        u.cedula_sha256 = usuario.cedula_sha256

        u.cedula_bytes = usuario.cedula_bytes

        u.cedula_ancho = usuario.cedula_ancho

        u.cedula_alto = usuario.cedula_alto

        u.cedula_content_type = usuario.cedula_content_type

        u.cedula_retener_hasta = usuario.cedula_retener_hasta

        u.cedula_score = usuario.cedula_score

        u.cedula_rut_ocr = usuario.cedula_rut_ocr

        u.antecedentes_verificados = bool(usuario.antecedentes_verificados)

        u.antecedentes_verificados_en = usuario.antecedentes_verificados_en

        u.antecedentes_anotaciones = usuario.antecedentes_anotaciones

        u.antecedentes_score = usuario.antecedentes_score

        u.antecedentes_pades = bool(usuario.antecedentes_pades)

        u.antecedentes_entidad_emisora = usuario.antecedentes_entidad_emisora

        u.antecedentes_fecha_emision = usuario.antecedentes_fecha_emision

        u.antecedentes_sha256 = usuario.antecedentes_sha256

        u.antecedentes_glosa = usuario.antecedentes_glosa

        u.aval_verificado = bool(usuario.aval_verificado)

        u.aval_verificado_en = usuario.aval_verificado_en

        u.aval_score = usuario.aval_score

        u.aval_tipo = usuario.aval_tipo

        u.xp = int(usuario.xp or 0)

        if usuario.perfil is not None:

            if u.perfil is None:

                u.perfil = orm.Perfil(usuario_id=usuario.id)

            u.perfil.edad = usuario.perfil.edad

            u.perfil.tipo_cuenta = usuario.perfil.tipo_cuenta

        self.session.commit()

        self.session.refresh(u)

        return _usuario(u)


class RepositorioXp:

    def __init__(self, session: Session) -> None:

        self.session = session

    def otorgar(self, usuario_id: uuid.UUID, evento: str, puntos: int) -> int:

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


def registrar_hash_pades(
    session: Session,
    sha256: str,
    *,
    scope: str,
    tipo: str | None = None,
    usuario_id: uuid.UUID | None = None,
    business_id: uuid.UUID | None = None,
) -> bool:
    """True si OK; False si el hash ya fue usado por otra cuenta/empresa."""
    existente = session.get(orm.HashDocumentoPades, sha256)
    if existente is not None:
        mismo_usuario = (
            usuario_id is not None and existente.usuario_id == usuario_id
        )
        misma_empresa = (
            business_id is not None and existente.business_id == business_id
        )
        return bool(mismo_usuario or misma_empresa)
    session.add(
        orm.HashDocumentoPades(
            sha256=sha256,
            scope=scope,
            tipo=tipo,
            usuario_id=usuario_id,
            business_id=business_id,
        )
    )
    return True


class RepositorioNegocio:

    def __init__(self, session: Session) -> None:

        self.session = session

    def registrar_hash_pades(
        self,
        sha256: str,
        *,
        scope: str,
        tipo: str | None = None,
        usuario_id: uuid.UUID | None = None,
        business_id: uuid.UUID | None = None,
    ) -> bool:
        return registrar_hash_pades(
            self.session,
            sha256,
            scope=scope,
            tipo=tipo,
            usuario_id=usuario_id,
            business_id=business_id,
        )

    def obtener(self, negocio_id: uuid.UUID) -> Negocio | None:

        n = self.session.get(orm.EntidadNegocio, negocio_id)

        return _negocio(n) if n else None

    def listar(
        self, categoria: str | None = None, q: str | None = None, limite: int = 100
    ) -> list[Negocio]:

        stmt = (
            select(orm.EntidadNegocio)
            .options(*_opciones_lista())
            .order_by(orm.EntidadNegocio.nombre)
        )

        if categoria:

            stmt = stmt.where(orm.EntidadNegocio.categoria == categoria)

        if q:

            patron = f"%{q.strip()}%"

            stmt = stmt.where(
                orm.EntidadNegocio.nombre.ilike(patron)
                | orm.EntidadNegocio.direccion.ilike(patron)
            )

        return [
            _negocio_lista(n) for n in self.session.scalars(stmt.limit(limite)).unique()
        ]

    def listar_de(self, usuario_id: uuid.UUID) -> list[Negocio]:
        """Ficha completa del titular (incluye RUT, teléfono, sitio para editar)."""
        stmt = (
            select(orm.EntidadNegocio)
            .options(joinedload(orm.EntidadNegocio.metricas))
            .where(orm.EntidadNegocio.reclamado_por == usuario_id)
        )

        return [_negocio(n) for n in self.session.scalars(stmt).unique()]

    def listar_completos(self, limite: int = 500) -> list[Negocio]:
        """Listado para refrescar el evaluador: primero pendientes (sin escaneo)."""
        stmt = (
            select(orm.EntidadNegocio)
            .outerjoin(orm.MetricasReputacionNegocio)
            .options(joinedload(orm.EntidadNegocio.metricas))
            .order_by(
                orm.MetricasReputacionNegocio.rater_escaneado_en.is_(None).desc(),
                orm.EntidadNegocio.nombre,
            )
            .limit(max(1, min(limite, 2000)))
        )
        return [_negocio(n) for n in self.session.scalars(stmt).unique()]

    def eliminar(self, negocio_id: uuid.UUID) -> None:

        n = self.session.get(orm.EntidadNegocio, negocio_id)

        if n is None:

            return

        self.session.delete(n)

        self.session.commit()

    def eliminar_de(self, usuario_id: uuid.UUID) -> None:

        stmt = select(orm.EntidadNegocio).where(
            orm.EntidadNegocio.reclamado_por == usuario_id
        )

        for n in list(self.session.scalars(stmt)):

            self.session.delete(n)

        self.session.commit()

    def guardar(self, negocio: Negocio) -> Negocio:

        n = self.session.get(orm.EntidadNegocio, negocio.id)

        if n is None:

            n = orm.EntidadNegocio(id=negocio.id)

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

        n.rut_empresa = negocio.rut_empresa

        n.docs_empresa = (
            docs_empresa_a_raw(negocio.docs_empresa)
            if negocio.docs_empresa is not None
            else {}
        )

        if negocio.metricas is not None:

            m = negocio.metricas

            if n.metricas is None:

                n.metricas = orm.MetricasReputacionNegocio(
                    business_id=negocio.id, actualizado_en=ahora_utc()
                )

            n.metricas.google_rating_avg = m.google_rating_avg

            n.metricas.google_reviews_count = m.google_reviews_count

            n.metricas.final_score = m.final_score

            n.metricas.rater_escaneado_en = m.rater_escaneado_en

            n.metricas.observables = (
                list(m.observables)
                if isinstance(m.observables, list)
                else None
            )

        self.session.commit()

        self.session.refresh(n)

        return _negocio(n)


class RepositorioTrabajo:

    def __init__(self, session: Session) -> None:

        self.session = session

    def crear(
        self, usuario_id: uuid.UUID, negocio_id: uuid.UUID, token_qr: str
    ) -> Trabajo:

        r = orm.Trabajo(
            usuario_id=usuario_id,
            business_id=negocio_id,
            estado="abierto",
            qr_token=token_qr,
        )

        self.session.add(r)

        self.session.commit()

        self.session.refresh(r)

        return _trabajo(r)

    def obtener(self, trabajo_id: uuid.UUID) -> Trabajo | None:

        r = self.session.get(orm.Trabajo, trabajo_id)

        return _trabajo(r) if r else None

    def obtener_por_qr(self, negocio_id: uuid.UUID, token_qr: str) -> Trabajo | None:

        stmt = select(orm.Trabajo).where(
            orm.Trabajo.business_id == negocio_id, orm.Trabajo.qr_token == token_qr
        )

        r = self.session.scalar(stmt)

        return _trabajo(r) if r else None

    def listar_por_usuario(self, usuario_id: uuid.UUID) -> list[Trabajo]:

        stmt = (
            select(orm.Trabajo)
            .where(orm.Trabajo.usuario_id == usuario_id)
            .order_by(orm.Trabajo.creado_en.desc())
        )

        return [_trabajo(r) for r in self.session.scalars(stmt)]

    def listar_por_negocio(self, negocio_id: uuid.UUID) -> list[Trabajo]:
        stmt = (
            select(orm.Trabajo)
            .where(orm.Trabajo.business_id == negocio_id)
            .order_by(orm.Trabajo.creado_en.desc())
        )
        return [_trabajo(r) for r in self.session.scalars(stmt)]

    def contar_por_estado(self, usuario_id: uuid.UUID) -> dict[str, int]:

        stmt = (
            select(orm.Trabajo.estado, func.count())
            .where(orm.Trabajo.usuario_id == usuario_id)
            .group_by(orm.Trabajo.estado)
        )

        return {
            estado: cantidad for estado, cantidad in self.session.execute(stmt).all()
        }

    def guardar(self, trabajo: Trabajo) -> Trabajo:

        r = self.session.get(orm.Trabajo, trabajo.id)

        r.estado = trabajo.estado

        self.session.commit()

        self.session.refresh(r)

        return _trabajo(r)
