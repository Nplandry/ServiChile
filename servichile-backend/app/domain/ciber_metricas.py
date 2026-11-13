from __future__ import annotations
from datetime import datetime
from app.domain.ciber_observables import armar_observables, score_resenas
from app.domain.entidades import Metricas, ObservableCiber
CAMPOS_SCORE_SONDA: tuple[tuple[str, str], ...] = (('ssl-tls', 'score_ssl_tls'), ('email-auth', 'score_email_auth'), ('puertos', 'score_puertos'), ('headers-http', 'score_headers_http'), ('stack-vulnerable', 'score_stack_vulnerable'), ('blacklist', 'score_blacklist'), ('dnssec', 'score_dnssec'), ('subdominios', 'score_subdominios'), ('whois', 'score_whois'), ('uptime', 'score_uptime'))

def metricas_necesitan_escaneo(m: Metricas) -> bool:
    return m.ciber_escaneado_en is None or m.score_email_auth is None

def volcar_scores_en_metricas(metricas: Metricas, scores: dict[str, int], ahora: datetime) -> None:
    for oid, attr in CAMPOS_SCORE_SONDA:
        setattr(metricas, attr, float(scores.get(oid, 0)))
    metricas.ciber_escaneado_en = ahora

def valores_desde_metricas(m: Metricas) -> dict[str, int]:
    if m.ciber_escaneado_en is None and m.score_ssl_tls is None:
        return {}
    valores = {oid: int(getattr(m, attr) if getattr(m, attr) is not None else 0) for oid, attr in CAMPOS_SCORE_SONDA}
    valores['resenas-reclamos'] = score_resenas(m.google_rating_avg, m.google_reviews_count or 0)
    return valores

def observables_desde_metricas(m: Metricas) -> list[ObservableCiber]:
    valores = valores_desde_metricas(m)
    if not valores:
        return []
    return [ObservableCiber(id=s.id, etiqueta=s.etiqueta, detalle=s.detalle, score=s.score, peso=s.peso, grupo=s.grupo) for s in armar_observables(valores)]
