from app.domain.transparencia.docs_legales import (
    HallazgoDocLegal,
    ResultadoDocsLegales,
    clasificar_url_candidata,
    enriquecer_con_pagina,
    extraer_candidatos_desde_html,
    fusionar_sla_desde_otros,
    mismo_sitio,
    pagina_parece_util,
    score_doc_legal,
    senales_contenido,
    url_irrelevante,
)


def test_extraer_links_privacidad_y_terminos():

    html = """
    <footer>
      <a href="/politica-de-privacidad">Política de Privacidad</a>
      <a href="https://ejemplo.cl/terminos-y-condiciones">Términos y Condiciones</a>
      <a href="/trust">Trust Center</a>
    </footer>
    """

    c = extraer_candidatos_desde_html(html, "https://ejemplo.cl/")

    assert any("politica-de-privacidad" in u for u in c["politica-privacidad"])

    assert any("terminos-y-condiciones" in u for u in c["terminos"])

    assert any("trust" in u for u in c["sla"])


def test_score_doc_con_contenido():

    h = HallazgoDocLegal(
        enlace_en_home=True,
        url="https://x.cl/privacy",
        pagina_ok=True,
        contenido_ok=True,
        senales=4,
    )

    assert score_doc_legal(h, sitio_alcanzado=True) >= 90

    assert score_doc_legal(HallazgoDocLegal(), sitio_alcanzado=True) == 18

    assert score_doc_legal(HallazgoDocLegal(), sitio_alcanzado=False) == 15


def test_terminos_pagina_publica_es_100():

    h = HallazgoDocLegal(
        url="https://permisodecirculacion.cl/terminos-y-condiciones/",
        pagina_ok=True,
        contenido_ok=False,
        senales=1,
    )

    assert score_doc_legal(h, sitio_alcanzado=True, tipo="terminos") == 100

    assert score_doc_legal(h, sitio_alcanzado=True, tipo="politica-privacidad") == 62


def test_senales_y_enriquecer():

    html = "<h1>Política de Privacidad</h1><p>Datos personales y tratamiento de datos según Ley 21.719 y GDPR.</p>"

    assert senales_contenido(html, "politica-privacidad") >= 3

    h = enriquecer_con_pagina(
        HallazgoDocLegal(enlace_en_home=True),
        "https://x.cl/p",
        html,
        "politica-privacidad",
        desde_enlace=True,
    )

    assert h.pagina_ok and h.contenido_ok


def test_sla_desde_terminos():

    html = "<p>Nuestro SLA garantiza disponibilidad 99.9 y un DPA / data processing agreement con subprocesador.</p>"

    out = fusionar_sla_desde_otros(
        HallazgoDocLegal(), [("https://x.cl/terminos", html)]
    )

    assert out.pagina_ok and out.contenido_ok

    assert out.url.endswith("/terminos")


def test_resultado_scores_keys():

    r = ResultadoDocsLegales(sitio_alcanzado=True)

    assert set(r.scores()) == {"politica-privacidad", "terminos", "sla"}

    assert r.razones()["politica-privacidad"] == []

    assert r.razones()["terminos"] == []

    assert r.razones()["sla"] == []


def test_mismo_sitio_cdn_y_soft404():

    assert mismo_sitio("www.falabella.com", "https://assets.falabella.com/x.pdf")

    assert not pagina_parece_util(
        "https://www.falabella.com/falabella-cl/not-found", 200, "x" * 100
    )

    assert pagina_parece_util("https://assets.falabella.com/politica.pdf", 200, "")

    assert (
        clasificar_url_candidata(
            "https://www.paris.cl/informaciones-legales/politica-privacidad-de-datos/"
        )
        == "politica-privacidad"
    )

    assert clasificar_url_candidata("https://www.shopify.com/legal/dpa") == "sla"

    assert url_irrelevante("https://www.mercadolibre.cl/gz/account-verification?go=x")
