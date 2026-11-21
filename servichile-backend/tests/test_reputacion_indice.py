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
    bid = alta.json()["id"]
    # Público: solo teaser (monetización). El desglose completo es del titular / compra.
    publico = client.get(f"/v1/businesses/{bid}/reputation")
    assert publico.status_code == 200
    pub = publico.json()
    assert len(pub["observables"]) == 3
    assert pub["observables_restantes"] >= 25
    assert pub["docs_empresa"] is None
    titular = client.get(
        f"/v1/businesses/{bid}/reputation",
        headers={"Authorization": f"Bearer {token_empresa}"},
    )
    assert titular.status_code == 200
    cuerpo = titular.json()
    assert len(cuerpo["observables"]) >= 25
    assert 0.0 < float(cuerpo["indice_transparencia"]) <= 10.0
    assert 0 < int(cuerpo["indice_pct"]) <= 100


def test_reputacion_inexistente(client):
    r = client.get(f"/v1/businesses/{uuid.uuid4()}/reputation")
    assert r.status_code == 404
