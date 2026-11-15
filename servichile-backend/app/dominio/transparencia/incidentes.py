from __future__ import annotations

from dataclasses import dataclass

from app.dominio.transparencia.indicadores import DefinicionObservable, PESO_OPERATIVA

OBSERVABLE_INCIDENTES = DefinicionObservable(
    id="incidentes",
    etiqueta="Historial de incidentes físicos, brechas o escándalos públicos",
    detalle="",
    grupo="operativa",
    peso=PESO_OPERATIVA,
)

KEYWORDS_RIESGO: tuple[str, ...] = (
    "fraude",
    "estafa",
    "brecha de datos",
    "ransomware",
    "accidente fatal",
    "clausura",
    "demanda",
    "colusión",
    "escándalo",
    "filtración",
)

KEYWORDS_SEVEROS: tuple[str, ...] = (
    "ransomware",
    "accidente fatal",
    "colusión",
    "fraude",
    "estafa",
)

_TITULOS_BASURA: tuple[str, ...] = (
    "tiktok - make your day",
    "make your day",
    "instagram",
    "facebook",
    "youtube",
    "linkedin",
    "twitter",
    "x.com",
)

_DOMINIOS_BAJA_SENAL: tuple[str, ...] = (
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "fb.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "youtu.be",
    "linkedin.com",
)

_ALIAS_TOKEN: dict[str, tuple[str, ...]] = {
    "gym": ("gym", "gimnasio", "gimnasios", "fitness"),
    "spa": ("spa",),
}


@dataclass(frozen=True)
class SnippetBusqueda:

    titulo: str

    url: str

    texto: str

    consulta: str = ""


@dataclass(frozen=True)
class HallazgosIncidentes:

    nombre_consultable: bool = False

    busqueda_ok: bool = False

    snippets_crudos: int = 0

    confirmados: int = 0

    severos: int = 0


_KEYWORDS_RAPIDAS: tuple[str, ...] = (
    "fraude",
    "estafa",
    "demanda",
    "clausura",
    "colusión",
    "escándalo",
)


def armar_consultas(nombre: str, *, max_queries: int = 1) -> list[str]:

    limpio = " ".join(str(nombre or "").split()).strip()

    if len(limpio) < 2:

        return []

    quoted = f'"{limpio}"'

    grupo = " OR ".join(_KEYWORDS_RAPIDAS)

    out = [f"{quoted} ({grupo}) Chile"]

    if max_queries <= 1:

        return out

    for kw in KEYWORDS_RIESGO:

        if kw in _KEYWORDS_RAPIDAS:

            continue

        if len(out) >= max_queries:

            break

        out.append(f"{quoted} {kw} Chile")

    return out


def score_incidentes(h: HallazgosIncidentes) -> int:

    if not h.nombre_consultable or not h.busqueda_ok:

        return 0

    if h.confirmados <= 0:

        return 100

    if h.severos > 0 or h.confirmados >= 4:

        return 25

    if h.confirmados >= 2:

        return 50

    return 75


def texto_tiene_nombre(texto: str, nombre: str) -> bool:

    t = _norm(texto)

    n = _norm(nombre)

    if len(n) < 3:

        return False

    if n in t:

        return True

    toks = [p for p in n.split() if len(p) >= 3]

    if not toks:

        return False

    return all((_token_en_texto(t, p) for p in toks))


def texto_tiene_riesgo(texto: str) -> bool:

    t = _norm(texto)

    return any((_norm(kw) in t for kw in KEYWORDS_RIESGO))


def es_severo(texto: str) -> bool:

    t = _norm(texto)

    return any((_norm(kw) in t for kw in KEYWORDS_SEVEROS))


def es_snippet_basura(s: SnippetBusqueda) -> bool:

    tit = _norm(s.titulo)

    if not tit or len(tit) < 16:

        return True

    if any((tit == b or tit.startswith(b + " ") for b in _TITULOS_BASURA)):

        return True

    url = _norm(s.url)

    if any((d in url for d in _DOMINIOS_BAJA_SENAL)):

        return True

    return False


def filtrar_heuristico(
    nombre: str, snippets: list[SnippetBusqueda]
) -> list[SnippetBusqueda]:

    out: list[SnippetBusqueda] = []

    vistos: set[str] = set()

    for s in snippets:

        if es_snippet_basura(s):

            continue

        blob = f"{s.titulo} {s.texto}"

        if not texto_tiene_nombre(blob, nombre):

            continue

        if not texto_tiene_riesgo(blob):

            continue

        clave = _norm(s.url) or _norm(s.titulo)[:80]

        if clave in vistos:

            continue

        vistos.add(clave)

        out.append(s)

    return out


def hallazgos_desde_confirmados(
    *,
    nombre_consultable: bool,
    busqueda_ok: bool,
    snippets_crudos: int,
    confirmados: list[SnippetBusqueda],
) -> HallazgosIncidentes:

    severos = sum((1 for s in confirmados if es_severo(f"{s.titulo} {s.texto}")))

    return HallazgosIncidentes(
        nombre_consultable=nombre_consultable,
        busqueda_ok=busqueda_ok,
        snippets_crudos=snippets_crudos,
        confirmados=len(confirmados),
        severos=severos,
    )


def razones_breves(
    h: HallazgosIncidentes, confirmados: list[SnippetBusqueda], *, max_items: int = 5
) -> list[str]:

    if not h.nombre_consultable:

        return ["Sin nombre consultable."]

    if not h.busqueda_ok:

        return ["Sin búsqueda usable."]

    if not confirmados:

        return ["Sin hallazgos confirmados en fuentes públicas."]

    out: list[str] = []

    for s in confirmados[:max_items]:

        titulo = " ".join(str(s.titulo or "").split()).strip()

        if not titulo:

            titulo = " ".join(str(s.url or "").split()).strip() or "Fuente pública"

        if len(titulo) > 110:

            titulo = titulo[:107] + "…"

        tag = "Severo" if es_severo(f"{s.titulo} {s.texto}") else "Hallazgo"

        out.append(f"{tag}: {titulo}")

    resto = len(confirmados) - max_items

    if resto > 0:

        out.append(f"+{resto} hallazgo(s) más")

    return out


def _token_en_texto(texto_norm: str, token: str) -> bool:

    variantes = _ALIAS_TOKEN.get(token, (token,))

    padded = f" {texto_norm} "

    return any((f" {v} " in padded for v in variantes))


def _norm(texto: str) -> str:

    return " ".join(
        str(texto or "")
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
        .split()
    )
