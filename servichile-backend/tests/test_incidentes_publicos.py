from app.domain.incidentes_publicos import (
    HallazgosIncidentes,
    SnippetBusqueda,
    armar_consultas,
    filtrar_heuristico,
    score_incidentes,
)

from app.infrastructure.incidentes_scanner import (
    FakeIncidentesScanner,
    LiveIncidentesScanner,
    NullIncidentesScanner,
)

from app.infrastructure.llm_filtro_incidentes import HeuristicoFiltroIncidentes


def test_score_sin_nombre_o_busqueda_cero():

    assert score_incidentes(HallazgosIncidentes()) == 0

    assert (
        score_incidentes(
            HallazgosIncidentes(nombre_consultable=True, busqueda_ok=False)
        )
        == 0
    )


def test_score_sin_confirmados_100():

    assert (
        score_incidentes(
            HallazgosIncidentes(
                nombre_consultable=True, busqueda_ok=True, confirmados=0
            )
        )
        == 100
    )


def test_score_con_confirmados():

    assert (
        score_incidentes(
            HallazgosIncidentes(
                nombre_consultable=True, busqueda_ok=True, confirmados=1
            )
        )
        == 75
    )

    assert (
        score_incidentes(
            HallazgosIncidentes(
                nombre_consultable=True, busqueda_ok=True, confirmados=2
            )
        )
        == 50
    )

    assert (
        score_incidentes(
            HallazgosIncidentes(
                nombre_consultable=True, busqueda_ok=True, confirmados=1, severos=1
            )
        )
        == 25
    )


def test_razones_breves_lista_titulos():

    from app.domain.incidentes_publicos import razones_breves

    h = HallazgosIncidentes(
        nombre_consultable=True, busqueda_ok=True, confirmados=1, severos=1
    )

    confirmados = [
        SnippetBusqueda(
            titulo="Estafa en Demo SpA",
            url="https://noticia.cl/x",
            texto="Caso de estafa vinculado a Demo SpA.",
        )
    ]

    raz = razones_breves(h, confirmados)

    assert raz == ["Severo: Estafa en Demo SpA"]

    assert razones_breves(
        HallazgosIncidentes(nombre_consultable=True, busqueda_ok=True), []
    ) == ["Sin hallazgos confirmados en fuentes públicas."]


def test_armar_consultas_incluye_nombre_y_keyword():

    qs = armar_consultas("Acme Logística SpA", max_queries=1)

    assert len(qs) == 1

    assert "Acme Logística SpA" in qs[0]

    assert "fraude" in qs[0]

    assert " OR " in qs[0]


def test_filtrar_heuristico_rechaza_homonimo():

    nombre = "Transportes Andes Sur"

    snippets = [
        SnippetBusqueda(
            titulo="Estafa en Transportes Andes Sur deja clientes sin carga",
            url="https://noticia.cl/1",
            texto="La empresa Transportes Andes Sur enfrenta demanda por fraude.",
        ),
        SnippetBusqueda(
            titulo="Fraude en otra compañía homónima",
            url="https://noticia.cl/2",
            texto="Un caso de estafa no relacionado con la firma consultada.",
        ),
    ]

    ok = filtrar_heuristico(nombre, snippets)

    assert len(ok) == 1

    assert "Andes Sur" in ok[0].titulo


def test_filtrar_rechaza_basura_y_energy_sector():

    nombre = "Energy Gym"

    snippets = [
        SnippetBusqueda(
            titulo='"Esto es una estafa": Conadecus apunta contra Energy tras cierre de gimnasios',
            url="https://chocale.cl/estafa-energy",
            texto="Conadecus denuncia estafa de la cadena Energy Gym / gimnasios Energy.",
        ),
        SnippetBusqueda(
            titulo="TikTok - Make Your Day",
            url="https://www.tiktok.com/@x/video/1",
            texto="Energy Gym estafa clientes en Chile.",
        ),
        SnippetBusqueda(
            titulo="Chile: Ransomware hits critical infrastructure — CiberLATAM",
            url="https://ciberlatam.com/ransomware",
            texto="Ransomware against the energy sector in Chile.",
        ),
        SnippetBusqueda(
            titulo="Cyber Threats Against Energy Sector Surge",
            url="https://resecurity.com/energy",
            texto="Threats mount against the global energy sector.",
        ),
    ]

    ok = filtrar_heuristico(nombre, snippets)

    assert len(ok) == 1

    assert "Conadecus" in ok[0].titulo


def test_null_y_fake():

    assert NullIncidentesScanner().score_para_nombre("Acme") == 0

    assert FakeIncidentesScanner().score_para_nombre("") == 0

    assert FakeIncidentesScanner().score_para_nombre("Acme SpA") == 100


class _BuscadorFijo:

    def __init__(self, hits: list[SnippetBusqueda]) -> None:

        self.hits = hits

    def buscar(
        self, consulta: str, *, max_resultados: int = 5
    ) -> list[SnippetBusqueda]:

        return self.hits[:max_resultados]


def test_live_scanner_sin_hits_da_100():

    scanner = LiveIncidentesScanner(
        _BuscadorFijo([]), HeuristicoFiltroIncidentes(), max_queries=2
    )

    assert scanner.score_para_nombre("Demo SpA") == 100


def test_live_scanner_con_hit_confirmado():

    hits = [
        SnippetBusqueda(
            titulo="Clausura de Demo SpA por infracción",
            url="https://noticia.cl/x",
            texto="Autoridad ordenó clausura de Demo SpA tras fiscalización.",
        )
    ]

    scanner = LiveIncidentesScanner(
        _BuscadorFijo(hits), HeuristicoFiltroIncidentes(), max_queries=1
    )

    assert scanner.score_para_nombre("Demo SpA") == 75
