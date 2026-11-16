import uuid

from fastapi.testclient import TestClient

from app.dominio.docs_empresa import TIPOS_DOC_EMPRESA, docs_empresa_desde_raw
from app.dominio.transparencia.rating import calcular_indice

from app.infraestructura.persistencia.modelos import BusinessEntity, BusinessReputationMetrics


def test_indice_en_rango_0_a_10():
    vacio = calcular_indice(docs=None)
    completo = calcular_indice(
        docs=docs_empresa_desde_raw({t: {"verificado": True} for t in TIPOS_DOC_EMPRESA})
    )
    assert vacio == 0.0
    assert completo == 10.0
    assert 0.0 <= vacio <= 10.0
    assert 0.0 <= completo <= 10.0


def test_verificacion_sube_el_indice():
    sin_docs = calcular_indice(docs={})
    con_docs = calcular_indice(
        docs=docs_empresa_desde_raw({TIPOS_DOC_EMPRESA[0]: {"verificado": True}})
    )
    assert con_docs > sin_docs


def test_sin_resenas_no_invalida_el_indice():
    indice = calcular_indice(docs=None)
    assert 0.0 <= indice <= 10.0


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
                    final_score=kwargs.get("final_score", 7.5),
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
    assert cuerpo["indice_pct"] == 75
    assert cuerpo["docs_verificados"] == 0
    assert cuerpo["docs_total"] == len(TIPOS_DOC_EMPRESA)

    assert cuerpo["google_rating_avg"] == 4.2

    assert cuerpo["google_reviews_count"] == 150


def test_reputacion_sin_sello_verificado(client: TestClient, session_factory):

    bid = _crear_negocio(session_factory, claimed=False)

    cuerpo = client.get(f"/v1/businesses/{bid}/reputation").json()

    assert "is_verified_profile" not in cuerpo
    assert "estado_perfil" not in cuerpo

    assert "No constituye un juicio" in cuerpo["descargo"]

    assert "reviews" not in cuerpo and "comentarios" not in cuerpo


def test_reputacion_docs_solo_flags_publicos(client: TestClient, session_factory):
    with session_factory() as s:
        negocio = BusinessEntity(
            nombre="Docs Publicos SpA",
            categoria="tecnologia",
            latitud=-33.45,
            longitud=-70.66,
            docs_empresa={
                "patente": {
                    "verificado": True,
                    "verificado_en": "2026-01-01T00:00:00+00:00",
                    "score": 92,
                    "sha256_hash": "abc" * 20,
                    "glosa": "secreto",
                    "senales": ["interno"],
                }
            },
        )
        s.add(negocio)
        s.flush()
        s.add(BusinessReputationMetrics(business_id=negocio.id, final_score=5.0))
        s.commit()
        bid = negocio.id

    cuerpo = client.get(f"/v1/businesses/{bid}/reputation").json()
    meta = cuerpo["docs_empresa"]["patente"]
    assert meta["verificado"] is True
    assert meta["verificado_en"] == "2026-01-01T00:00:00+00:00"
    assert "sha256_hash" not in meta
    assert "glosa" not in meta
    assert "score" not in meta
    assert "senales" not in meta


def test_reputacion_negocio_inexistente_da_404(client: TestClient):

    r = client.get(f"/v1/businesses/{uuid.uuid4()}/reputation")

    assert r.status_code == 404


def test_reputacion_sin_metricas_calcula_al_vuelo(client: TestClient, session_factory):

    bid = _crear_negocio(session_factory, metricas=False)

    cuerpo = client.get(f"/v1/businesses/{bid}/reputation").json()

    assert cuerpo["indice_transparencia"] == 0.0
    assert cuerpo["indice_pct"] == 0


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


def test_crear_empresa_queda_del_titular(client: TestClient, token_empresa: str):

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

    assert "is_verified_profile" not in cuerpo

    assert cuerpo["imagen_url"] == banner

    assert cuerpo["logo_url"] == "https://cdn.ejemplo.cl/logo-pyme.png"

    assert 0.0 <= float(cuerpo["indice_transparencia"]) <= 10.0
    assert 0 <= int(cuerpo["indice_pct"]) <= 100

    mias = client.get("/v1/businesses/mias", headers=h)

    assert mias.status_code == 200

    assert any((n["id"] == cuerpo["id"] for n in mias.json()))


