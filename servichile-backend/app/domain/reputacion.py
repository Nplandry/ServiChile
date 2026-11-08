"""Cálculo del Índice de Transparencia de un negocio.

Blindaje legal (ver README): el índice es un indicador algorítmico sobre datos
públicos y nivel de verificación, NUNCA un juicio de valor sobre la calidad del
servicio. Este módulo solo combina métricas estadísticas; no interpreta ni
almacena opiniones. Es código puro, sin dependencias de base de datos ni de red,
para poder probar la fórmula de forma aislada.
"""
from __future__ import annotations

from dataclasses import dataclass

# Ponderaciones fijas y auditables. Suman 1.0.
PESO_GOOGLE = 0.4
PESO_VOLUMEN = 0.3
PESO_VERIFICACION = 0.3

# El volumen de reseñas se normaliza de forma logarítmica: duplicar reseñas no
# duplica el aporte. Este valor es la cantidad de reseñas que alcanza el tope.
VOLUMEN_SATURACION = 500

# Factor de verificación neutro para perfiles no reclamados: no premia ni castiga.
# Un perfil reclamado y verificado por su dueño recibe el factor máximo.
FACTOR_VERIFICACION_NEUTRO = 0.6
FACTOR_VERIFICACION_VERIFICADO = 1.0

ESCALA_MIN = 1.0
ESCALA_MAX = 10.0


@dataclass(frozen=True)
class EntradaScore:
    """Datos crudos que alimentan la fórmula. Todos opcionales salvo verificación."""

    google_rating_avg: float | None  # 0.0 a 5.0 (estrellas de Google Maps)
    google_reviews_count: int  # volumen de reseñas públicas
    is_verified_profile: bool  # ¿el dueño administra el perfil?


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def _normalizar_volumen(reviews_count: int) -> float:
    """Devuelve 0.0 a 1.0. Crecimiento logarítmico que satura en VOLUMEN_SATURACION."""
    import math

    if reviews_count <= 0:
        return 0.0
    ratio = math.log1p(reviews_count) / math.log1p(VOLUMEN_SATURACION)
    return _clamp(ratio, 0.0, 1.0)


def _factor_verificacion(is_verified: bool) -> float:
    return FACTOR_VERIFICACION_VERIFICADO if is_verified else FACTOR_VERIFICACION_NEUTRO


def calcular_indice(entrada: EntradaScore) -> float:
    """Índice de Transparencia de 1.0 a 10.0, redondeado a un decimal.

    Fórmula: (0.4 × Google normalizado) + (0.3 × Volumen normalizado)
             + (0.3 × Factor de verificación), reescalada a 1.0–10.0.

    Si no hay promedio de Google (negocio sin reseñas públicas), ese componente
    aporta 0 pero no invalida el índice: prevalece el volumen y la verificación.
    """
    # Cada componente se expresa en 0.0–1.0 antes de ponderar.
    google_norm = _clamp((entrada.google_rating_avg or 0.0) / 5.0, 0.0, 1.0)
    volumen_norm = _normalizar_volumen(entrada.google_reviews_count)
    verificacion = _factor_verificacion(entrada.is_verified_profile)

    ponderado = (
        PESO_GOOGLE * google_norm
        + PESO_VOLUMEN * volumen_norm
        + PESO_VERIFICACION * verificacion
    )  # 0.0 a 1.0

    indice = ESCALA_MIN + ponderado * (ESCALA_MAX - ESCALA_MIN)
    return round(_clamp(indice, ESCALA_MIN, ESCALA_MAX), 1)
