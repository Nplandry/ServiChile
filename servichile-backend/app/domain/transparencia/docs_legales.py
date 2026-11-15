from __future__ import annotations

import re

from dataclasses import dataclass, field

from urllib.parse import urljoin, urlparse

from app.domain.transparencia.indicadores import DefinicionObservable, PESO_CONTRACTUAL

TIPOS = ("politica-privacidad", "terminos", "sla")

OBSERVABLE_PRIVACIDAD = DefinicionObservable(
    id="politica-privacidad",
    etiqueta="Política de Privacidad accesible e información acerca de la Ley 21.719",
    detalle="",
    grupo="contractual",
    peso=PESO_CONTRACTUAL,
)

OBSERVABLE_TERMINOS = DefinicionObservable(
    id="terminos",
    etiqueta="Términos y Condiciones públicos de la oferta comercial",
    detalle="",
    grupo="contractual",
    peso=PESO_CONTRACTUAL,
)

OBSERVABLE_SLA = DefinicionObservable(
    id="sla",
    etiqueta="Cláusulas de servicio, SLA y DPA",
    detalle="",
    grupo="contractual",
    peso=PESO_CONTRACTUAL,
)


RUTAS: dict[str, tuple[str, ...]] = {
    "politica-privacidad": (
        "/privacy",
        "/privacidad",
        "/politica-de-privacidad",
        "/informaciones-legales/politica-privacidad-de-datos",
        "/privacy-policy",
    ),
    "terminos": (
        "/terminos-y-condiciones",
        "/terms",
        "/terminos",
        "/informaciones-legales/terminos-y-condiciones",
        "/terms-of-service",
    ),
}

_KW: dict[str, tuple[str, ...]] = {
    "politica-privacidad": (
        "política de privacidad",
        "politica de privacidad",
        "privacy policy",
        "datos personales",
        "personal data",
        "tratamiento de datos",
        "ley 21.719",
        "gdpr",
        "rgpd",
    ),
    "terminos": (
        "términos y condiciones",
        "terminos y condiciones",
        "terms of service",
        "terms and conditions",
        "condiciones de uso",
        "jurisdicción",
        "jurisdiccion",
        "responsabilidad",
    ),
    "sla": (
        "sla",
        "service level",
        "nivel de servicio",
        "dpa",
        "data processing agreement",
        "acuerdo de tratamiento",
        "99.9",
        "uptime",
    ),
}

_RE_A = re.compile(
    r'<a\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S
)

_RE_TAGS = re.compile(r"<[^>]+>")

_RE_WS = re.compile(r"\s+")

_IRRELEVANTE = (
    "/login",
    "/signin",
    "identification",
    "account-verification",
    "challenge_id",
    "/gz/account",
    "redirect_url=",
    "/cart",
    "/checkout",
    "/blog/",
    "/news/",
    "/noticias/",
    "/press/",
)


@dataclass
class HallazgoDocLegal:

    enlace_en_home: bool = False

    url: str | None = None

    pagina_ok: bool = False

    contenido_ok: bool = False

    senales: int = 0


@dataclass
class ResultadoDocsLegales:

    privacidad: HallazgoDocLegal = field(default_factory=HallazgoDocLegal)

    terminos: HallazgoDocLegal = field(default_factory=HallazgoDocLegal)

    sla: HallazgoDocLegal = field(default_factory=HallazgoDocLegal)

    sitio_alcanzado: bool = False

    def scores(self) -> dict[str, int]:

        return {
            "politica-privacidad": score_doc_legal(
                self.privacidad,
                sitio_alcanzado=self.sitio_alcanzado,
                tipo="politica-privacidad",
            ),
            "terminos": score_doc_legal(
                self.terminos, sitio_alcanzado=self.sitio_alcanzado, tipo="terminos"
            ),
            "sla": score_doc_legal(
                self.sla,
                sitio_alcanzado=self.sitio_alcanzado,
                tipo="sla",
                base_sin_doc=22,
            ),
        }

    def razones(self) -> dict[str, list[str]]:

        return {
            "politica-privacidad": razones_doc(
                "politica-privacidad", self.privacidad, self.sitio_alcanzado
            ),
            "terminos": razones_doc("terminos", self.terminos, self.sitio_alcanzado),
            "sla": razones_doc("sla", self.sla, self.sitio_alcanzado),
        }


