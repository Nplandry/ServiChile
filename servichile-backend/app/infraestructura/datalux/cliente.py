from __future__ import annotations

import gzip
import html as html_lib
import json
import re
import time
from http.client import HTTPSConnection
from threading import Lock
from urllib.parse import quote_plus, urlparse

from app.dominio.puertos import NuloDatalux, ProveedorDatalux
from app.dominio.transparencia.datalux import ActividadEconomica, FichaDatalux
from app.infraestructura.contexto_https import ssl_context

HOST = "datalux.cl"
BUSCADOR = "/buscador/"
UA = "Mozilla/5.0 (compatible; ServiChile-DataLux/1.2)"
_TIMEOUT = 3.5
_CACHE_TTL = 6 * 3600
_NEG_TTL = 15 * 60
_CACHE_MAX = 512
_BODY_MAX = 160_000

_RE_CARD = re.compile(r'<article class="dtx-search-card">(.*?)</article>', re.I | re.S)
_RE_LINK = re.compile(r'<a[^>]*class="[^"]*dtx-result-link[^"]*"[^>]*>', re.I)
_RE_ATTR = re.compile(r'([\w:-]+)="([^"]*)"', re.I)
_RE_FIELD = re.compile(
    r'<(?:div|span)[^>]*class="[^"]*(?:dtx-field|dtx-estado)[^"]*"[^>]*>'
    r"(.*?)</(?:div|span)>",
    re.I | re.S,
)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_WS = re.compile(r"\s+")
_RE_STRONG = re.compile(r"<strong[^>]*>\s*([^:<]*)\s*:?\s*</strong>\s*(.*)", re.I | re.S)
_RE_HELP = re.compile(r'<span[^>]*class="[^"]*dtx-help', re.I)
_RE_JSON_LD = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.I | re.S
)
_RE_TITLE = re.compile(
    r'<h1[^>]*class="[^"]*dtx-titulo-empresa[^"]*"[^>]*>(.*?)</h1>', re.I | re.S
)
_RE_SLUG = re.compile(r"^\s*(\d{7,8}-[\dkK]-[\w-]+)\s*$", re.I)
_RE_URL = re.compile(r"https?://(?:www\.)?datalux\.cl(/empresa/[\w.-]+/?)", re.I)
_RE_RUT_Q = re.compile(r"^\s*(\d{1,2}\.?\d{3}\.?\d{3})\s*-?\s*([\dkK])\s*$")
_RE_RESUMEN = re.compile(
    r'<(?:p|div)[^>]*class="[^"]*dtx-(?:resumen|descripcion|intro)[^"]*"[^>]*>'
    r"(.*?)</(?:p|div)>",
    re.I | re.S,
)
_RE_TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.I | re.S)
_RE_ACT_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
_RE_ACT_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
_RE_ANIO = re.compile(r"\b(?:19|20)\d{2}\b")
_HEAD_ACT = frozenset({"código", "codigo", "giro", "#", "actividad", "glosa"})

_SSL = ssl_context()
_CACHE: dict[str, tuple[float, FichaDatalux | None]] = {}
_CACHE_LOCK = Lock()
_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-CL,es;q=0.9",
    "Accept-Encoding": "gzip",
    "Connection": "keep-alive",
}


def _limpiar(valor: str | None) -> str:
    if not valor:
        return ""
    return _RE_WS.sub(" ", _RE_TAG.sub(" ", html_lib.unescape(valor))).strip(" :\n\t")


def _attrs(tag: str) -> dict[str, str]:
    return {k.lower(): html_lib.unescape(v) for k, v in _RE_ATTR.findall(tag)}


