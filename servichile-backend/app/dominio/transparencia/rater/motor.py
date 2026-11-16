"""Motor de puntuación: pesos por segmento + overall + proyección a observables."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.dominio.entidades import ObservableSenal
from app.dominio.transparencia.rater.parametros import (
    GRUPO_FE,
    PARAMETROS,
    CategoriaRater,
    grade_from_score,
)
from app.dominio.transparencia.rater.segmento import (
    SegmentProfile,
    detect_segment,
    effective_weight,
)


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, float(v)))


@dataclass(frozen=True, slots=True)
class ParametroScore:
    id: str
    nombre: str
    categoria: CategoriaRater
    score: float | None
    peso: float
    evidencia: str | None = None
    fuente: str | None = None
    status: str = "ok"


@dataclass(frozen=True, slots=True)
class CategoriaScore:
    categoria: CategoriaRater
    score: float | None
    scored: bool
    parametros: tuple[ParametroScore, ...]


@dataclass
class ResultadoRater:
    overall_score: float | None
    grade: str | None
    categorias: list[CategoriaScore]
    parametros: list[ParametroScore]
    ficha_fiable: bool | None = None
    summary: str | None = None
    recommendations: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def a_observables(self) -> list[ObservableSenal]:
        out: list[ObservableSenal] = []
        for p in self.parametros:
            score = 0 if p.score is None else int(round(_clamp(p.score)))
            out.append(
                ObservableSenal(
                    id=p.id,
                    etiqueta=p.nombre,
                    detalle="",
                    score=score,
                    peso=f"{p.peso:.1f}",
                    grupo=GRUPO_FE.get(p.categoria, "operativa"),
                    razones=[],
                )
            )
        return out


def build_scores(
    *,
    hints: dict[str, float],
    evidence_map: dict[str, str] | None = None,
    source_map: dict[str, str] | None = None,
    status_map: dict[str, str] | None = None,
    rubro: str | None = None,
    company_name: str | None = None,
    segment_hint: str | None = None,
    ficha_fiable: bool | None = None,
    summary: str | None = None,
    recommendations: list[str] | None = None,
    metadata: dict | None = None,
) -> ResultadoRater:
    evidence_map = evidence_map or {}
    source_map = source_map or {}
    status_map = status_map or {}
    profile = detect_segment(
        rubro, segment_hint=segment_hint, company_name=company_name
    )

    params: list[ParametroScore] = []
    for pdef in PARAMETROS:
        status = status_map.get(pdef.id)
        raw = hints.get(pdef.id)
        weight = effective_weight(pdef.peso, pdef.id, profile)
        if status in {"skipped", "unscored", "error"}:
            params.append(
                ParametroScore(
                    id=pdef.id,
                    nombre=pdef.nombre,
                    categoria=pdef.categoria,
                    score=None,
                    peso=weight,
                    evidencia=evidence_map.get(pdef.id),
                    fuente=source_map.get(pdef.id),
                    status=status,
                )
            )
            continue
        if raw is None:
            params.append(
                ParametroScore(
                    id=pdef.id,
                    nombre=pdef.nombre,
                    categoria=pdef.categoria,
                    score=None,
                    peso=weight,
                    evidencia=evidence_map.get(pdef.id),
                    fuente=source_map.get(pdef.id),
                    status=status or "missing",
                )
            )
            continue
        params.append(
            ParametroScore(
                id=pdef.id,
                nombre=pdef.nombre,
                categoria=pdef.categoria,
                score=round(_clamp(raw), 1),
                peso=weight,
                evidencia=evidence_map.get(pdef.id),
                fuente=source_map.get(pdef.id),
                status=status or "ok",
            )
        )

    by_cat: dict[CategoriaRater, list[ParametroScore]] = defaultdict(list)
    for p in params:
        by_cat[p.categoria].append(p)

    categories: list[CategoriaScore] = []
    weighted_total = 0.0
    weight_sum = 0.0
    for cat, plist in by_cat.items():
        measured = [x for x in plist if x.status == "ok" and x.score is not None]
        if not measured:
            categories.append(
                CategoriaScore(categoria=cat, score=None, scored=False, parametros=tuple(plist))
            )
            continue
        w = sum(x.peso for x in measured) or 1.0
        cat_score = sum((x.score or 0.0) * x.peso for x in measured) / w
        categories.append(
            CategoriaScore(
                categoria=cat,
                score=round(cat_score, 1),
                scored=True,
                parametros=tuple(plist),
            )
        )
        weighted_total += cat_score * w
        weight_sum += w

    overall = round(weighted_total / weight_sum, 1) if weight_sum else None
    meta = {
        **(metadata or {}),
        "segment": profile.segment,
        "segment_reason": profile.reason,
        "measured_parameters": sum(1 for p in params if p.status == "ok" and p.score is not None),
    }
    return ResultadoRater(
        overall_score=overall,
        grade=grade_from_score(overall) if overall is not None else None,
        categorias=sorted(categories, key=lambda c: c.categoria),
        parametros=params,
        ficha_fiable=ficha_fiable,
        summary=summary,
        recommendations=list(recommendations or []),
        metadata=meta,
    )


def block_fisica(
    hints: dict[str, float],
    evidence: dict[str, str],
    sources: dict[str, str],
    status: dict[str, str],
    *,
    reason: str,
) -> None:
    from app.dominio.transparencia.rater.parametros import IDS_FISICA

    for pid in IDS_FISICA:
        hints.pop(pid, None)
        status[pid] = "unscored"
        evidence[pid] = reason
        sources[pid] = "ficha_confidence"