def test_actualizar_datos_empresa_refresca_ficha(client: TestClient, token_empresa: str):
    h = {"Authorization": f"Bearer {token_empresa}"}
    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Editar SpA",
            "categoria": "tecnologia",
            "direccion": "Providencia 1",
            "rut_empresa": "76.123.456-0",
        },
    )
    assert r.status_code == 201, r.text
    bid = r.json()["id"]

    ok = client.patch(
        f"/v1/businesses/{bid}",
        headers=h,
        json={
            "nombre": "Editada SpA",
            "categoria": "industria",
            "direccion": "Las Condes 50",
            "telefono": "+56 9 8765 4321",
            "sitio_web": "https://editada.cl",
            "rut_empresa": "76.123.456-0",
        },
    )
    assert ok.status_code == 200, ok.text
    cuerpo = ok.json()
    assert cuerpo["nombre"] == "Editada SpA"
    assert cuerpo["categoria"] == "industria"
    assert cuerpo["direccion"] == "Las Condes 50"
    assert cuerpo["telefono"] == "+56 9 8765 4321"
    assert cuerpo["sitio_web"] == "https://editada.cl"
    assert cuerpo["rut_empresa"] == "76123456-0"


def test_actualizar_rut_empresa_habilita_consulta(client: TestClient, token_empresa: str):
    h = {"Authorization": f"Bearer {token_empresa}"}
    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Rut Pendiente SpA",
            "categoria": "tecnologia",
            "direccion": "Las Condes 10",
        },
    )
    assert r.status_code == 201, r.text
    bid = r.json()["id"]
    assert r.json().get("rut_empresa") in (None, "")

    bad = client.patch(
        f"/v1/businesses/{bid}/rut",
        headers=h,
        json={"rut_empresa": "no-es-rut"},
    )
    assert bad.status_code == 422

    ok = client.patch(
        f"/v1/businesses/{bid}/rut",
        headers=h,
        json={"rut_empresa": "76.123.456-0"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["rut_empresa"] == "76123456-0"

    mias = client.get("/v1/businesses/mias", headers=h)
    assert mias.status_code == 200
    mia = next(n for n in mias.json() if n["id"] == bid)
    assert mia["rut_empresa"] == "76123456-0"


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


def test_eliminar_empresa_la_borra(client: TestClient, token_empresa: str):

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

    r = client.delete(f"/v1/businesses/{bid}", headers=h)

    assert r.status_code == 204

    mias = client.get("/v1/businesses/mias", headers=h)

    assert mias.status_code == 200

    assert all((n["id"] != bid for n in mias.json()))

    publico = client.get("/v1/businesses")

    assert all((n["id"] != bid for n in publico.json()))

    assert client.get(f"/v1/businesses/{bid}/reputation").status_code == 404


def test_eliminar_empresa_ajena_da_403(
    client: TestClient, session_factory, token_empresa: str
):

    bid = _crear_negocio(session_factory, claimed=True)

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.delete(f"/v1/businesses/{bid}", headers=h)

    assert r.status_code == 403


def test_eliminar_empresa_inexistente_da_404(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.delete(f"/v1/businesses/{uuid.uuid4()}", headers=h)

    assert r.status_code == 404


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
    assert item["indice_pct"] == 75

    assert item["latitud"] == -33.45 and item["longitud"] == -70.66

    assert item["requiere_nivel"] == 1

    assert item["cta_texto"] == "Ver ficha de transparencia"

    assert item["logo_texto"]

    assert item["imagen_url"]

    assert "google_reviews_count" not in item
    assert "docs_empresa" not in item
    assert "rut_empresa" not in item
    assert "telefono" not in item
    assert "sitio_web" not in item


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

    assert cuerpo[0]["indice_transparencia"] == 0.0
    assert cuerpo[0]["indice_pct"] == 0
