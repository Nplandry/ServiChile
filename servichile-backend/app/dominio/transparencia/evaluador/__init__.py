"""Evaluador empresarial: parámetros externos + motor de puntaje."""

from app.dominio.transparencia.evaluador.motor import ResultadoEvaluador, construir_puntajes
from app.dominio.transparencia.evaluador.parametros import PARAMETROS

__all__ = ["PARAMETROS", "ResultadoEvaluador", "construir_puntajes"]