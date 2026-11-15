from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from dataclasses import dataclass

from typing import Protocol

from app.domain.incidentes_publicos import (
    HallazgosIncidentes,
    SnippetBusqueda,
    armar_consultas,
    hallazgos_desde_confirmados,
    razones_breves,
    score_incidentes,
)

from app.infrastructure.busqueda_web import BuscadorWeb, build_buscador

from app.infrastructure.llm_filtro_incidentes import (
    FiltroIncidentes,
    build_filtro_incidentes,
)


@dataclass(frozen=True)
class ResultadoIncidentes:

    score: int

    razones: tuple[str, ...] = ()


class IncidentesScanner(Protocol):

    def evaluar_nombre(self, nombre: str | None) -> ResultadoIncidentes: ...

    def score_para_nombre(self, nombre: str | None) -> int: ...


class NullIncidentesScanner:

    def evaluar_nombre(self, nombre: str | None) -> ResultadoIncidentes:

        return ResultadoIncidentes(0, ("Módulo de incidentes no disponible.",))

    def score_para_nombre(self, nombre: str | None) -> int:

        return self.evaluar_nombre(nombre).score


class FakeIncidentesScanner:

    def evaluar_nombre(self, nombre: str | None) -> ResultadoIncidentes:

        limpio = " ".join(str(nombre or "").split()).strip()

        if len(limpio) < 2:

            return ResultadoIncidentes(0, ("Sin nombre consultable.",))

        h = HallazgosIncidentes(
            nombre_consultable=True,
            busqueda_ok=True,
            snippets_crudos=0,
            confirmados=0,
            severos=0,
        )

        return ResultadoIncidentes(score_incidentes(h), tuple(razones_breves(h, [])))

    def score_para_nombre(self, nombre: str | None) -> int:

        return self.evaluar_nombre(nombre).score


class LiveIncidentesScanner:

    def __init__(
        self,
        buscador: BuscadorWeb,
        filtro: FiltroIncidentes,
        *,
        max_queries: int = 1,
        max_por_query: int = 3,
    ) -> None:

        self.buscador = buscador

        self.filtro = filtro

        self.max_queries = max_queries

        self.max_por_query = max_por_query

    def evaluar_nombre(self, nombre: str | None) -> ResultadoIncidentes:

        limpio = " ".join(str(nombre or "").split()).strip()

        if len(limpio) < 2:

            h = HallazgosIncidentes()

            return ResultadoIncidentes(
                score_incidentes(h), tuple(razones_breves(h, []))
            )

        consultas = armar_consultas(limpio, max_queries=self.max_queries)

        if not consultas:

            h = HallazgosIncidentes()

            return ResultadoIncidentes(
                score_incidentes(h), tuple(razones_breves(h, []))
            )

        crudos: list[SnippetBusqueda] = []

        busqueda_ok = False

        if len(consultas) == 1:

            try:

                hits = self.buscador.buscar(
                    consultas[0], max_resultados=self.max_por_query
                )

                busqueda_ok = True

                crudos.extend(hits)

            except Exception:

                pass

        else:

            with ThreadPoolExecutor(max_workers=min(4, len(consultas))) as pool:

                futs = {
                    pool.submit(
                        self.buscador.buscar, q, max_resultados=self.max_por_query
                    ): q
                    for q in consultas
                }

                for fut in as_completed(futs):

                    try:

                        hits = fut.result()

                    except Exception:

                        continue

                    busqueda_ok = True

                    crudos.extend(hits)

        confirmados = self.filtro.filtrar(limpio, crudos) if busqueda_ok else []

        h = hallazgos_desde_confirmados(
            nombre_consultable=True,
            busqueda_ok=busqueda_ok,
            snippets_crudos=len(crudos),
            confirmados=confirmados,
        )

        return ResultadoIncidentes(
            score_incidentes(h), tuple(razones_breves(h, confirmados))
        )

    def score_para_nombre(self, nombre: str | None) -> int:

        return self.evaluar_nombre(nombre).score


def build_incidentes_scanner(
    *, mode: str, tavily_key: str | None = None
) -> IncidentesScanner:

    if mode == "fake":

        return FakeIncidentesScanner()

    if mode == "off":

        return NullIncidentesScanner()

    buscador = build_buscador(tavily_key=tavily_key)

    if buscador is None:

        return NullIncidentesScanner()

    return LiveIncidentesScanner(buscador, build_filtro_incidentes())
