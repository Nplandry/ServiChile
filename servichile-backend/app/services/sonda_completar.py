from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait

from app.domain.ciber_metricas import (
    necesita_extensiones,
    necesita_places,
    necesita_sonda_ciber,
    scores_desde_metricas,
    volcar_scores_en_metricas,
)

from app.domain.entidades import Metricas

from app.domain.reputacion import EntradaScore, calcular_indice

from app.infrastructure.chilecompra import ChileCompra, NullChileCompra

from app.infrastructure.ciber_sonda import CiberSonda

from app.infrastructure.cmf_indice import CmfIndice, NullCmfIndice

from app.infrastructure.incidentes_scanner import (
    IncidentesScanner,
    NullIncidentesScanner,
    ResultadoIncidentes,
)

from app.infrastructure.places_google import (
    NullPlacesGoogle,
    PlacesGoogle,
    ResultadoPlaces,
)

from app.infrastructure.sii_apigateway import NullSiiContribuyentes, SiiContribuyentes

from app.utils import ahora_utc

_OIDS_CYBER = (
    "ssl-tls",
    "email-auth",
    "puertos",
    "headers-http",
    "stack-vulnerable",
    "blacklist",
    "dnssec",
    "subdominios",
    "whois",
    "uptime",
    "cookies",
    "politica-privacidad",
    "terminos",
    "sla",
)

_OIDS_EXT = (
    "mercado-publico",
    "sii",
    "cmf",
    "incidentes",
)


_PRESUPUESTO_S = 8.0

_PRESUPUESTO_CYBER_EXTRA_S = 6.0


def _aplicar_places(metricas: Metricas, res: ResultadoPlaces) -> None:

    if res.encontrado and res.rating is not None:

        metricas.google_rating_avg = float(res.rating)

        metricas.google_reviews_count = max(0, int(res.reviews_count or 0))

        metricas.google_place_nombre = (res.nombre or "").strip() or None

    else:

        metricas.google_rating_avg = 0.0

        metricas.google_reviews_count = 0

        metricas.google_place_nombre = None

    metricas.final_score = calcular_indice(
        EntradaScore(
            google_rating_avg=metricas.google_rating_avg,
            google_reviews_count=metricas.google_reviews_count or 0,
            is_verified_profile=bool(metricas.is_verified_profile),
        )
    )


def _tomar(fut, default):

    if fut is None:

        return default

    try:

        return fut.result(timeout=0)

    except Exception:

        return default


def completar_metricas(
    metricas: Metricas,
    sonda: CiberSonda,
    sitio_web: str | None,
    *,
    chilecompra: ChileCompra | None = None,
    sii: SiiContribuyentes | None = None,
    cmf: CmfIndice | None = None,
    incidentes: IncidentesScanner | None = None,
    places: PlacesGoogle | None = None,
    rut: str | None = None,
    nombre: str | None = None,
    direccion: str | None = None,
    forzar: bool = False,
) -> None:

    chilecompra = chilecompra or NullChileCompra()

    sii = sii or NullSiiContribuyentes()

    cmf = cmf or NullCmfIndice()

    incidentes = incidentes or NullIncidentesScanner()

    places = places or NullPlacesGoogle()

    do_cyber = forzar or necesita_sonda_ciber(metricas)

    do_ext = forzar or necesita_extensiones(metricas) or do_cyber

    do_places = forzar or necesita_places(metricas)

    if not do_cyber and not do_ext and not do_places:

        return

    scores = scores_desde_metricas(metricas)

    razones = (
        list(metricas.incidentes_razones)
        if metricas.incidentes_razones is not None
        else None
    )

    res_inc: ResultadoIncidentes | None = None

    res_places: ResultadoPlaces | None = None

    docs_razones: dict[str, list[str]] | None = None

    cyber_ok = False

    with ThreadPoolExecutor(max_workers=8) as pool:

        f_cyber = pool.submit(sonda.escanear, sitio_web) if do_cyber else None

        f_mp = pool.submit(chilecompra.score_para_rut, rut) if do_ext else None

        f_sii = pool.submit(sii.score_para_rut, rut) if do_ext else None

        f_cmf = pool.submit(cmf.score_para_rut, rut) if do_ext else None

        f_inc = pool.submit(incidentes.evaluar_nombre, nombre) if do_ext else None

        f_places = (
            pool.submit(
                places.buscar_reputacion,
                nombre=nombre,
                direccion=direccion,
                sitio_web=sitio_web,
            )
            if do_places
            else None
        )

        pendientes = [
            f for f in (f_cyber, f_mp, f_sii, f_cmf, f_inc, f_places) if f is not None
        ]

        if pendientes:

            wait(pendientes, timeout=_PRESUPUESTO_S)

        if f_cyber is not None and not f_cyber.done():

            wait([f_cyber], timeout=_PRESUPUESTO_CYBER_EXTRA_S)

        if f_cyber is not None:

            res_cyber = _tomar(f_cyber, None)

            if res_cyber is not None:

                scores.update(res_cyber.scores)

                docs_razones = getattr(res_cyber, "docs_razones", None)

                cyber_ok = True

        if f_mp is not None:

            scores["mercado-publico"] = int(
                _tomar(f_mp, scores.get("mercado-publico", 0)) or 0
            )

        if f_sii is not None:

            scores["sii"] = int(_tomar(f_sii, scores.get("sii", 0)) or 0)

        if f_cmf is not None:

            scores["cmf"] = int(_tomar(f_cmf, scores.get("cmf", 0)) or 0)

        if f_inc is not None:

            res_inc = _tomar(f_inc, None)

            if res_inc is not None:

                scores["incidentes"] = res_inc.score

                razones = list(res_inc.razones)

        if f_places is not None:

            res_places = _tomar(f_places, None)

    scores_out: dict[str, int] = {}

    if cyber_ok:

        for oid in _OIDS_CYBER:

            scores_out[oid] = int(scores.get(oid, 0))

    if do_ext:

        for oid in _OIDS_EXT:

            scores_out[oid] = int(scores.get(oid, 0))

    if scores_out:

        volcar_scores_en_metricas(
            metricas, scores_out, ahora_utc(), marcar_ciber=cyber_ok
        )

        if do_ext:

            if razones is None:

                razones = (
                    ["Sin hallazgos confirmados en fuentes públicas."]
                    if scores_out.get("incidentes", 0) >= 100
                    else []
                )

            metricas.incidentes_razones = razones

        if cyber_ok and docs_razones is not None:

            metricas.docs_legales_razones = docs_razones

    elif do_cyber and not cyber_ok:

        metricas.ciber_escaneado_en = None

    if res_places is not None:

        _aplicar_places(metricas, res_places)

        metricas.actualizado_en = ahora_utc()

    elif do_places and metricas.google_rating_avg is None:

        metricas.google_rating_avg = 0.0

        metricas.google_reviews_count = 0

        metricas.google_place_nombre = None

        metricas.final_score = calcular_indice(
            EntradaScore(
                google_rating_avg=0.0,
                google_reviews_count=0,
                is_verified_profile=bool(metricas.is_verified_profile),
            )
        )

        metricas.actualizado_en = ahora_utc()
