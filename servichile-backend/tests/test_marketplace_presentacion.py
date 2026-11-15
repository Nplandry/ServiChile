from app.domain.marketplace import cta_texto, imagen_efectiva, logo_texto


def test_cta_por_categoria():

    assert cta_texto("tecnologia") == "Ver ficha de transparencia"

    assert cta_texto("industria") == "Evaluar proveedor"

    assert cta_texto("logistica") == "Validar operador logístico"

    assert cta_texto("desconocida") == "Ver ficha"


def test_logo_texto_desde_nombre():

    assert logo_texto("FitHouse Gym") == "FG"

    assert logo_texto("Bistró") == "BI"

    assert logo_texto("") == "S"


def test_imagen_efectiva_usa_guardada_o_defecto():

    propia = "https://cdn.ejemplo.cl/foto.jpg"

    assert imagen_efectiva(propia, "tecnologia") == propia

    assert "unsplash" in imagen_efectiva(None, "industria")
