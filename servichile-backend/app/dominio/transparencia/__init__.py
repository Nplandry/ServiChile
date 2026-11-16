"""Transparencia empresarial: un solo índice (señales + documentos)."""

from app.dominio.transparencia.rating import (
    RatingDocumentos,
    calcular_indice,
    calcular_rating_documentos,
    score_unificado,
)

__all__ = [
    "RatingDocumentos",
    "calcular_indice",
    "calcular_rating_documentos",
    "score_unificado",
]
