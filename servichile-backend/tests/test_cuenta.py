import uuid

from fastapi.testclient import TestClient

from app.infraestructura.persistencia.modelos import BusinessEntity

CLAVE = "clave-segura-123"


def _cuenta(client: TestClient, email: str, tipo: str = "persona") -> dict[str, str]:

    datos = {
        "email": email,
        "nombre": "Usuario Prueba",
        "password": CLAVE,
        "perfil": {"tipo_cuenta": tipo},
    }

    assert client.post("/v1/auth/registro", json=datos).status_code == 201

    t = client.post("/v1/auth/login", json={"email": email, "password": CLAVE}).json()

    return {"Authorization": f"Bearer {t['access_token']}"}


def _negocio(session_factory, nombre="Proveedor TI Central") -> uuid.UUID:

    with session_factory() as s:

        negocio = BusinessEntity(
            nombre=nombre, categoria="tecnologia", latitud=-33.45, longitud=-70.66
        )

        s.add(negocio)

        s.commit()

        return negocio.id


def _reservar(client: TestClient, headers, business_id) -> dict:

    r = client.post(
        "/v1/reservas", json={"business_id": str(business_id)}, headers=headers
    )

    assert r.status_code == 201, r.text

    return r.json()


def test_cancelar_reserva_propia_cambia_estado(client: TestClient, session_factory):

    bid = _negocio(session_factory)

    h = _cuenta(client, "cancela@servichile.cl")

    reserva = _reservar(client, h, bid)

    r = client.delete(f"/v1/reservas/{reserva['id']}", headers=h)

    assert r.status_code == 200, r.text

    assert r.json()["estado"] == "cancelada"

    activas = [
        x
        for x in client.get("/v1/reservas", headers=h).json()
        if x["id"] == reserva["id"]
    ]

    assert activas[0]["estado"] == "cancelada"


def test_cancelar_dos_veces_da_409(client: TestClient, session_factory):

    bid = _negocio(session_factory)

    h = _cuenta(client, "dos@servichile.cl")

    reserva = _reservar(client, h, bid)

    client.delete(f"/v1/reservas/{reserva['id']}", headers=h)

    assert client.delete(f"/v1/reservas/{reserva['id']}", headers=h).status_code == 409


def test_cancelar_reserva_ajena_da_404(client: TestClient, session_factory):

    bid = _negocio(session_factory)

    dueno = _cuenta(client, "dueno@servichile.cl")

    otro = _cuenta(client, "otro@servichile.cl")

    reserva = _reservar(client, dueno, bid)

    assert (
        client.delete(f"/v1/reservas/{reserva['id']}", headers=otro).status_code == 404
    )


def test_cancelar_requiere_sesion(client: TestClient):

    assert client.delete(f"/v1/reservas/{uuid.uuid4()}").status_code == 401


def test_eliminar_cuenta_con_contrasena_incorrecta_da_403(client: TestClient):

    h = _cuenta(client, "nofunciona@servichile.cl")

    r = client.request(
        "DELETE", "/v1/auth/yo", json={"password": "otra-clave-123"}, headers=h
    )

    assert r.status_code == 403

    assert client.get("/v1/auth/yo", headers=h).status_code == 200


def test_eliminar_cuenta_borra_el_acceso(client: TestClient):

    h = _cuenta(client, "borrame@servichile.cl")

    r = client.request("DELETE", "/v1/auth/yo", json={"password": CLAVE}, headers=h)

    assert r.status_code == 204

    assert client.get("/v1/auth/yo", headers=h).status_code == 401

    login = client.post(
        "/v1/auth/login", json={"email": "borrame@servichile.cl", "password": CLAVE}
    )

    assert login.status_code == 401


def test_eliminar_cuenta_libera_negocios_reclamados(
    client: TestClient, session_factory
):

    bid = _negocio(session_factory, nombre="Negocio a reclamar")

    h = _cuenta(client, "titular@servichile.cl", tipo="proveedor")

    claim = client.post(
        f"/v1/businesses/{bid}/claim",
        json={"documento_verificacion": "76.543.210-K"},
        headers=h,
    )

    assert claim.status_code == 201

    assert (
        client.get(f"/v1/businesses/{bid}/reputation").json()["is_verified_profile"]
        is True
    )

    client.request("DELETE", "/v1/auth/yo", json={"password": CLAVE}, headers=h)

    despues = client.get(f"/v1/businesses/{bid}/reputation").json()

    assert despues["is_verified_profile"] is False

    assert despues["estado_perfil"] == "Perfil No Verificado / Índice Básico"


def test_eliminar_cuenta_requiere_sesion(client: TestClient):

    r = client.request("DELETE", "/v1/auth/yo", json={"password": CLAVE})

    assert r.status_code == 401
