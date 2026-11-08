"""Pruebas del Índice de Transparencia de negocios.

Cubren: la fórmula pura del score, la reputación pública, el estado de perfil no
verificado, el reclamo (Derecho a Réplica) y sus errores (404, 409, sin sesión).
"""
import uuid

from fastapi.testclient import TestClient

from app.domain.reputacion import EntradaScore, calcular_indice
from app.infrastructure.db import BusinessEntity, BusinessReputationMetrics



def test_indice_en_rango_1_a_10():
    maximo = calcular_indice(EntradaScore(5.0, 100000, True))
    minimo = calcular_indice(EntradaScore(0.0, 0, False))
    assert minimo >= 1.0
    assert maximo <= 10.0
    assert maximo > minimo


def test_verificacion_sube_el_indice():
    sin_verificar = calcular_indice(EntradaScore(4.0, 200, False))
    verificado = calcular_indice(EntradaScore(4.0, 200, True))
    assert verificado > sin_verificar


def test_sin_resenas_no_invalida_el_indice():
    # Un negocio sin reseñas públicas aún recibe un índice válido (>= 1.0), no un error.
    indice = calcular_indice(EntradaScore(None, 0, False))
    assert 1.0 <= indice <= 10.0


def test_mas_volumen_no_baja_el_indice():
    pocas = calcular_indice(EntradaScore(4.5, 10, False))
    muchas = calcular_indice(EntradaScore(4.5, 480, False))
    assert muchas >= pocas



def _crear_negocio(session_factory, *, claimed=False, metricas=True, **kwargs) -> uuid.UUID:
    with session_factory() as s:
        negocio = BusinessEntity(
            nombre=kwargs.get("nombre", "Gimnasio Central"),
            categoria=kwargs.get("categoria", "gimnasio"),
            latitud=-33.45,
            longitud=-70.66,
            direccion=kwargs.get("direccion", "Av. Siempre Viva 100"),
            descripcion=kwargs.get("descripcion", "Un lugar de prueba."),
            requiere_nivel=kwargs.get("requiere_nivel", 1),
            is_claimed=claimed,
        )
        s.add(negocio)
        s.flush()
        if metricas:
            s.add(
                BusinessReputationMetrics(
                    business_id=negocio.id,
                    google_rating_avg=kwargs.get("rating", 4.2),
                    google_reviews_count=kwargs.get("reviews", 150),
                    sentiment_positive_ratio=0.8,
                    response_time_score=0.9,
                    final_score=kwargs.get("final_score", 7.5),
                    is_verified_profile=claimed,
                )
            )
        s.commit()
        return negocio.id



def test_reputacion_publica_no_requiere_sesion(client: TestClient, session_factory):
    bid = _crear_negocio(session_factory)
    r = client.get(f"/v1/businesses/{bid}/reputation")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["business_id"] == str(bid)
    assert cuerpo["indice_transparencia"] == 7.5
    assert cuerpo["google_rating_avg"] == 4.2
    assert cuerpo["google_reviews_count"] == 150


def test_reputacion_perfil_no_verificado(client: TestClient, session_factory):
    bid = _crear_negocio(session_factory, claimed=False)
    cuerpo = client.get(f"/v1/businesses/{bid}/reputation").json()
    assert cuerpo["is_verified_profile"] is False
    assert cuerpo["estado_perfil"] == "Perfil No Verificado / Índice Básico"
    # Blindaje legal: siempre incluye el descargo y nunca expone textos de reseñas.
    assert "No constituye un juicio" in cuerpo["descargo"]
    assert "reviews" not in cuerpo and "comentarios" not in cuerpo


def test_reputacion_negocio_inexistente_da_404(client: TestClient):
    r = client.get(f"/v1/businesses/{uuid.uuid4()}/reputation")
    assert r.status_code == 404


def test_reputacion_sin_metricas_calcula_al_vuelo(client: TestClient, session_factory):
    bid = _crear_negocio(session_factory, metricas=False)
    cuerpo = client.get(f"/v1/businesses/{bid}/reputation").json()
    assert 1.0 <= cuerpo["indice_transparencia"] <= 10.0