def score_doc_legal(
    h: HallazgoDocLegal,
    *,
    sitio_alcanzado: bool,
    base_sin_doc: int = 18,
    tipo: str | None = None,
) -> int:

    if not sitio_alcanzado:

        return 15

    if tipo == "terminos":

        if h.pagina_ok:

            return 100

        if h.enlace_en_home:

            return 70

        return base_sin_doc

    if h.pagina_ok and h.contenido_ok:

        return int(max(0, min(100, round(78 + min(20, 4 * max(1, h.senales))))))

    if h.pagina_ok:

        return 62

    if h.enlace_en_home:

        return 42

    return base_sin_doc


def razones_doc(tipo: str, h: HallazgoDocLegal, sitio_alcanzado: bool) -> list[str]:

    if not sitio_alcanzado or not (h.url or h.enlace_en_home or h.pagina_ok):

        return []

    out: list[str] = []

    if h.url:

        out.append(h.url)

    elif h.enlace_en_home:

        out.append("Enlace en home (página no validada)")

    if h.pagina_ok and h.contenido_ok:

        out.append(f"Señales de contenido: {h.senales}")

    elif h.pagina_ok:

        out.append(
            "TyC públicos accesibles"
            if tipo == "terminos"
            else "Página responde, contenido débil o genérico"
        )

    return out


def apex(host: str) -> str:

    h = host.lower().strip(".")

    if h.startswith("www."):

        h = h[4:]

    parts = h.split(".")

    return ".".join(parts[-2:]) if len(parts) >= 2 else h


def mismo_sitio(base_host: str, url: str) -> bool:

    try:

        h = (urlparse(url).hostname or "").lower()

    except ValueError:

        return False

    if not h or apex(h) != apex(base_host):

        return False

    sub = h[4:] if h.startswith("www.") else h

    primer = sub.split(".", 1)[0]

    if primer in (
        "apps",
        "app",
        "community",
        "help",
        "support",
        "partners",
        "store",
        "stores",
    ):

        return False

    return True


def url_irrelevante(url: str) -> bool:

    u = (url or "").lower()

    return any(x in u for x in _IRRELEVANTE)


def pagina_parece_util(url: str, code: int, body: str) -> bool:

    if not (200 <= int(code) < 400):

        return False

    u = (url or "").lower()

    if any(x in u for x in ("/not-found", "/404", "error-404", "pagenotfound")):

        return False

    if u.endswith(".pdf"):

        return True

    texto = (body or "").strip()

    if len(texto) < 80:

        return False

    low = texto.lower()

    if ("página no encontrada" in low or "page not found" in low) and len(
        texto
    ) < 12000:

        return False

    return True


def clasificar_url_candidata(url: str, titulo: str = "") -> str | None:

    if url_irrelevante(url):

        return None

    path = (urlparse(url).path or "").lower().replace("-", " ").replace("_", " ")

    if any(
        x in path
        for x in (
            "privacidad",
            "privacy",
            "proteccion de datos",
            "protección de datos",
            "datos personales",
        )
    ):

        return "politica-privacidad"

    if any(
        x in path
        for x in (
            "terminos",
            "términos",
            "terms",
            "condiciones de",
            "condiciones y",
            "/tyc",
            "/tos",
        )
    ):

        return "terminos"

    if any(
        x in path
        for x in (
            "/sla",
            " sla",
            "/dpa",
            " dpa",
            "data processing",
            "tratamiento datos",
            "trust",
            "service level",
            "nivel de servicio",
        )
    ):

        return "sla"

    tit = (titulo or "").lower()

    if any(
        x in tit
        for x in (
            "política de privacidad",
            "politica de privacidad",
            "privacy policy",
            "protección de datos",
        )
    ):

        return "politica-privacidad"

    if any(
        x in tit
        for x in (
            "términos y condiciones",
            "terminos y condiciones",
            "terms of service",
            "terms and conditions",
        )
    ):

        return "terminos"

    if any(
        x in tit
        for x in (
            "data processing agreement",
            "trust center",
            "service level",
            "acuerdo de tratamiento",
        )
    ):

        return "sla"

    return None


