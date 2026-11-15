import uuid

from app.dominio.transparencia.indicadores import razones_resenas, score_resenas


def test_score_resenas_sin_volumen_es_bajo():
    assert score_resenas(None, 0) == 20


def test_score_resenas_con_notas_queda_en_rango():
    assert 0 <= score_resenas(4.8, 120) <= 100


def test_razones_resenas_formato_reporte():
    lineas = razones_resenas(
        ficha="Mercado Libre",
        google_rating_avg=2.0,
        google_reviews_count=1455,
        score=67,
    )
    assert lineas == [
        "Ficha: Mercado Libre",
        "Rating Google: 2.0 / 5",
        "Reseñas: 1.455",
        "Score: 67 / 100",
    ]


def test_reputacion_de_ficha_nueva_no_inventa_busqueda(client, token_empresa):
    alta = client.post(
        "/v1/businesses",
        headers={"Authorization": f"Bearer {token_empresa}"},
        json={
            "nombre": "Ciber Demo SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Providencia 100, Santiago",
            "sitio_web": "https://ejemplo-ciber.cl",
        },
    )
    assert alta.status_code == 201
    r = client.get(f"/v1/businesses/{alta.json()['id']}/reputation")
    assert r.status_code == 200
    cuerpo = r.json()
    por_id = {item["id"]: item["score"] for item in cuerpo["observables_ciber"]}
    assert por_id["ssl-tls"] == 100
    assert por_id["headers-http"] == 0
    assert por_id["sii"] == 0
    assert por_id["politica-privacidad"] == 18
    assert por_id["resenas-reclamos"] == 20
    assert 1.0 <= cuerpo["indice_transparencia"] <= 10.0


def test_reputacion_inexistente(client):
    r = client.get(f"/v1/businesses/{uuid.uuid4()}/reputation")
    assert r.status_code == 404
