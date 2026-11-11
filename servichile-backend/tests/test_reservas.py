"""Pruebas de reservas (nivel 1 del Pasaporte): reservar, check-in y no-show del titular."""
import uuid

from fastapi.testclient import TestClient

from app.infrastructure.db import BusinessEntity


def _negocio(session_factory) -> uuid.UUID:
    with session_factory() as s:
        negocio = BusinessEntity(nombre="Gimnasio Central", categoria="gimnasio")
        s.add(negocio)
        s.commit()
        return negocio.id


def _cuenta(client: TestClient, email: str) -> dict[str, str]:
    datos = {"email": email, "nombre": "Usuario Prueba", "password": "clave-segura-123"}
    assert client.post("/v1/auth/registro", json=datos).status_code == 201
    t = client.post("/v1/auth/login", json={"email": email, "password": datos["password"]}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def _reservar(client: TestClient, headers, business_id) -> dict:
    r = client.post("/v1/reservas", json={"business_id": str(business_id)}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _reclamar(client: TestClient, headers, business_id) -> None:
    r = client.post(
        f"/v1/businesses/{business_id}/claim",
        json={"documento_verificacion": "76.543.210-K"},
        headers=headers,
    )
    assert r.status_code == 201, r.text


def test_reservar_devuelve_codigo_qr(client: TestClient, session_factory, token: str):
    bid = _negocio(session_factory)
    h = {"Authorization": f"Bearer {token}"}
    reserva = _reservar(client, h, bid)
    assert reserva["estado"] == "reservada"
    assert len(reserva["qr_token"]) >= 10


def test_reservar_negocio_inexistente_da_404(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/v1/reservas", json={"business_id": str(uuid.uuid4())}, headers=h)
    assert r.status_code == 404


def test_listar_mis_reservas(client: TestClient, session_factory, token: str):
    bid = _negocio(session_factory)
    h = {"Authorization": f"Bearer {token}"}
    _reservar(client, h, bid)
    _reservar(client, h, bid)
    assert len(client.get("/v1/reservas", headers=h).json()) == 2


def test_checkin_del_titular_da_score_100(client: TestClient, session_factory, token: str):
    bid = _negocio(session_factory)
    titular = {"Authorization": f"Bearer {token}"}
    _reclamar(client, titular, bid)

    cliente = _cuenta(client, "cliente@servichile.cl")
    reserva = _reservar(client, cliente, bid)

    r = client.post(
        f"/v1/businesses/{bid}/checkin", json={"qr_token": reserva["qr_token"]}, headers=titular
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "asistido"
    assert client.get("/v1/perfil", headers=cliente).json()["score_confiabilidad"] == 100.0


def test_no_show_baja_el_score(client: TestClient, session_factory, token: str):
    bid = _negocio(session_factory)
    titular = {"Authorization": f"Bearer {token}"}
    _reclamar(client, titular, bid)

    cliente = _cuenta(client, "cliente@servichile.cl")
    asistio = _reservar(client, cliente, bid)
    faltó = _reservar(client, cliente, bid)
    client.post(f"/v1/businesses/{bid}/checkin", json={"qr_token": asistio["qr_token"]}, headers=titular)

    r = client.post(f"/v1/businesses/{bid}/reservas/{faltó['id']}/no-show", headers=titular)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "no_show"
    assert client.get("/v1/perfil", headers=cliente).json()["score_confiabilidad"] == 50.0


def test_checkin_de_otro_usuario_da_403(client: TestClient, session_factory, token: str):
    bid = _negocio(session_factory)
    titular = {"Authorization": f"Bearer {token}"}
    _reclamar(client, titular, bid)

    otro = _cuenta(client, "otro@servichile.cl")
    cliente = _cuenta(client, "cliente@servichile.cl")
    reserva = _reservar(client, cliente, bid)
    r = client.post(f"/v1/businesses/{bid}/checkin", json={"qr_token": reserva["qr_token"]}, headers=otro)
    assert r.status_code == 403


def test_checkin_en_negocio_no_reclamado_da_403(client: TestClient, session_factory, token: str):
    bid = _negocio(session_factory)
    cliente = _cuenta(client, "cliente@servichile.cl")
    reserva = _reservar(client, cliente, bid)
    r = client.post(f"/v1/businesses/{bid}/checkin", json={"qr_token": reserva["qr_token"]}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_qr_de_otro_negocio_da_404(client: TestClient, session_factory, token: str):
    bid_a = _negocio(session_factory)
    bid_b = _negocio(session_factory)
    titular = {"Authorization": f"Bearer {token}"}
    _reclamar(client, titular, bid_a)
    _reclamar(client, titular, bid_b)

    cliente = _cuenta(client, "cliente@servichile.cl")
    reserva_b = _reservar(client, cliente, bid_b)
    # El QR pertenece a bid_b: el titular de bid_a no puede usarlo en bid_a.
    r = client.post(f"/v1/businesses/{bid_a}/checkin", json={"qr_token": reserva_b["qr_token"]}, headers=titular)
    assert r.status_code == 404


def test_reserva_cerrada_no_se_puede_volver_a_cerrar(client: TestClient, session_factory, token: str):
    bid = _negocio(session_factory)
    titular = {"Authorization": f"Bearer {token}"}
    _reclamar(client, titular, bid)
    cliente = _cuenta(client, "cliente@servichile.cl")
    reserva = _reservar(client, cliente, bid)
    client.post(f"/v1/businesses/{bid}/checkin", json={"qr_token": reserva["qr_token"]}, headers=titular)
    r = client.post(f"/v1/businesses/{bid}/checkin", json={"qr_token": reserva["qr_token"]}, headers=titular)
    assert r.status_code == 409


def test_reservas_requieren_sesion(client: TestClient, session_factory):
    bid = _negocio(session_factory)
    assert client.post("/v1/reservas", json={"business_id": str(bid)}).status_code == 401
    assert client.get("/v1/reservas").status_code == 401
    assert client.post(f"/v1/businesses/{bid}/checkin", json={"qr_token": "x" * 12}).status_code == 401
