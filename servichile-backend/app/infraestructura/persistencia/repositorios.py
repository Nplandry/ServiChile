import uuid

from sqlalchemy import func, select

from sqlalchemy.orm import Session

from app.dominio.entidades import Metricas, Negocio, Perfil, Reserva, Usuario

from app.infraestructura.persistencia import modelos as orm

from app.tiempo import ahora_utc


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
        antecedentes_verificados=bool(getattr(u, "antecedentes_verificados", False)),
        antecedentes_verificados_en=getattr(u, "antecedentes_verificados_en", None),
        antecedentes_anotaciones=getattr(u, "antecedentes_anotaciones", None),
        antecedentes_score=getattr(u, "antecedentes_score", None),
        xp=int(u.xp or 0),
        creado_en=u.creado_en,
        perfil=_perfil(u.perfil),
    )


def _metricas(m: orm.BusinessReputationMetrics | None) -> Metricas | None:

    if m is None:

        return None

    raw_raz = getattr(m, "incidentes_razones", None)

    razones = [str(x) for x in raw_raz] if isinstance(raw_raz, list) else None

    raw_docs = getattr(m, "docs_legales_razones", None)

    docs_raz = None

    if isinstance(raw_docs, dict):

        docs_raz = {
            str(k): [str(x) for x in (v or [])]
            for k, v in raw_docs.items()
            if isinstance(v, list)
        }

    return Metricas(
        business_id=m.business_id,
        google_rating_avg=m.google_rating_avg,
        google_reviews_count=m.google_reviews_count or 0,
        google_place_nombre=getattr(m, "google_place_nombre", None),
        sentiment_positive_ratio=m.sentiment_positive_ratio,
        response_time_score=m.response_time_score,
        final_score=m.final_score,
        is_verified_profile=m.is_verified_profile,
        score_ssl_tls=m.score_ssl_tls,
        score_email_auth=m.score_email_auth,
        score_puertos=m.score_puertos,
        score_headers_http=m.score_headers_http,
        score_stack_vulnerable=m.score_stack_vulnerable,
        score_blacklist=m.score_blacklist,
        score_dnssec=m.score_dnssec,
        score_subdominios=m.score_subdominios,
        score_whois=m.score_whois,
        score_uptime=m.score_uptime,
        score_cookies=getattr(m, "score_cookies", None),
        score_politica_privacidad=getattr(m, "score_politica_privacidad", None),
        score_terminos=getattr(m, "score_terminos", None),
        score_sla=getattr(m, "score_sla", None),
        docs_legales_razones=docs_raz,
        score_mercado_publico=getattr(m, "score_mercado_publico", None),
        score_sii=getattr(m, "score_sii", None),
        score_cmf=getattr(m, "score_cmf", None),
        score_incidentes=getattr(m, "score_incidentes", None),
        incidentes_razones=razones,
        score_domicilio=getattr(m, "score_domicilio", None),
        score_huella_digital=getattr(m, "score_huella_digital", None),
        score_persona_juridica=getattr(m, "score_persona_juridica", None),
        datalux_razones=(
            {
                str(k): [str(x) for x in (v or [])]
                for k, v in getattr(m, "datalux_razones", None).items()
                if isinstance(v, list)
            }
            if isinstance(getattr(m, "datalux_razones", None), dict)
            else None
        ),
        ciber_escaneado_en=m.ciber_escaneado_en,
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
        rut_empresa=getattr(n, "rut_empresa", None),
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

        return Usuario(
            id=uuid.uuid4(), email=email, nombre=nombre, password_hash=password_hash
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

        u.antecedentes_verificados = bool(usuario.antecedentes_verificados)

        u.antecedentes_verificados_en = usuario.antecedentes_verificados_en

        u.antecedentes_anotaciones = usuario.antecedentes_anotaciones

        u.antecedentes_score = usuario.antecedentes_score

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


class NegocioRepository:

    def __init__(self, session: Session) -> None:

        self.session = session

    def get(self, business_id: uuid.UUID) -> Negocio | None:

        n = self.session.get(orm.BusinessEntity, business_id)

        return _negocio(n) if n else None

    def listar(
        self, categoria: str | None = None, q: str | None = None, limite: int = 100
    ) -> list[Negocio]:

        stmt = select(orm.BusinessEntity).order_by(orm.BusinessEntity.nombre)

        if categoria:

            stmt = stmt.where(orm.BusinessEntity.categoria == categoria)

        if q:

            patron = f"%{q.strip()}%"

            stmt = stmt.where(
                orm.BusinessEntity.nombre.ilike(patron)
                | orm.BusinessEntity.direccion.ilike(patron)
            )

        return [_negocio(n) for n in self.session.scalars(stmt.limit(limite))]

    def listar_reclamados_por(self, usuario_id: uuid.UUID) -> list[Negocio]:

        stmt = select(orm.BusinessEntity).where(
            orm.BusinessEntity.reclamado_por == usuario_id
        )

        return [_negocio(n) for n in self.session.scalars(stmt)]

    def guardar(self, negocio: Negocio) -> Negocio:

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

        n.rut_empresa = negocio.rut_empresa

        if negocio.metricas is not None:

            m = negocio.metricas

            if n.metricas is None:

                n.metricas = orm.BusinessReputationMetrics(
                    business_id=negocio.id, actualizado_en=ahora_utc()
                )

            n.metricas.google_rating_avg = m.google_rating_avg

            n.metricas.google_reviews_count = m.google_reviews_count

            n.metricas.google_place_nombre = getattr(m, "google_place_nombre", None)

            n.metricas.sentiment_positive_ratio = m.sentiment_positive_ratio

            n.metricas.response_time_score = m.response_time_score

            n.metricas.final_score = m.final_score

            n.metricas.is_verified_profile = m.is_verified_profile

            n.metricas.score_ssl_tls = m.score_ssl_tls

            n.metricas.score_email_auth = m.score_email_auth

            n.metricas.score_puertos = m.score_puertos

            n.metricas.score_headers_http = m.score_headers_http

            n.metricas.score_stack_vulnerable = m.score_stack_vulnerable

            n.metricas.score_blacklist = m.score_blacklist

            n.metricas.score_dnssec = m.score_dnssec

            n.metricas.score_subdominios = m.score_subdominios

            n.metricas.score_whois = m.score_whois

            n.metricas.score_uptime = m.score_uptime

            n.metricas.score_cookies = m.score_cookies

            n.metricas.score_politica_privacidad = getattr(
                m, "score_politica_privacidad", None
            )

            n.metricas.score_terminos = getattr(m, "score_terminos", None)

            n.metricas.score_sla = getattr(m, "score_sla", None)

            n.metricas.docs_legales_razones = getattr(m, "docs_legales_razones", None)

            n.metricas.score_mercado_publico = m.score_mercado_publico

            n.metricas.score_sii = m.score_sii

            n.metricas.score_cmf = m.score_cmf

            n.metricas.score_incidentes = m.score_incidentes

            n.metricas.incidentes_razones = m.incidentes_razones

            n.metricas.score_domicilio = getattr(m, "score_domicilio", None)

            n.metricas.score_huella_digital = getattr(m, "score_huella_digital", None)

            n.metricas.score_persona_juridica = getattr(
                m, "score_persona_juridica", None
            )

            n.metricas.datalux_razones = getattr(m, "datalux_razones", None)

            n.metricas.ciber_escaneado_en = m.ciber_escaneado_en

        self.session.commit()

        self.session.refresh(n)

        return _negocio(n)


class ReservaRepository:

    def __init__(self, session: Session) -> None:

        self.session = session

    def crear(
        self, usuario_id: uuid.UUID, business_id: uuid.UUID, qr_token: str
    ) -> Reserva:

        r = orm.Reserva(
            usuario_id=usuario_id,
            business_id=business_id,
            estado="reservada",
            qr_token=qr_token,
        )

        self.session.add(r)

        self.session.commit()

        self.session.refresh(r)

        return _reserva(r)

    def get(self, reserva_id: uuid.UUID) -> Reserva | None:

        r = self.session.get(orm.Reserva, reserva_id)

        return _reserva(r) if r else None

    def get_por_qr(self, business_id: uuid.UUID, qr_token: str) -> Reserva | None:

        stmt = select(orm.Reserva).where(
            orm.Reserva.business_id == business_id, orm.Reserva.qr_token == qr_token
        )

        r = self.session.scalar(stmt)

        return _reserva(r) if r else None

    def listar_por_usuario(self, usuario_id: uuid.UUID) -> list[Reserva]:

        stmt = (
            select(orm.Reserva)
            .where(orm.Reserva.usuario_id == usuario_id)
            .order_by(orm.Reserva.creado_en.desc())
        )

        return [_reserva(r) for r in self.session.scalars(stmt)]

    def contar_por_estado(self, usuario_id: uuid.UUID) -> dict[str, int]:

        stmt = (
            select(orm.Reserva.estado, func.count())
            .where(orm.Reserva.usuario_id == usuario_id)
            .group_by(orm.Reserva.estado)
        )

        return {
            estado: cantidad for estado, cantidad in self.session.execute(stmt).all()
        }

    def guardar(self, reserva: Reserva) -> Reserva:

        r = self.session.get(orm.Reserva, reserva.id)

        r.estado = reserva.estado

        self.session.commit()

        self.session.refresh(r)

        return _reserva(r)
