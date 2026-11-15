from __future__ import annotations

from datetime import datetime

from app.domain.ciber_observables import (
    armar_observables,
    razones_resenas,
    score_resenas,
)

from app.domain.entidades import Metricas, ObservableCiber

CAMPOS_SCORE_SONDA: tuple[tuple[str, str], ...] = (
    ("ssl-tls", "score_ssl_tls"),
    ("email-auth", "score_email_auth"),
    ("puertos", "score_puertos"),
    ("headers-http", "score_headers_http"),
    ("stack-vulnerable", "score_stack_vulnerable"),
    ("blacklist", "score_blacklist"),
    ("dnssec", "score_dnssec"),
    ("subdominios", "score_subdominios"),
    ("whois", "score_whois"),
    ("uptime", "score_uptime"),
    ("cookies", "score_cookies"),
    ("politica-privacidad", "score_politica_privacidad"),
    ("terminos", "score_terminos"),
    ("sla", "score_sla"),
    ("mercado-publico", "score_mercado_publico"),
    ("sii", "score_sii"),
    ("cmf", "score_cmf"),
    ("incidentes", "score_incidentes"),
)

_CAMPOS_CIBER_NUCLEO: tuple[str, ...] = (
    "score_email_auth",
    "score_cookies",
    "score_politica_privacidad",
    "score_terminos",
    "score_sla",
)

_IDS_DOCS = ("politica-privacidad", "terminos", "sla")


def necesita_sonda_ciber(m: Metricas) -> bool:

    return m.ciber_escaneado_en is None or any(
        (getattr(m, a) is None for a in _CAMPOS_CIBER_NUCLEO)
    )


def necesita_extensiones(m: Metricas) -> bool:

    return (
        m.score_mercado_publico is None
        or m.score_sii is None
        or m.score_cmf is None
        or (m.score_incidentes is None)
        or (m.incidentes_razones is None)
    )


def necesita_places(m: Metricas) -> bool:

    return m.google_rating_avg is None


def metricas_necesitan_escaneo(m: Metricas) -> bool:

    return necesita_sonda_ciber(m) or necesita_extensiones(m) or necesita_places(m)


def scores_desde_metricas(m: Metricas) -> dict[str, int]:

    out: dict[str, int] = {}

    for oid, attr in CAMPOS_SCORE_SONDA:

        v = getattr(m, attr)

        if v is not None:

            out[oid] = int(v)

    return out


def volcar_scores_en_metricas(
    metricas: Metricas,
    scores: dict[str, int],
    ahora: datetime,
    *,
    marcar_ciber: bool = True,
) -> None:

    for oid, attr in CAMPOS_SCORE_SONDA:

        if oid not in scores:

            continue

        setattr(metricas, attr, float(scores[oid]))

    if marcar_ciber:

        metricas.ciber_escaneado_en = ahora


def valores_desde_metricas(m: Metricas) -> dict[str, int]:

    if m.ciber_escaneado_en is None and m.score_ssl_tls is None:

        return {}

    valores = {
        oid: int(getattr(m, attr) if getattr(m, attr) is not None else 0)
        for oid, attr in CAMPOS_SCORE_SONDA
    }

    valores["resenas-reclamos"] = score_resenas(
        m.google_rating_avg, m.google_reviews_count or 0
    )

    return valores


def observables_desde_metricas(m: Metricas) -> list[ObservableCiber]:

    valores = valores_desde_metricas(m)

    if not valores:

        return []

    razones_inc = [str(x) for x in m.incidentes_razones or [] if str(x).strip()]

    score_res = int(valores.get("resenas-reclamos", 0))

    razones_res = razones_resenas(
        ficha=getattr(m, "google_place_nombre", None),
        google_rating_avg=m.google_rating_avg,
        google_reviews_count=m.google_reviews_count or 0,
        score=score_res,
    )

    docs_raz = (
        m.docs_legales_razones if isinstance(m.docs_legales_razones, dict) else {}
    )

    out: list[ObservableCiber] = []

    for s in armar_observables(valores):

        if s.id == "incidentes":

            razones = razones_inc

        elif s.id == "resenas-reclamos":

            razones = razones_res

        elif s.id in _IDS_DOCS:

            raw = docs_raz.get(s.id) if docs_raz else None

            razones = [str(x) for x in raw] if isinstance(raw, list) else []

        else:

            razones = []

        out.append(
            ObservableCiber(
                id=s.id,
                etiqueta=s.etiqueta,
                detalle=s.detalle,
                score=s.score,
                peso=s.peso,
                grupo=s.grupo,
                razones=razones,
            )
        )

    return out
