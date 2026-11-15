import uuid

from fastapi.testclient import TestClient

from app.domain.transparencia.reputacion import EntradaScore, calcular_indice

from app.infrastructure.persistencia.modelos import BusinessEntity, BusinessReputationMetrics


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

    indice = calcular_indice(EntradaScore(None, 0, False))

    assert 1.0 <= indice <= 10.0


def test_mas_volumen_no_baja_el_indice():

    pocas = calcular_indice(EntradaScore(4.5, 10, False))

    muchas = calcular_indice(EntradaScore(4.5, 480, False))

    assert muchas >= pocas


def _crear_negocio(
    session_factory, *, claimed=False, metricas=True, **kwargs
) -> uuid.UUID:

    with session_factory() as s:

        negocio = BusinessEntity(
            nombre=kwargs.get("nombre", "Proveedor TI Central"),
            categoria=kwargs.get("categoria", "tecnologia"),
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

    r = client.post(
        f"/v1/businesses/{bid}/claim", json={"documento_verificacion": "76.543.210-K"}
    )

    assert r.status_code == 401


def test_claim_persona_da_403(client: TestClient, session_factory, token: str):

    bid = _crear_negocio(session_factory)

    h = {"Authorization": f"Bearer {token}"}

    r = client.post(
        f"/v1/businesses/{bid}/claim",
        json={"documento_verificacion": "76.543.210-K"},
        headers=h,
    )

    assert r.status_code == 403


def test_crear_empresa_persona_da_403(client: TestClient, token: str):

    h = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Persona SpA",
            "categoria": "tecnologia",
            "direccion": "Calle 1",
        },
    )

    assert r.status_code == 403


def test_claim_marca_verificado_y_rectifica_datos(
    client: TestClient, session_factory, token_empresa: str
):

    bid = _crear_negocio(session_factory, claimed=False, rating=4.0, reviews=200)

    antes = client.get(f"/v1/businesses/{bid}/reputation").json()

    assert antes["is_verified_profile"] is False

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.post(
        f"/v1/businesses/{bid}/claim",
        json={
            "documento_verificacion": "76.543.210-K",
            "nombre": "Proveedor TI Central SpA",
        },
        headers=h,
    )

    assert r.status_code == 201, r.text

    assert r.json()["is_claimed"] is True

    assert r.json()["is_verified_profile"] is True

    despues = client.get(f"/v1/businesses/{bid}/reputation").json()

    assert despues["is_verified_profile"] is True

    assert despues["estado_perfil"] == "Perfil Verificado"

    assert despues["nombre"] == "Proveedor TI Central SpA"

    assert despues["indice_transparencia"] >= antes["indice_transparencia"]


def test_claim_dos_veces_da_409(
    client: TestClient, session_factory, token_empresa: str
):

    bid = _crear_negocio(session_factory, claimed=True)

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.post(
        f"/v1/businesses/{bid}/claim",
        json={"documento_verificacion": "76.543.210-K"},
        headers=h,
    )

    assert r.status_code == 409


def test_claim_negocio_inexistente_da_404(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.post(
        f"/v1/businesses/{uuid.uuid4()}/claim",
        json={"documento_verificacion": "76.543.210-K"},
        headers=h,
    )

    assert r.status_code == 404


def test_claim_documento_obligatorio(
    client: TestClient, session_factory, token_empresa: str
):

    bid = _crear_negocio(session_factory)

    h = {"Authorization": f"Bearer {token_empresa}"}

    assert (
        client.post(f"/v1/businesses/{bid}/claim", json={}, headers=h).status_code
        == 422
    )


def test_crear_empresa_queda_reclamada(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    banner = "https://cdn.ejemplo.cl/banner-pyme.jpg"

    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Nueva Pyme SpA",
            "categoria": "tecnologia",
            "direccion": "Providencia 100",
            "telefono": "+56 9 1111 2222",
            "imagen_url": banner,
            "logo_url": "https://cdn.ejemplo.cl/logo-pyme.png",
        },
    )

    assert r.status_code == 201, r.text

    cuerpo = r.json()

    assert cuerpo["nombre"] == "Nueva Pyme SpA"

    assert cuerpo["direccion"] == "Providencia 100"

    assert cuerpo["is_claimed"] is True

    assert cuerpo["is_verified_profile"] is True

    assert cuerpo["imagen_url"] == banner

    assert cuerpo["logo_url"] == "https://cdn.ejemplo.cl/logo-pyme.png"

    assert 1.0 <= cuerpo["indice_transparencia"] <= 10.0

    mias = client.get("/v1/businesses/mias", headers=h)

    assert mias.status_code == 200

    assert any((n["id"] == cuerpo["id"] for n in mias.json()))


