from fastapi.testclient import TestClient

def test_ruta_inexistente_mensaje_personalizado(client: TestClient):
    r = client.get("/esta-ruta-no-existe")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert "Ruta no encontrada" in detail
    assert "/esta-ruta-no-existe" in detail
