import uuid


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
    assert len(cuerpo["observables"]) >= 25
    assert 0.0 < float(cuerpo["indice_transparencia"]) <= 10.0
    assert 0 < int(cuerpo["indice_pct"]) <= 100


def test_reputacion_inexistente(client):
    r = client.get(f"/v1/businesses/{uuid.uuid4()}/reputation")
    assert r.status_code == 404
