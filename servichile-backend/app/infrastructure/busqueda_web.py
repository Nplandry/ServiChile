from __future__ import annotations

import json

import urllib.error

import urllib.request

from typing import Protocol

from app.domain.incidentes_publicos import SnippetBusqueda

from app.infrastructure.http_ssl import ssl_context

_UA = "ServiChile-Incidentes/1.0"

_TIMEOUT = 4.0


class BuscadorWeb(Protocol):

    def buscar(
        self, consulta: str, *, max_resultados: int = 5
    ) -> list[SnippetBusqueda]: ...


class NullBuscadorWeb:

    def buscar(
        self, consulta: str, *, max_resultados: int = 5
    ) -> list[SnippetBusqueda]:

        return []


class TavilyBuscador:

    def __init__(self, api_key: str) -> None:

        self.api_key = api_key.strip()

    def buscar(
        self, consulta: str, *, max_resultados: int = 5
    ) -> list[SnippetBusqueda]:

        body = json.dumps(
            {
                "api_key": self.api_key,
                "query": consulta,
                "search_depth": "basic",
                "max_results": max(1, min(10, max_resultados)),
                "include_answer": False,
            }
        ).encode()

        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=body,
            headers={"User-Agent": _UA, "Content-Type": "application/json"},
            method="POST",
        )

        data = _json_request(req)

        if not isinstance(data, dict):

            return []

        out: list[SnippetBusqueda] = []

        for item in data.get("results") or []:

            if not isinstance(item, dict):

                continue

            out.append(
                SnippetBusqueda(
                    titulo=str(item.get("title") or ""),
                    url=str(item.get("url") or ""),
                    texto=str(item.get("content") or item.get("snippet") or ""),
                    consulta=consulta,
                )
            )

            if len(out) >= max_resultados:

                break

        return out


def build_buscador(*, tavily_key: str | None = None) -> BuscadorWeb | None:

    if tavily_key and tavily_key.strip():

        return TavilyBuscador(tavily_key)

    return None


def _json_request(req: urllib.request.Request) -> object | None:

    try:

        with urllib.request.urlopen(
            req, timeout=_TIMEOUT, context=ssl_context()
        ) as resp:

            if getattr(resp, "status", 200) >= 400:

                return None

            raw = resp.read(1500000)

            if not raw:

                return None

            return json.loads(raw.decode("utf-8", errors="ignore"))

    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ):

        return None