def senales_contenido(html: str, tipo: str) -> int:

    if not html:

        return 0

    texto = _RE_WS.sub(" ", _RE_TAGS.sub(" ", html)).lower()

    return sum(1 for k in _KW.get(tipo, ()) if k in texto)


def enriquecer_con_pagina(
    h: HallazgoDocLegal, url: str, html: str, tipo: str, *, desde_enlace: bool
) -> HallazgoDocLegal:

    if url_irrelevante(url):

        return h

    if url.lower().endswith(".pdf"):

        n = senales_contenido(
            url.replace("-", " ").replace("_", " ").replace("%20", " ").lower(), tipo
        )

        if n < 1:

            return h

        n = max(3, n + 2)

        return HallazgoDocLegal(
            enlace_en_home=h.enlace_en_home or desde_enlace,
            url=url,
            pagina_ok=True,
            contenido_ok=True,
            senales=max(h.senales, n),
        )

    n = senales_contenido(html, tipo)

    return HallazgoDocLegal(
        enlace_en_home=h.enlace_en_home or desde_enlace,
        url=url,
        pagina_ok=True,
        contenido_ok=n >= 2,
        senales=max(h.senales, n),
    )


def mejor_hallazgo(prev: HallazgoDocLegal, cand: HallazgoDocLegal) -> HallazgoDocLegal:

    if not cand.pagina_ok:

        return prev

    if (
        (cand.contenido_ok and not prev.contenido_ok)
        or cand.senales > prev.senales
        or not prev.pagina_ok
    ):

        return cand

    return prev


def extraer_candidatos_desde_html(html: str, base_url: str) -> dict[str, list[str]]:

    out: dict[str, list[str]] = {t: [] for t in TIPOS}

    if not html:

        return out

    host = urlparse(base_url).hostname or ""

    for m in _RE_A.finditer(html):

        href, inner = m.group(1), m.group(2)

        href = (href or "").strip()

        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):

            continue

        try:

            url = urljoin(base_url, href).split("#", 1)[0]

        except ValueError:

            continue

        if urlparse(url).scheme not in ("http", "https") or not mismo_sitio(host, url):

            continue

        texto = _RE_WS.sub(" ", _RE_TAGS.sub(" ", inner or "")).strip()

        tipo = clasificar_url_candidata(url, texto) or clasificar_url_candidata(
            href, texto
        )

        if tipo:

            out[tipo].append(url)

    for t, urls in out.items():

        seen: set[str] = set()

        dedup: list[str] = []

        for u in urls:

            key = u.rstrip("/").lower()

            if key in seen:

                continue

            seen.add(key)

            dedup.append(u)

        out[t] = dedup

    return out


def rutas_rapidas(
    base_url: str, faltan: list[str], *, por_tipo: int = 2
) -> list[tuple[str, str]]:

    root = base_url.rstrip("/") + "/"

    out: list[tuple[str, str]] = []

    for tipo in (t for t in ("politica-privacidad", "terminos") if t in faltan):

        for path in RUTAS.get(tipo, ())[:por_tipo]:

            out.append((tipo, urljoin(root, path.lstrip("/"))))

    return out


def consulta_busqueda_unica(apex_host: str) -> str:

    a = apex(apex_host)

    return (
        f'site:{a} ("política de privacidad" OR "privacy policy" OR '
        f'"términos y condiciones" OR "terms and conditions" OR DPA OR "trust center")'
    )


def fusionar_sla_desde_otros(
    sla: HallazgoDocLegal, htmls: list[tuple[str, str]]
) -> HallazgoDocLegal:

    if sla.pagina_ok and sla.contenido_ok and not url_irrelevante(sla.url or ""):

        return sla

    mejor = HallazgoDocLegal() if url_irrelevante(sla.url or "") else sla

    for url, html in htmls:

        if url_irrelevante(url):

            continue

        n = senales_contenido(html, "sla")

        if n < 3:

            continue

        path = (urlparse(url).path or "").lower()

        if not any(
            x in path
            for x in (
                "term",
                "condic",
                "priva",
                "legal",
                "sla",
                "dpa",
                "trust",
                "policy",
            )
        ):

            continue

        mejor = mejor_hallazgo(
            mejor,
            HallazgoDocLegal(
                enlace_en_home=True,
                url=url,
                pagina_ok=True,
                contenido_ok=True,
                senales=n,
            ),
        )

    return mejor