def _mapa_campos(html: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _RE_FIELD.finditer(html):
        parsed = _RE_STRONG.search(m.group(1))
        if not parsed:
            continue
        label = _limpiar(parsed.group(1)).lower()
        if not label or label in out:
            continue
        valor = _RE_HELP.split(parsed.group(2), maxsplit=1)[0]
        out[label] = _limpiar(valor)
    return out


def _campo(campos: dict[str, str], *labels: str) -> str:
    for label in labels:
        v = campos.get(label.lower())
        if v:
            return v
        for k, val in campos.items():
            if label.lower() in k:
                return val
    return ""


def _json_ld(html: str) -> dict:
    for m in _RE_JSON_LD.finditer(html):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Organization":
            return data
    return {}


def _primer_hit(html: str) -> dict[str, str] | None:
    card = _RE_CARD.search(html)
    if not card:
        return None
    link = _RE_LINK.search(card.group(1))
    if not link:
        return None
    a = _attrs(link.group(0))
    href = a.get("href", "")
    path = urlparse(href).path if href.startswith("http") else href
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith("/"):
        path += "/"
    return {
        "nombre": a.get("data-company-name", ""),
        "rut": a.get("data-rut-empresa", ""),
        "path": path,
        "comuna": a.get("data-comuna-empresa", ""),
    }


def _actividades(html: str) -> tuple[ActividadEconomica, ...]:
    out: list[ActividadEconomica] = []
    tablas = _RE_TABLE.findall(html) or [html]
    for tabla in tablas:
        for row in _RE_ACT_ROW.finditer(tabla):
            cells = [_limpiar(c) for c in _RE_ACT_CELL.findall(row.group(1))]
            if len(cells) < 2:
                continue
            if cells[0].lower() in _HEAD_ACT:
                continue
            nombre = cells[1] if len(cells) > 1 else cells[0]
            if len(nombre) < 3:
                continue
            fecha = next(
                (c for c in cells if _RE_ANIO.search(c) or "/" in c or "-" in c),
                "",
            )
            out.append(ActividadEconomica(nombre=nombre, fecha_inicio=fecha))
            if len(out) >= 8:
                return tuple(out)
    return tuple(out)


def _parse_ficha(html: str) -> FichaDatalux:
    org = _json_ld(html)
    address = org.get("address") if isinstance(org.get("address"), dict) else {}
    ident = org.get("identifier") if isinstance(org.get("identifier"), dict) else {}
    campos = _mapa_campos(html)
    titulo = _RE_TITLE.search(html)
    nombre = _limpiar(titulo.group(1) if titulo else "") or str(org.get("name") or "")
    rut = _campo(campos, "rut") or str(ident.get("value") or "")
    direccion = str(address.get("streetAddress") or "") or _campo(campos, "dirección", "direccion")
    comuna = str(address.get("addressLocality") or "") or _campo(campos, "comuna")
    estado = _campo(campos, "estado")
    resumen_m = _RE_RESUMEN.search(html)
    resumen = _limpiar(resumen_m.group(1) if resumen_m else "") or _campo(campos, "resumen")
    anio = _campo(
        campos,
        "año de inicio",
        "año inicio",
        "anio de inicio",
        "inicio de actividades",
    )
    if not anio:
        m = _RE_ANIO.search(_campo(campos, "fecha de inicio") or "")
        anio = m.group(0) if m else ""
    return FichaDatalux(
        nombre=nombre,
        rut=rut,
        estado=estado,
        direccion=_limpiar(direccion),
        comuna=_limpiar(comuna),
        resumen=resumen,
        anio_inicio=_limpiar(anio),
        actividades_economicas=_actividades(html),
    )


def _path_directo(consulta: str) -> str | None:
    m = _RE_URL.search(consulta)
    if m:
        path = m.group(1)
        return path if path.endswith("/") else path + "/"
    m = _RE_SLUG.match(consulta)
    if m:
        return f"/empresa/{m.group(1).lower()}/"
    return None


def _cache_key(consulta: str) -> str:
    rut = _RE_RUT_Q.match(consulta)
    if rut:
        return f"rut:{rut.group(1).replace('.', '')}-{rut.group(2).upper()}"
    return f"q:{_RE_WS.sub(' ', consulta.strip().lower())}"


def _cache_get(key: str) -> tuple[bool, FichaDatalux | None]:
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if not item:
            return False, None
        ts, ficha = item
        ttl = _CACHE_TTL if ficha is not None else _NEG_TTL
        if time.time() - ts > ttl:
            _CACHE.pop(key, None)
            return False, None
        return True, ficha


def _cache_put(key: str, ficha: FichaDatalux | None) -> None:
    now = time.time()
    with _CACHE_LOCK:
        if len(_CACHE) >= _CACHE_MAX:
            for k, (ts, v) in list(_CACHE.items()):
                ttl = _CACHE_TTL if v is not None else _NEG_TTL
                if now - ts > ttl:
                    _CACHE.pop(k, None)
            while len(_CACHE) >= _CACHE_MAX:
                _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = (now, ficha)


def _con_hint(ficha: FichaDatalux, hint: dict[str, str] | None) -> FichaDatalux:
    if not hint:
        return ficha
    return FichaDatalux(
        nombre=ficha.nombre or hint.get("nombre", ""),
        rut=ficha.rut or hint.get("rut", ""),
        estado=ficha.estado,
        direccion=ficha.direccion,
        comuna=ficha.comuna or hint.get("comuna", ""),
        resumen=ficha.resumen,
        anio_inicio=ficha.anio_inicio,
        actividades_economicas=ficha.actividades_economicas,
    )


class DataluxCliente:
    def __init__(self, timeout: float = _TIMEOUT) -> None:
        self.timeout = timeout
        self._conn: HTTPSConnection | None = None

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def _get(self, path: str) -> str:
        last: Exception | None = None
        for _ in range(2):
            if self._conn is None:
                self._conn = HTTPSConnection(HOST, context=_SSL, timeout=self.timeout)
            try:
                self._conn.request("GET", path, headers=_HEADERS)
                resp = self._conn.getresponse()
                raw = resp.read(_BODY_MAX)
                if resp.getheader("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                if resp.status >= 400:
                    raise LookupError(f"HTTP {resp.status}")
                return raw.decode("utf-8", "ignore")
            except Exception as exc:
                last = exc
                self.close()
        assert last is not None
        raise last

    def _buscar(self, q: str) -> dict[str, str] | None:
        return _primer_hit(self._get(f"{BUSCADOR}?q={quote_plus(q)}"))

    def consultar(self, consulta: str | None) -> FichaDatalux | None:
        q = (consulta or "").strip()
        if not q:
            return None
        key = _cache_key(q)
        hit_cache, cached = _cache_get(key)
        if hit_cache:
            return cached
        try:
            path = _path_directo(q)
            hint: dict[str, str] | None = None
            if path is None:
                hint = self._buscar(q)
                if not hint:
                    _cache_put(key, None)
                    return None
                path = hint["path"]
            html = self._get(path)
            if "dtx-titulo-empresa" not in html and "application/ld+json" not in html:
                hint = self._buscar(q)
                if not hint:
                    _cache_put(key, None)
                    return None
                html = self._get(hint["path"])
            ficha = _con_hint(_parse_ficha(html), hint)
            if not (ficha.nombre or ficha.rut):
                _cache_put(key, None)
                return None
            _cache_put(key, ficha)
            return ficha
        except Exception:
            return None
        finally:
            self.close()


_CLIENTE: DataluxCliente | None = None
_CLIENTE_LOCK = Lock()


def build_datalux(*, enabled: bool = True, timeout: float = _TIMEOUT) -> ProveedorDatalux:
    if not enabled:
        return NuloDatalux()
    global _CLIENTE
    with _CLIENTE_LOCK:
        if _CLIENTE is None or _CLIENTE.timeout != timeout:
            _CLIENTE = DataluxCliente(timeout=timeout)
        return _CLIENTE
