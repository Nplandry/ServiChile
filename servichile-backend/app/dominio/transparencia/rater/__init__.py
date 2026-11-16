"""Rater empresarial: parámetros externos + motor de score."""

from app.dominio.transparencia.rater.motor import ResultadoRater, build_scores
from app.dominio.transparencia.rater.parametros import PARAMETROS

__all__ = ["PARAMETROS", "ResultadoRater", "build_scores"]
