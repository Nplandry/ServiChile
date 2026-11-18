import pytest

from app.dominio.ficha_negocio import (
    cta_texto,
    imagen_efectiva,
    logo_efectivo,
    logo_texto,
    normalizar_url_recurso,
    url_recurso_usable,
)


def test_cta_por_categoria():
    assert cta_texto("tecnologia") == "Ver ficha de transparencia"
    assert cta_texto("industria") == "Evaluar proveedor"
    assert cta_texto("logistica") == "Validar operador logístico"
    assert cta_texto("desconocida") == "Ver ficha"


def test_logo_texto_desde_nombre():
    assert logo_texto("FitHouse Gym") == "FG"
    assert logo_texto("Bistró") == "BI"
    assert logo_texto("") == "S"


def test_normalizar_url_recurso_https_y_upgrade():
    assert (
        normalizar_url_recurso("  https://cdn.ejemplo.cl/a.jpg  ")
        == "https://cdn.ejemplo.cl/a.jpg"
    )
    assert (
        normalizar_url_recurso("http://cdn.ejemplo.cl/a.jpg")
        == "https://cdn.ejemplo.cl/a.jpg"
    )
    assert normalizar_url_recurso("") is None
    assert normalizar_url_recurso(None) is None


@pytest.mark.parametrize(
    "mala",
    [
        "ftp://cdn.ejemplo.cl/a.jpg",
        "javascript:alert(1)",
        "data:image/png;base64,xxx",
        "https://cdn.ejemplo.cl/con espacio.jpg",
        "https://solo",
        "cdn.ejemplo.cl/sin-esquema.jpg",
    ],
)
def test_normalizar_url_recurso_rechaza(mala: str):
    with pytest.raises(ValueError):
        normalizar_url_recurso(mala)


def test_imagen_efectiva_usa_guardada_o_defecto():
    propia = "https://cdn.ejemplo.cl/foto.jpg"
    assert imagen_efectiva(propia, "tecnologia") == propia
    assert "unsplash" in imagen_efectiva(None, "industria")
    assert "unsplash" in imagen_efectiva("ftp://mala.cl/x.jpg", "industria")
    assert "unsplash" in imagen_efectiva("javascript:evil", "logistica")


def test_logo_efectivo_solo_https_usable():
    assert logo_efectivo("https://cdn.ejemplo.cl/logo.png") == (
        "https://cdn.ejemplo.cl/logo.png"
    )
    assert logo_efectivo("http://cdn.ejemplo.cl/logo.png") == (
        "https://cdn.ejemplo.cl/logo.png"
    )
    assert logo_efectivo(None) is None
    assert logo_efectivo("ftp://x") is None
    assert not url_recurso_usable("not-a-url")
