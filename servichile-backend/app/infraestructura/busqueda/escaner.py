from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.dominio.puertos import NuloIncidentes, ProveedorIncidentes, ResultadoIncidentes

from app.dominio.transparencia.incidentes import (
    HallazgosIncidentes,
    SnippetBusqueda,
    armar_consultas,
    hallazgos_desde_confirmados,
    razones_breves,
    score_incidentes,
)

from app.infraestructura.busqueda.web import BuscadorWeb, build_buscador

from app.infraestructura.busqueda.filtro import (
    FiltroIncidentes,
    build_filtro_incidentes,
)


NullIncidentesScanner = NuloIncidentes


class MuestraIncidentesScanner:

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


class ProduccionIncidentesScanner:

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
) -> ProveedorIncidentes:

    if mode == "muestra":

        return MuestraIncidentesScanner()

    if mode == "apagado":

        return NullIncidentesScanner()

    buscador = build_buscador(tavily_key=tavily_key)

    if buscador is None:

        return NullIncidentesScanner()

    return ProduccionIncidentesScanner(buscador, build_filtro_incidentes())
