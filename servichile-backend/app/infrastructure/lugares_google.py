from __future__ import annotations

import json

import urllib.error

import urllib.parse

import urllib.request

from app.domain.puertos import NuloPlaces, ProveedorPlaces, ResultadoPlaces

from app.infrastructure.contexto_https import ssl_context

_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

_UA = "ServiChile-Places/1.0"

_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.rating,places.userRatingCount,places.websiteUri"
)


NullPlacesGoogle = NuloPlaces


class FakePlacesGoogle:

    def buscar_reputacion(
        self,
        *,
        nombre: str | None,
        direccion: str | None = None,
        sitio_web: str | None = None,
    ) -> ResultadoPlaces:

        if not (nombre or "").strip():

            return ResultadoPlaces(encontrado=False)

        return ResultadoPlaces(
            encontrado=True,
            rating=4.5,
            reviews_count=120,
            place_id="fake-place",
            nombre=(nombre or "").strip(),
        )


def _host(url: str | None) -> str:

    if not url or not str(url).strip():

        return ""

    raw = str(url).strip()

    if "://" not in raw:

        raw = "https://" + raw

    try:

        host = (urllib.parse.urlparse(raw).hostname or "").lower()

    except ValueError:

        return ""

    return host.removeprefix("www.")


def _texto_consulta(nombre: str | None, direccion: str | None) -> str:

    partes = [
        p.strip() for p in (nombre or "", direccion or "") if p and str(p).strip()
    ]

    if not partes:

        return ""

    q = " ".join(partes)

    if "chile" not in q.lower():

        q = f"{q} Chile"

    return q


def elegir_lugar(places: list[dict], sitio_web: str | None) -> dict | None:

    if not places:

        return None

    target = _host(sitio_web)

    if target:

        for p in places:

            if not isinstance(p, dict):

                continue

            if _host(p.get("websiteUri")) == target:

                return p

    for p in places:

        if isinstance(p, dict):

            return p

    return None


def resultado_desde_lugar(lugar: dict | None) -> ResultadoPlaces:

    if not isinstance(lugar, dict):

        return ResultadoPlaces(encontrado=False)

    rating_raw = lugar.get("rating")

    try:

        rating = float(rating_raw) if rating_raw is not None else None

    except (TypeError, ValueError):

        rating = None

    count_raw = lugar.get("userRatingCount")

    try:

        reviews = max(0, int(count_raw or 0))

    except (TypeError, ValueError):

        reviews = 0

    display = lugar.get("displayName")

    nombre = None

    if isinstance(display, dict):

        nombre = str(display.get("text") or "").strip() or None

    place_id = str(lugar.get("id") or "").strip() or None

    if rating is None and reviews == 0 and not place_id:

        return ResultadoPlaces(encontrado=False)

    return ResultadoPlaces(
        encontrado=True,
        rating=rating,
        reviews_count=reviews,
        place_id=place_id,
        nombre=nombre,
    )


class LivePlacesGoogle:

    def __init__(self, api_key: str, timeout: float = 3.5) -> None:

        self.api_key = api_key.strip()

        self.timeout = timeout

    def buscar_reputacion(
        self,
        *,
        nombre: str | None,
        direccion: str | None = None,
        sitio_web: str | None = None,
    ) -> ResultadoPlaces:

        if not self.api_key:

            return ResultadoPlaces(encontrado=False)

        query = _texto_consulta(nombre, direccion)

        if not query:

            return ResultadoPlaces(encontrado=False)

        body = json.dumps(
            {
                "textQuery": query,
                "languageCode": "es",
                "regionCode": "CL",
                "maxResultCount": 3,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            _SEARCH_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": _UA,
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": _FIELD_MASK,
            },
            method="POST",
        )

        try:

            with urllib.request.urlopen(
                req, timeout=self.timeout, context=ssl_context()
            ) as resp:

                raw = resp.read(500000)

        except urllib.error.HTTPError:

            return ResultadoPlaces(encontrado=False)

        except (urllib.error.URLError, OSError, TimeoutError):

            return ResultadoPlaces(encontrado=False)

        try:

            payload = json.loads(raw.decode("utf-8", errors="ignore")) if raw else {}

        except json.JSONDecodeError:

            return ResultadoPlaces(encontrado=False)

        places = payload.get("places") if isinstance(payload, dict) else None

        if not isinstance(places, list):

            return ResultadoPlaces(encontrado=False)

        return resultado_desde_lugar(elegir_lugar(places, sitio_web))


def build_places_google(api_key: str | None, *, fake: bool = False) -> ProveedorPlaces:

    if fake:

        return FakePlacesGoogle()

    if not api_key or not str(api_key).strip():

        return NullPlacesGoogle()

    return LivePlacesGoogle(str(api_key).strip())
