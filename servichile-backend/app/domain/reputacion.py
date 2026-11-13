from __future__ import annotations
from dataclasses import dataclass
PESO_GOOGLE = 0.4
PESO_VOLUMEN = 0.3
PESO_VERIFICACION = 0.3
VOLUMEN_SATURACION = 500
FACTOR_VERIFICACION_NEUTRO = 0.6
FACTOR_VERIFICACION_VERIFICADO = 1.0
ESCALA_MIN = 1.0
ESCALA_MAX = 10.0

@dataclass(frozen=True)
class EntradaScore:
    google_rating_avg: float | None
    google_reviews_count: int
    is_verified_profile: bool

def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))

def _normalizar_volumen(reviews_count: int) -> float:
    import math
    if reviews_count <= 0:
        return 0.0
    ratio = math.log1p(reviews_count) / math.log1p(VOLUMEN_SATURACION)
    return _clamp(ratio, 0.0, 1.0)

def _factor_verificacion(is_verified: bool) -> float:
    return FACTOR_VERIFICACION_VERIFICADO if is_verified else FACTOR_VERIFICACION_NEUTRO

def calcular_indice(entrada: EntradaScore) -> float:
    google_norm = _clamp((entrada.google_rating_avg or 0.0) / 5.0, 0.0, 1.0)
    volumen_norm = _normalizar_volumen(entrada.google_reviews_count)
    verificacion = _factor_verificacion(entrada.is_verified_profile)
    ponderado = PESO_GOOGLE * google_norm + PESO_VOLUMEN * volumen_norm + PESO_VERIFICACION * verificacion
    indice = ESCALA_MIN + ponderado * (ESCALA_MAX - ESCALA_MIN)
    return round(_clamp(indice, ESCALA_MIN, ESCALA_MAX), 1)
