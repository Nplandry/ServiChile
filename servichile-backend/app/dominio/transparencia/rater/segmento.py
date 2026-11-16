"""Ajuste de pesos por segmento B2B vs B2C."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Segment = Literal["b2b", "b2c", "unknown"]

B2B_PATTERNS = [
    r"\bb2b\b",
    r"industrial",
    r"industria",
    r"manufactur",
    r"minería",
    r"mineria",
    r"construcción",
    r"construccion",
    r"ingenier[ií]a",
    r"consultor[ií]a",
    r"software",
    r"saas",
    r"tecnolog[ií]a",
    r"inform[aá]tica",
    r"ti\b",
    r"enterprise",
    r"mayorista",
    r"proveedor\s+b2b",
    r"servicios?\s+profesionales",
    r"outsourcing",
    r"log[ií]stica\s+industrial",
    r"erp",
    r"desarrollo\s+de\s+software",
    r"gesti[oó]n\s+empresarial",
]

B2C_PATTERNS = [
    r"\bb2c\b",
    r"retail",
    r"e-?commerce",
    r"comercio\s+minorista",
    r"tienda",
    r"restaurante",
    r"cafeter[ií]a",
    r"food",
    r"delivery\s+consumidor",
    r"consumo\s+masivo",
    r"peluquer[ií]a",
    r"belleza",
    r"turismo",
    r"hospedaje",
    r"supermercado",
    r"moda",
    r"retail\s+local",
]

B2B_WEIGHT_MULTIPLIERS: dict[str, float] = {
    "fis_hours": 0.35,
    "fis_reviews": 0.65,
    "fis_rating": 0.75,
    "con_tyc": 1.45,
    "con_sla": 1.55,
    "con_dpa": 1.50,
    "con_clausulas": 1.45,
    "con_privacy": 1.20,
    "con_ley_21719": 1.25,
}

B2C_WEIGHT_MULTIPLIERS: dict[str, float] = {
    "fis_hours": 1.40,
    "fis_reviews": 1.25,
    "fis_rating": 1.20,
    "con_sla": 0.85,
    "con_dpa": 0.90,
}


@dataclass(frozen=True)
class SegmentProfile:
    segment: Segment
    reason: str
    multipliers: dict[str, float]


def detect_segment(
    rubro: str | None = None,
    *,
    segment_hint: str | None = None,
    company_name: str | None = None,
) -> SegmentProfile:
    hint = (segment_hint or "").strip().lower()
    if hint in {"b2b", "b2c"}:
        mult = B2B_WEIGHT_MULTIPLIERS if hint == "b2b" else B2C_WEIGHT_MULTIPLIERS
        return SegmentProfile(segment=hint, reason=f"hint explícito ({hint})", multipliers=mult)

    blob = f"{rubro or ''} {company_name or ''}".lower()
    b2b_hits = [p for p in B2B_PATTERNS if re.search(p, blob, re.I)]
    b2c_hits = [p for p in B2C_PATTERNS if re.search(p, blob, re.I)]

    if b2b_hits and not b2c_hits:
        return SegmentProfile(
            segment="b2b",
            reason=f"rubro/nombre B2B ({', '.join(b2b_hits[:3])})",
            multipliers=B2B_WEIGHT_MULTIPLIERS,
        )
    if b2c_hits and not b2b_hits:
        return SegmentProfile(
            segment="b2c",
            reason=f"rubro/nombre B2C ({', '.join(b2c_hits[:3])})",
            multipliers=B2C_WEIGHT_MULTIPLIERS,
        )
    if b2b_hits and b2c_hits:
        return SegmentProfile(
            segment="b2b",
            reason=f"señales mixtas; prioriza B2B ({', '.join(b2b_hits[:2])})",
            multipliers=B2B_WEIGHT_MULTIPLIERS,
        )
    return SegmentProfile(segment="unknown", reason="sin señal clara; pesos base", multipliers={})


def effective_weight(base_weight: float, param_id: str, profile: SegmentProfile) -> float:
    mult = profile.multipliers.get(param_id, 1.0)
    return round(max(0.05, base_weight * mult), 3)


# Alias usado por el motor ServiChile (mismo contrato).