def test_claim_requiere_sesion(client: TestClient, session_factory):
    bid = _crear_negocio(session_factory)
    r = client.post(f"/v1/businesses/{bid}/claim", json={"documento_verificacion": "76.543.210-K"})
    assert r.status_code == 401


def test_claim_marca_verificado_y_rectifica_datos(client: TestClient, session_factory, token: str):
    bid = _crear_negocio(session_factory, claimed=False, rating=4.0, reviews=200)
    antes = client.get(f"/v1/businesses/{bid}/reputation").json()
    assert antes["is_verified_profile"] is False

    h = {"Authorization": f"Bearer {token}"}
    r = client.post(
        f"/v1/businesses/{bid}/claim",
        json={"documento_verificacion": "76.543.210-K", "nombre": "Gimnasio Central SpA"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["is_claimed"] is True
    assert r.json()["is_verified_profile"] is True

    despues = client.get(f"/v1/businesses/{bid}/reputation").json()
    assert despues["is_verified_profile"] is True
    assert despues["estado_perfil"] == "Perfil Verificado"
    assert despues["nombre"] == "Gimnasio Central SpA"
    assert despues["indice_transparencia"] >= antes["indice_transparencia"]


def test_claim_dos_veces_da_409(client: TestClient, session_factory, token: str):
    bid = _crear_negocio(session_factory, claimed=True)
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(f"/v1/businesses/{bid}/claim", json={"documento_verificacion": "76.543.210-K"}, headers=h)
    assert r.status_code == 409


def test_claim_negocio_inexistente_da_404(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(f"/v1/businesses/{uuid.uuid4()}/claim", json={"documento_verificacion": "76.543.210-K"}, headers=h)
    assert r.status_code == 404


def test_claim_documento_obligatorio(client: TestClient, session_factory, token: str):
    bid = _crear_negocio(session_factory)
    h = {"Authorization": f"Bearer {token}"}
    assert client.post(f"/v1/businesses/{bid}/claim", json={}, headers=h).status_code == 422



def test_listado_publico_devuelve_negocios_con_indice(client: TestClient, session_factory):
    _crear_negocio(session_factory, nombre="FitHouse Gym", categoria="gimnasio")
    r = client.get("/v1/businesses")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert len(cuerpo) == 1
    item = cuerpo[0]
    assert item["nombre"] == "FitHouse Gym"
    assert item["categoria"] == "gimnasio"
    assert item["indice_transparencia"] == 7.5
    assert item["latitud"] == -33.45 and item["longitud"] == -70.66
    assert item["requiere_nivel"] == 1
    # Blindaje legal: el listado no expone datos crudos de reseñas.
    assert "google_reviews_count" not in item and "sentiment_positive_ratio" not in item


def test_listado_filtra_por_categoria(client: TestClient, session_factory):
    _crear_negocio(session_factory, nombre="Gym Uno", categoria="gimnasio")
    _crear_negocio(session_factory, nombre="Dept Dos", categoria="arriendo", requiere_nivel=2)
    r = client.get("/v1/businesses", params={"categoria": "arriendo"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo) == 1
    assert cuerpo[0]["categoria"] == "arriendo"
    assert cuerpo[0]["requiere_nivel"] == 2


def test_listado_busca_por_nombre_o_direccion(client: TestClient, session_factory):
    _crear_negocio(session_factory, nombre="Bistró La Bourgogne", categoria="restaurante", direccion="Santa Isabel 512")
    _crear_negocio(session_factory, nombre="Gym Central", categoria="gimnasio", direccion="Providencia 1420")
    assert len(client.get("/v1/businesses", params={"q": "bourgogne"}).json()) == 1
    assert len(client.get("/v1/businesses", params={"q": "Providencia"}).json()) == 1
    assert len(client.get("/v1/businesses", params={"q": "nada-que-coincide"}).json()) == 0


def test_listado_vacio_sin_negocios(client: TestClient):
    assert client.get("/v1/businesses").json() == []


def test_listado_sin_metricas_calcula_indice_minimo(client: TestClient, session_factory):
    _crear_negocio(session_factory, metricas=False)
    cuerpo = client.get("/v1/businesses").json()
    assert len(cuerpo) == 1
    assert 1.0 <= cuerpo[0]["indice_transparencia"] <= 10.0
