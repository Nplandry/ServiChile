"""Índice único: señales públicas (rater) + documentos legales → un solo score."""

from __future__ import annotations

from dataclasses import dataclass

from app.dominio.docs_empresa import (
    DocsEmpresa,
    MetaDocEmpresa,
    TIPOS_DOC_EMPRESA,
    label_tipo,
)
from app.dominio.entidades import ObservableSenal

_TOTAL_DOCS = len(TIPOS_DOC_EMPRESA)
# Mitad señales públicas, mitad documentación verificada.
_PESO_RATER = 0.5
_PESO_DOCS = 0.5


@dataclass(frozen=True, slots=True)
class RatingDocumentos:
    verificados: int
    total: int
    pct: int  # 0–100
    indice: float  # ★ 0.0–10.0


_RATING_VACIO = RatingDocumentos(0, _TOTAL_DOCS, 0, 0.0)
_RATING_COMPLETO = RatingDocumentos(_TOTAL_DOCS, _TOTAL_DOCS, 100, 10.0)


def _meta_verificado(meta: object) -> bool:
    return isinstance(meta, MetaDocEmpresa) and bool(meta.verificado)


def doc_esta_verificado(docs: DocsEmpresa | None, tipo: str) -> bool:
    if not docs:
        return False
    return _meta_verificado(docs.get(tipo))


def calcular_rating_documentos(docs: DocsEmpresa | None) -> RatingDocumentos:
    """Proporción de documentos legales validados (0–100% → ★ 0–10)."""
    if not docs:
        return _RATING_VACIO

    verificados = 0
    for tipo in TIPOS_DOC_EMPRESA:
        if _meta_verificado(docs.get(tipo)):
            verificados += 1

    if verificados == 0:
        return _RATING_VACIO
    if verificados >= _TOTAL_DOCS:
        return _RATING_COMPLETO

    return RatingDocumentos(
        verificados=verificados,
        total=_TOTAL_DOCS,
        pct=int(round(100.0 * verificados / _TOTAL_DOCS)),
        indice=round(10.0 * verificados / _TOTAL_DOCS, 1),
    )


def score_unificado(*, rater_pct: float | None, docs_pct: int) -> tuple[float, int]:
    """Un solo índice: ★ 0–10 y % 0–100 (rater + documentos)."""
    r = 0.0 if rater_pct is None else max(0.0, min(100.0, float(rater_pct)))
    d = max(0, min(100, int(docs_pct)))
    pct = int(round(_PESO_RATER * r + _PESO_DOCS * d))
    return round(pct / 10.0, 1), pct


def observables_documentos(docs: DocsEmpresa | None) -> list[ObservableSenal]:
    """Cada documento legal es una señal del índice (legal, 0 o 100)."""
    out: list[ObservableSenal] = []
    for tipo in TIPOS_DOC_EMPRESA:
        ok = doc_esta_verificado(docs, tipo)
        out.append(
            ObservableSenal(
                id=f"doc_{tipo}",
                etiqueta=label_tipo(tipo),
                detalle="",
                score=100 if ok else 0,
                peso="1.0",
                grupo="documentos",
                razones=[],
            )
        )
    return out


def calcular_indice(docs: DocsEmpresa | None = None) -> float:
    return calcular_rating_documentos(docs).indice


def es_observable_documento(oid: str) -> bool:
    return str(oid or "").startswith("doc_")
