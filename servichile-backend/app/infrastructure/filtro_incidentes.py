from __future__ import annotations

from typing import Protocol

from app.domain.transparencia.incidentes import SnippetBusqueda, filtrar_heuristico


class FiltroIncidentes(Protocol):

    def filtrar(
        self, nombre: str, snippets: list[SnippetBusqueda]
    ) -> list[SnippetBusqueda]: ...


class HeuristicoFiltroIncidentes:

    def filtrar(
        self, nombre: str, snippets: list[SnippetBusqueda]
    ) -> list[SnippetBusqueda]:

        return filtrar_heuristico(nombre, snippets)


def build_filtro_incidentes() -> FiltroIncidentes:

    return HeuristicoFiltroIncidentes()
