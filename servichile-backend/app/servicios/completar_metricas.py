from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait

from app.dominio.entidades import Metricas
from app.dominio.puertos import (
    NuloCmf,
    NuloDatalux,
    NuloIncidentes,
    NuloMercadoPublico,
    NuloPlaces,
    NuloSii,
    ProveedorCmf,
    ProveedorDatalux,
    ProveedorIncidentes,
    ProveedorMercadoPublico,
    ProveedorPlaces,
    ProveedorSii,
    ResultadoIncidentes,
    ResultadoPlaces,
    SondaCiber,
)
from app.dominio.transparencia.datalux import SCORE_BASE, scores_desde_ficha
from app.dominio.transparencia.metricas import (
    necesita_datalux,
    necesita_extensiones,
    necesita_places,
    necesita_sonda_ciber,
    scores_desde_metricas,
    volcar_scores_en_metricas,
)
from app.dominio.transparencia.reputacion import EntradaScore, calcular_indice
from app.tiempo import ahora_utc

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
_OIDS_EXT = ("mercado-publico", "sii", "cmf", "incidentes")
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


def _tomar(fut: Future | None, default):
    if fut is None:
        return default
    try:
        return fut.result(timeout=0)
    except Exception:
        return default


def _consulta_datalux(rut: str | None, nombre: str | None) -> str | None:
    q = (rut or nombre or "").strip()
    return q or None


def completar_metricas(
    metricas: Metricas,
    sonda: SondaCiber,
    sitio_web: str | None,
    *,
    chilecompra: ProveedorMercadoPublico | None = None,
    sii: ProveedorSii | None = None,
    cmf: ProveedorCmf | None = None,
    incidentes: ProveedorIncidentes | None = None,
    places: ProveedorPlaces | None = None,
    datalux: ProveedorDatalux | None = None,
    rut: str | None = None,
    nombre: str | None = None,
    direccion: str | None = None,
    forzar: bool = False,
) -> None:
    chilecompra = chilecompra or NuloMercadoPublico()
    sii = sii or NuloSii()
    cmf = cmf or NuloCmf()
    incidentes = incidentes or NuloIncidentes()
    places = places or NuloPlaces()
    datalux = datalux or NuloDatalux()

    do_cyber = forzar or necesita_sonda_ciber(metricas)
    # Extensiones solo si faltan (o forzar); no re-disparar por cyber.
    do_ext = forzar or necesita_extensiones(metricas)
    do_places = forzar or necesita_places(metricas)
    do_datalux = forzar or necesita_datalux(metricas)
    if not (do_cyber or do_ext or do_places or do_datalux):
        return

    scores = scores_desde_metricas(metricas)
    razones = (
        list(metricas.incidentes_razones)
        if metricas.incidentes_razones is not None
        else None
    )
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
        consulta_dl = _consulta_datalux(rut, nombre) if do_datalux else None
        f_datalux = (
            pool.submit(datalux.consultar, consulta_dl) if consulta_dl else None
        )

        pendientes = [
            f
            for f in (f_cyber, f_mp, f_sii, f_cmf, f_inc, f_places, f_datalux)
            if f is not None
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

        if do_datalux:
            ficha = _tomar(f_datalux, None) if f_datalux is not None else None
            dl = scores_desde_ficha(
                nombre=nombre, direccion=direccion, rut_empresa=rut, ficha=ficha
            )
            scores.update(dl.como_dict())
            metricas.datalux_razones = dl.razones

    scores_out: dict[str, int] = {}
    if cyber_ok:
        for oid in _OIDS_CYBER:
            scores_out[oid] = int(scores.get(oid, 0))
    if do_ext:
        for oid in _OIDS_EXT:
            scores_out[oid] = int(scores.get(oid, 0))
    if do_datalux:
        scores_out["persona-juridica"] = int(scores.get("persona-juridica", 0))
        scores_out["domicilio"] = int(scores.get("domicilio", SCORE_BASE))
        scores_out["huella-digital"] = int(scores.get("huella-digital", SCORE_BASE))

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
