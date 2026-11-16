"""Algoritmo de confianza de ficha (Google Places / identidad física).

Prioridad: baja tasa de falsos positivos y falsos negativos.
- FP: nunca puntuar una ficha de otra empresa (p.ej. Geodetec ≠ Gestech).
- FN: si websiteUri = dominio de la empresa, aceptar aunque el nombre difiera un poco.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse


STOPWORDS = {
    "ltda",
    "limitada",
    "spa",
    "sa",
    "s.a",
    "s.a.",
    "eirl",
    "chile",
    "para",
    "de",
    "la",
    "el",
    "los",
    "las",
    "y",
    "e",
    "del",
    "informacion",
    "información",
    "gestion",
    "gestión",
    "tecnologia",
    "tecnología",
    "empresa",
    "servicios",
    "servicio",
    "service",
    "services",
    "group",
    "grupo",
    "company",
    "comercial",
}

FOREIGN_MARKERS = (
    "colombia",
    "méxico",
    "mexico",
    "argentina",
    "perú",
    "peru",
    "españa",
    "spain",
    "usa",
    "united states",
    ".com.co",
    ".com.mx",
    ".com.ar",
    ".com.br",
    ".com.pe",
)

CHILE_HINTS = (
    "chile",
    "santiago",
    "región metropolitana",
    "region metropolitana",
    "valparaíso",
    "valparaiso",
    "biobío",
    "biobio",
    "araucanía",
    "araucania",
    "los lagos",
    "antofagasta",
    "coquimbo",
    "ñuble",
    "nuble",
    "maule",
    "ohiggins",
    "o'higgins",
)


@dataclass
class FichaAssessment:
    reliable: bool
    confidence: float  # 0..1
    match_score: int
    reasons: list[str] = field(default_factory=list)
    place_name: str | None = None
    place_address: str | None = None
    place_website: str | None = None
    name_match: bool = False
    domain_match: bool = False
    chile_match: bool = False
    foreign: bool = False
    brand_collision: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _host(url: str | None) -> str:
    if not url:
        return ""
    u = url.lower().strip()
    if not u.startswith("http"):
        u = "https://" + u
    host = (urlparse(u).netloc or "").removeprefix("www.")
    return host


def domain_stem(domain: str | None) -> str | None:
    host = _host(domain) if domain and "://" in (domain or "") else (domain or "").lower()
    host = host.removeprefix("www.").split("/")[0]
    if not host:
        return None
    stem = host.split(".")[0]
    return stem if len(stem) >= 3 else None


def brand_tokens(company_name: str | None, domain: str | None = None) -> list[str]:
    """Tokens de marca distintivos; el stem del dominio va primero."""
    tokens: list[str] = []
    stem = domain_stem(domain)
    if stem and stem not in STOPWORDS:
        tokens.append(stem)

    raw = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+", company_name or "")
    for t in raw:
        folded = _fold(t)
        min_len = 3 if stem and folded == stem else 4
        if len(folded) < min_len or folded in STOPWORDS:
            continue
        if folded not in tokens:
            tokens.append(folded)
    return tokens


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins, delete, sub = cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def _similar_but_different(a: str, b: str) -> bool:
    """Detecta colisiones tipo gestech/geodetec (parecido ≠ mismo)."""
    if not a or not b or a == b:
        return False
    if a in b or b in a:
        return False
    # Solo comparar tokens de longitud similar (marcas)
    if abs(len(a) - len(b)) > 4:
        return False
    if min(len(a), len(b)) < 5:
        return False
    dist = _levenshtein(a, b)
    ratio = dist / max(len(a), len(b))
    # Parecidos pero no iguales
    return 0.15 <= ratio <= 0.45


def _place_name_tokens(pname: str) -> list[str]:
    return [
        t
        for t in re.findall(r"[a-z0-9]+", _fold(pname))
        if len(t) >= 3 and t not in STOPWORDS
    ]


def name_affiliation(tokens: list[str], place_name: str) -> tuple[bool, str]:
    """
    Match fuerte de nombre: algún token de marca aparece como token completo
    en el displayName (evita substring accidental).
    """
    pname = _fold(place_name)
    if not tokens or not pname:
        return False, "sin nombre Places o sin tokens"
    ptoks = set(_place_name_tokens(pname))
    # También aceptar token como palabra completa en el string
    for tok in tokens:
        if tok in ptoks:
            return True, f"token '{tok}' en nombre Places"
        if re.search(rf"(^|[^a-z0-9]){re.escape(tok)}([^a-z0-9]|$)", pname):
            return True, f"token '{tok}' como palabra en nombre Places"
    return False, f"ningún token {tokens} en '{place_name}'"


def detect_brand_collision(tokens: list[str], place_name: str) -> bool:
    ptoks = _place_name_tokens(place_name)
    for tok in tokens:
        for pt in ptoks:
            if _similar_but_different(tok, pt):
                return True
    return False


def domains_match(company_domain: str, website_uri: str | None) -> bool:
    """Match estricto de host (mismo sitio o subdominio)."""
    want = _host(company_domain) or (company_domain or "").lower().removeprefix("www.")
    got = _host(website_uri)
    if not want or not got:
        return False
    want = want.split("/")[0]
    return got == want or got.endswith("." + want)


def score_place_candidate(
    place: dict[str, Any],
    *,
    company_name: str | None,
    domain: str,
    comuna: str | None = None,
    ciudad: str | None = None,
) -> FichaAssessment:
    """Evalúa un candidato Places y decide si la ficha es usable para scoring."""
    addr = (place.get("formattedAddress") or "").lower()
    web = (place.get("websiteUri") or "").lower()
    pname_raw = (place.get("displayName") or {}).get("text") or ""
    pname = _fold(pname_raw)
    web_host = _host(place.get("websiteUri"))
    tokens = brand_tokens(company_name, domain)

    reasons: list[str] = []
    score = 0

    domain_match = domains_match(domain, place.get("websiteUri"))
    if domain_match:
        score += 80
        reasons.append(f"dominio coincide ({web_host})")
    elif web_host:
        reasons.append(f"dominio no coincide (web={web_host})")
        score -= 25
    else:
        reasons.append("ficha sin websiteUri")

    name_match, name_reason = name_affiliation(tokens, pname_raw)
    if name_match:
        score += 70
        reasons.append(name_reason)
    elif tokens:
        score -= 40
        reasons.append(name_reason)
    else:
        reasons.append("sin tokens de marca para validar nombre")

    brand_collision = False
    if tokens and not name_match and not domain_match:
        brand_collision = detect_brand_collision(tokens, pname_raw)
        if brand_collision:
            score -= 60
            reasons.append("posible colisión de marca parecida (FP)")

    chile_match = any(h in addr for h in CHILE_HINTS) or (
        web_host.endswith(".cl") if web_host else False
    )
    if chile_match:
        score += 25
        reasons.append("señales de ubicación Chile")
    else:
        score -= 30
        reasons.append("sin señales claras de Chile en dirección/web")

    foreign = any(m in addr or m in web for m in FOREIGN_MARKERS)
    if foreign:
        score -= 100
        reasons.append("posible ubicación/dominio extranjero")

    if comuna and _fold(comuna) in _fold(addr):
        score += 10
        reasons.append(f"comuna '{comuna}' en dirección")
    if ciudad and _fold(ciudad) in _fold(addr):
        score += 5
        reasons.append(f"ciudad '{ciudad}' en dirección")

    # Confianza 0..1 (rango útil aprox. -100..190)
    confidence = max(0.0, min(1.0, (score + 100) / 290.0))

    # --- Reglas duras (baja FP) ---
    reliable = True
    hard_fails: list[str] = []

    if foreign:
        reliable = False
        hard_fails.append("ficha extranjera")
    if brand_collision and not domain_match:
        reliable = False
        hard_fails.append("colisión de marca sin dominio")
    if not chile_match and not domain_match:
        # Dominio .cl propio implica Chile aunque la dirección venga incompleta
        reliable = False
        hard_fails.append("sin evidencia Chile")

    # Identidad: dominio fuerte O nombre fuerte (+Chile)
    identity_ok = False
    if domain_match:
        identity_ok = True
        reasons.append("identidad por dominio (reduce FN)")
    elif name_match and chile_match:
        identity_ok = True
        reasons.append("identidad por nombre+Chile")
    else:
        reliable = False
        hard_fails.append("sin identidad fuerte (ni dominio ni nombre+Chile)")

    if identity_ok and domain_match:
        # Dominio exacto: umbral más bajo (aceptar nombre comercial distinto)
        if score < 55:
            reliable = False
            hard_fails.append(f"match_score insuficiente con dominio ({score}<55)")
        if confidence < 0.40:
            reliable = False
            hard_fails.append(f"confianza baja ({confidence:.2f}<0.40)")
    elif identity_ok:
        # Solo nombre: umbral más alto (baja FP)
        if score < 80:
            reliable = False
            hard_fails.append(f"match_score insuficiente sin dominio ({score}<80)")
        if confidence < 0.55:
            reliable = False
            hard_fails.append(f"confianza baja ({confidence:.2f}<0.55)")

    if not reliable:
        reasons.append("NO CONFIABLE: " + "; ".join(hard_fails))
    else:
        reasons.append("CONFIABLE para scoring físico/reputacional")

    return FichaAssessment(
        reliable=reliable,
        confidence=round(confidence, 3),
        match_score=score,
        reasons=reasons,
        place_name=pname_raw or None,
        place_address=place.get("formattedAddress"),
        place_website=place.get("websiteUri"),
        name_match=name_match,
        domain_match=domain_match,
        chile_match=chile_match,
        foreign=foreign,
        brand_collision=brand_collision,
    )


def pick_reliable_place(
    places: list[dict[str, Any]],
    *,
    company_name: str | None,
    domain: str,
    comuna: str | None = None,
    ciudad: str | None = None,
) -> tuple[dict[str, Any] | None, FichaAssessment]:
    """Elige el mejor candidato; solo lo retorna si la ficha es confiable."""
    if not places:
        empty = FichaAssessment(
            reliable=False,
            confidence=0.0,
            match_score=0,
            reasons=["sin candidatos Places"],
        )
        return None, empty

    ranked: list[tuple[FichaAssessment, dict[str, Any]]] = []
    for p in places:
        assessment = score_place_candidate(
            p,
            company_name=company_name,
            domain=domain,
            comuna=comuna,
            ciudad=ciudad,
        )
        ranked.append((assessment, p))
    # Preferir: reliable > domain_match > score > confidence
    ranked.sort(
        key=lambda x: (
            x[0].reliable,
            x[0].domain_match,
            x[0].name_match,
            x[0].match_score,
            x[0].confidence,
        ),
        reverse=True,
    )
    best_assessment, best_place = ranked[0]
    if not best_assessment.reliable:
        return None, best_assessment
    return best_place, best_assessment


FISICA_PARAM_IDS = (
    "fis_places_exists",
    "fis_rating",
    "fis_reviews",
    "fis_address",
    "fis_phone",
    "fis_hours",
)
