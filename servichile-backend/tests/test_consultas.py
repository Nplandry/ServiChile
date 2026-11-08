from fastapi.testclient import TestClient


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_consulta_requiere_sesion(client: TestClient):
    assert client.post("/v1/consultas", json={"pregunta": "¿Qué hago?"}).status_code == 401


def test_consulta_con_fuentes(client: TestClient, token: str, fragmentos):
    r = client.post(
        "/v1/consultas",
        json={"pregunta": "Me cobran un seguro que no pedí", "categoria": "seguros"},
        headers=_auth(token),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["requiere_humano"] is False
    assert body["fuentes"][0] == {"n": 1, "titulo": "Ley 19.496", "url": "https://www.bcn.cl/leychile", "pagina": 12}
    assert fragmentos.ultima_categoria == "seguros"


def test_consulta_sin_fuentes_deriva_a_humano(client: TestClient, token: str, fragmentos):
    fragmentos.resultados = []
    r = client.post("/v1/consultas", json={"pregunta": "Pregunta sin respaldo"}, headers=_auth(token))
    body = r.json()
    assert body["requiere_humano"] is True
    assert body["fuentes"] == []
    assert "SERNAC" in body["respuesta"]


def test_historial_guarda_pregunta_redactada(client: TestClient, token: str):
    client.post(
        "/v1/consultas",
        json={"pregunta": "Mi RUT es 12.345.678-5 y mi correo ana@mail.cl"},
        headers=_auth(token),
    )
    historial = client.get("/v1/consultas", headers=_auth(token)).json()
    assert historial[0]["pregunta_redactada"] == "Mi RUT es [RUT] y mi correo [EMAIL]"


def test_categoria_invalida(client: TestClient, token: str):
    r = client.post("/v1/consultas", json={"pregunta": "Hola hola", "categoria": "otra"}, headers=_auth(token))
    assert r.status_code == 422