def test_crear_empresa_banner_invalido_da_422(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Sin Banner SpA",
            "categoria": "industria",
            "direccion": "Av. Central 1",
            "imagen_url": "ftp://no-vale.cl/x.jpg",
        },
    )

    assert r.status_code == 422


def test_crear_empresa_sin_direccion_da_422(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.post(
        "/v1/businesses",
        headers=h,
        json={"nombre": "Sin Direccion SpA", "categoria": "industria"},
    )

    assert r.status_code == 422


def test_crear_empresa_requiere_sesion(client: TestClient):

    r = client.post(
        "/v1/businesses",
        json={
            "nombre": "Sin Sesion SpA",
            "categoria": "industria",
            "direccion": "Calle 1",
        },
    )

    assert r.status_code == 401


def test_liberar_empresa_quita_asociacion(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    creada = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Pyme Temporal SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Temporal 10",
        },
    )

    assert creada.status_code == 201

    bid = creada.json()["id"]

    r = client.delete(f"/v1/businesses/{bid}/claim", headers=h)

    assert r.status_code == 204

    mias = client.get("/v1/businesses/mias", headers=h)

    assert mias.status_code == 200

    assert all((n["id"] != bid for n in mias.json()))

    publico = client.get("/v1/businesses")

    assert any((n["id"] == bid and n["is_claimed"] is False for n in publico.json()))

    reputacion = client.get(f"/v1/businesses/{bid}/reputation")

    assert reputacion.status_code == 200

    assert reputacion.json()["is_verified_profile"] is False


def test_liberar_empresa_ajena_da_403(
    client: TestClient, session_factory, token_empresa: str
):

    bid = _crear_negocio(session_factory, claimed=True)

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.delete(f"/v1/businesses/{bid}/claim", headers=h)

    assert r.status_code == 403


def test_listado_publico_devuelve_negocios_con_indice(
    client: TestClient, session_factory
):

    _crear_negocio(session_factory, nombre="FitHouse Gym", categoria="tecnologia")

    r = client.get("/v1/businesses")

    assert r.status_code == 200, r.text

    cuerpo = r.json()

    assert len(cuerpo) == 1

    item = cuerpo[0]

    assert item["nombre"] == "FitHouse Gym"

    assert item["categoria"] == "tecnologia"

    assert item["indice_transparencia"] == 7.5

    assert item["latitud"] == -33.45 and item["longitud"] == -70.66

    assert item["requiere_nivel"] == 1

    assert item["cta_texto"] == "Ver ficha de transparencia"

    assert item["logo_texto"]

    assert item["imagen_url"]

    assert "google_reviews_count" not in item and "sentiment_positive_ratio" not in item


def test_listado_filtra_por_categoria(client: TestClient, session_factory):

    _crear_negocio(session_factory, nombre="SaaS Uno", categoria="tecnologia")

    _crear_negocio(
        session_factory,
        nombre="Maestranza Dos",
        categoria="industria",
        requiere_nivel=2,
    )

    r = client.get("/v1/businesses", params={"categoria": "industria"})

    assert r.status_code == 200

    cuerpo = r.json()

    assert len(cuerpo) == 1

    assert cuerpo[0]["categoria"] == "industria"

    assert cuerpo[0]["requiere_nivel"] == 2


def test_listado_busca_por_nombre_o_direccion(client: TestClient, session_factory):

    _crear_negocio(
        session_factory,
        nombre="Consultora Norte",
        categoria="servicios-profesionales",
        direccion="Santa Isabel 512",
    )

    _crear_negocio(
        session_factory,
        nombre="SaaS Central",
        categoria="tecnologia",
        direccion="Providencia 1420",
    )

    assert len(client.get("/v1/businesses", params={"q": "Norte"}).json()) == 1

    assert len(client.get("/v1/businesses", params={"q": "Providencia"}).json()) == 1

    assert (
        len(client.get("/v1/businesses", params={"q": "nada-que-coincide"}).json()) == 0
    )


def test_listado_vacio_sin_negocios(client: TestClient):

    assert client.get("/v1/businesses").json() == []


def test_listado_sin_metricas_calcula_indice_minimo(
    client: TestClient, session_factory
):

    _crear_negocio(session_factory, metricas=False)

    cuerpo = client.get("/v1/businesses").json()

    assert len(cuerpo) == 1

    assert 1.0 <= cuerpo[0]["indice_transparencia"] <= 10.0
