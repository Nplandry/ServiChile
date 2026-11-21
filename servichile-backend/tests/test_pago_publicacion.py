import uuid

import pytest
from fastapi.testclient import TestClient


def _proveedor(client: TestClient, email: str) -> dict:
    assert (
        client.post(
            "/v1/auth/registro",
            json={
                "email": email,
                "nombre": "Proveedor Pub",
                "password": "clave-segura-123",
                "perfil": {"tipo_cuenta": "proveedor"},
            },
        ).status_code
        == 201
    )
    token = client.post(
        "/v1/auth/login", json={"email": email, "password": "clave-segura-123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _ficha_minima(**extra):
    body = {
        "nombre": "Pyme Publicada SpA",
        "categoria": "tecnologia",
        "direccion": "Providencia 200, Santiago",
        "telefono": "+56 9 1111 2222",
        "rut_empresa": "76.111.222-3",
    }
    body.update(extra)
    return body


def _pagar_cupon(client: TestClient, headers: dict) -> dict:
    ini = client.post("/v1/pagos/publicacion", json={}, headers=headers).json()
    conf = client.post(
        "/v1/pagos/publicacion/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    assert conf.status_code == 200, conf.text
    return conf.json()


def test_catalogo_pago_publicacion(client: TestClient):
    from app.dominio.pago_publicacion import PRECIO_PUBLICACION_CLP

    r = client.get("/v1/pagos/publicacion/catalogo")
    assert r.status_code == 200, r.text
    assert r.json()["monto"] == PRECIO_PUBLICACION_CLP
    assert r.json()["moneda"] == "CLP"
    assert r.json()["producto"] == "publicacion_empresa"


def test_pago_publicacion_iniciar_y_confirmar(client: TestClient):
    headers = _proveedor(client, f"pub.{uuid.uuid4().hex[:8]}@example.com")

    ini = client.post("/v1/pagos/publicacion", json={}, headers=headers)
    assert ini.status_code == 200, ini.text
    data = ini.json()
    assert data["buy_order"].startswith("SCP")
    assert data["token"]
    assert data["url"]
    assert data["monto"] == 8990
    assert "pagos@" in data["reclamo"]["email"]

    conf = client.post(
        "/v1/pagos/publicacion/confirmar",
        json={"token": data["token"]},
        headers=headers,
    )
    assert conf.status_code == 200, conf.text
    out = conf.json()
    assert out["autorizado"] is True
    assert out["estado"] == "autorizado"
    assert out["buy_order"] == data["buy_order"]
    assert out["consumido"] is False

    acceso = client.get("/v1/pagos/publicacion/acceso", headers=headers)
    assert acceso.status_code == 200, acceso.text
    assert acceso.json()["buy_order"] == data["buy_order"]
    assert acceso.json()["autorizado"] is True


def test_persona_no_puede_iniciar_pago_publicacion(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/v1/pagos/publicacion", json={}, headers=h)
    assert r.status_code == 403, r.text


def test_crear_empresa_con_cupon_publicacion(client: TestClient):
    headers = _proveedor(client, f"pub.ok.{uuid.uuid4().hex[:8]}@example.com")
    conf = _pagar_cupon(client, headers)
    buy_order = conf["buy_order"]

    alta = client.post(
        "/v1/businesses",
        headers=headers,
        json=_ficha_minima(buy_order=buy_order),
    )
    assert alta.status_code == 201, alta.text
    bid = alta.json()["id"]

    acceso = client.get("/v1/pagos/publicacion/acceso", headers=headers)
    assert acceso.status_code == 402

    estado = client.get(f"/v1/pagos/publicacion/{buy_order}", headers=headers)
    assert estado.status_code == 200
    assert estado.json()["consumido"] is True
    assert estado.json()["estado"] == "consumido"
    assert estado.json()["autorizado"] is True
    assert estado.json()["business_id"] == bid


def test_doble_consumo_mismo_buy_order_da_402(
    client: TestClient, monkeypatch
):
    from app.configuracion import obtener_configuracion

    headers = _proveedor(client, f"pub.race.{uuid.uuid4().hex[:8]}@example.com")
    conf = _pagar_cupon(client, headers)
    buy_order = conf["buy_order"]

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    obtener_configuracion.cache_clear()
    try:
        a = client.post(
            "/v1/businesses",
            headers=headers,
            json=_ficha_minima(buy_order=buy_order, rut_empresa="76.100.200-1"),
        )
        assert a.status_code == 201, a.text
        b = client.post(
            "/v1/businesses",
            headers=headers,
            json=_ficha_minima(
                buy_order=buy_order,
                nombre="Segunda SpA",
                rut_empresa="76.100.200-K",
            ),
        )
        assert b.status_code == 402, b.text
        assert b.json()["detail"]["codigo"] == "publicacion_sin_pago"
        mias = client.get("/v1/businesses/mias", headers=headers)
        assert mias.status_code == 200
        assert len(mias.json()) == 1
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()


def test_borrar_ficha_no_recicla_cupon_con_set_null(
    client: TestClient, session_factory, monkeypatch
):
    from sqlalchemy import select

    from app.configuracion import obtener_configuracion
    from app.dominio.pago_publicacion import ESTADO_CONSUMIDO
    from app.infraestructura.persistencia import modelos as orm

    headers = _proveedor(client, f"pub.del2.{uuid.uuid4().hex[:8]}@example.com")
    conf = _pagar_cupon(client, headers)
    buy_order = conf["buy_order"]

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    obtener_configuracion.cache_clear()
    try:
        alta = client.post(
            "/v1/businesses",
            headers=headers,
            json=_ficha_minima(buy_order=buy_order, rut_empresa="76.777.888-2"),
        )
        assert alta.status_code == 201, alta.text
        bid = alta.json()["id"]
        assert client.delete(f"/v1/businesses/{bid}", headers=headers).status_code == 204

        with session_factory() as s:
            row = s.scalars(
                select(orm.CompraPublicacion).where(
                    orm.CompraPublicacion.buy_order == buy_order
                )
            ).first()
            assert row is not None
            assert row.estado == ESTADO_CONSUMIDO
            # Fuerza el efecto de ON DELETE SET NULL.
            row.business_id = None
            s.commit()

        acceso = client.get("/v1/pagos/publicacion/acceso", headers=headers)
        assert acceso.status_code == 402, acceso.text

        reintento = client.post(
            "/v1/businesses",
            headers=headers,
            json=_ficha_minima(
                buy_order=buy_order, rut_empresa="76.777.888-2", nombre="Otra"
            ),
        )
        assert reintento.status_code == 402
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()


def test_cupon_disponible_bloquea_nuevo_inicio(client: TestClient):
    headers = _proveedor(client, f"pub.cup.{uuid.uuid4().hex[:8]}@example.com")
    ini = client.post("/v1/pagos/publicacion", json={}, headers=headers).json()
    client.post(
        "/v1/pagos/publicacion/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    otra = client.post("/v1/pagos/publicacion", json={}, headers=headers)
    assert otra.status_code == 409
    assert otra.json()["detail"]["codigo"] == "cupon_disponible"
    assert otra.json()["detail"]["buy_order"] == ini["buy_order"]


def test_return_url_no_permitida_publicacion(client: TestClient):
    headers = _proveedor(client, f"pub.url.{uuid.uuid4().hex[:8]}@example.com")
    r = client.post(
        "/v1/pagos/publicacion",
        json={"return_url": "https://evil.example/phish?pago=retorno"},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["codigo"] == "return_url_no_permitida"


def test_compra_ajena_publicacion(client: TestClient):
    a = _proveedor(client, f"pub.a.{uuid.uuid4().hex[:8]}@example.com")
    b = _proveedor(client, f"pub.b.{uuid.uuid4().hex[:8]}@example.com")
    ini = client.post("/v1/pagos/publicacion", json={}, headers=a).json()
    r = client.post(
        "/v1/pagos/publicacion/confirmar",
        json={"token": ini["token"]},
        headers=b,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["codigo"] == "compra_ajena"


def test_doble_confirmar_idempotente(client: TestClient):
    headers = _proveedor(client, f"pub.dup.{uuid.uuid4().hex[:8]}@example.com")
    ini = client.post("/v1/pagos/publicacion", json={}, headers=headers).json()
    c1 = client.post(
        "/v1/pagos/publicacion/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    c2 = client.post(
        "/v1/pagos/publicacion/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    assert c1.status_code == 200
    assert c2.status_code == 200
    assert c2.json()["autorizado"] is True
    assert c2.json()["estado"] == "autorizado"


def test_anular_pago_publicacion(client: TestClient):
    headers = _proveedor(client, f"pub.an.{uuid.uuid4().hex[:8]}@example.com")
    ini = client.post("/v1/pagos/publicacion", json={}, headers=headers).json()
    an = client.post(
        "/v1/pagos/publicacion/anular",
        json={"buy_order": ini["buy_order"], "motivo": "Abortó Webpay"},
        headers=headers,
    )
    assert an.status_code == 200, an.text
    assert an.json()["estado"] == "anulado"
    assert an.json()["autorizado"] is False


def test_crear_empresa_exige_pago_fuera_de_test(
    client: TestClient, token_empresa: str, monkeypatch
):
    from app.configuracion import obtener_configuracion

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    obtener_configuracion.cache_clear()
    try:
        h = {"Authorization": f"Bearer {token_empresa}"}
        r = client.post(
            "/v1/businesses",
            headers=h,
            json=_ficha_minima(rut_empresa="76.333.444-5"),
        )
        assert r.status_code == 402, r.text
        assert r.json()["detail"]["codigo"] == "publicacion_sin_pago"
        assert "8.990" in r.json()["detail"]["mensaje"]

        conf = _pagar_cupon(client, h)
        ok = client.post(
            "/v1/businesses",
            headers=h,
            json=_ficha_minima(
                rut_empresa="76.333.444-5", buy_order=conf["buy_order"]
            ),
        )
        assert ok.status_code == 201, ok.text
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()


def test_recuperar_pago_publicacion(client: TestClient):
    headers = _proveedor(client, f"pub.rec.{uuid.uuid4().hex[:8]}@example.com")
    conf = _pagar_cupon(client, headers)
    rec = client.post(
        "/v1/pagos/publicacion/recuperar",
        json={"buy_order": conf["buy_order"]},
        headers=headers,
    )
    assert rec.status_code == 200
    assert rec.json()["autorizado"] is True
    assert rec.json()["buy_order"] == conf["buy_order"]


def test_reserva_en_misma_tx_rollback_deja_autorizado(
    client: TestClient, session_factory, monkeypatch
):
    """Reserva flush + rollback no deja el pago en reservado."""
    from sqlalchemy import select

    from app.configuracion import obtener_configuracion
    from app.dominio.pago_publicacion import ESTADO_AUTORIZADO, ESTADO_RESERVADO
    from app.infraestructura.persistencia import modelos as orm
    from app.infraestructura.persistencia.repositorios import (
        RepositorioCompraPublicacion,
    )

    headers = _proveedor(client, f"pub.rtx.{uuid.uuid4().hex[:8]}@example.com")
    conf = _pagar_cupon(client, headers)
    buy_order = conf["buy_order"]

    with session_factory() as s:
        repo = RepositorioCompraPublicacion(s)
        row = s.scalars(
            select(orm.CompraPublicacion).where(
                orm.CompraPublicacion.buy_order == buy_order
            )
        ).first()
        assert row is not None
        ok = repo.reservar_para_alta(row.usuario_id, buy_order, commit=False)
        assert ok is not None
        assert ok.estado == ESTADO_RESERVADO
        s.rollback()
        otra = repo.obtener_por_buy_order(buy_order)
        assert otra is not None
        assert otra.estado == ESTADO_AUTORIZADO

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    obtener_configuracion.cache_clear()
    try:
        alta = client.post(
            "/v1/businesses",
            headers=headers,
            json=_ficha_minima(
                buy_order=buy_order, rut_empresa="76.888.999-3", nombre="Rtx SpA"
            ),
        )
        assert alta.status_code == 201, alta.text
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()


def test_liberar_reservas_stale(client: TestClient, session_factory):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.dominio.pago_publicacion import ESTADO_AUTORIZADO, ESTADO_RESERVADO
    from app.infraestructura.persistencia import modelos as orm
    from app.infraestructura.persistencia.repositorios import (
        RepositorioCompraPublicacion,
    )

    headers = _proveedor(client, f"pub.stale.{uuid.uuid4().hex[:8]}@example.com")
    conf = _pagar_cupon(client, headers)
    buy_order = conf["buy_order"]

    with session_factory() as s:
        row = s.scalars(
            select(orm.CompraPublicacion).where(
                orm.CompraPublicacion.buy_order == buy_order
            )
        ).first()
        assert row is not None
        row.estado = ESTADO_RESERVADO
        row.actualizado_en = datetime.now(timezone.utc) - timedelta(minutes=10)
        s.commit()

        n = RepositorioCompraPublicacion(s).liberar_reservas_stale(max_edad_seg=180)
        assert n >= 1
        otra = RepositorioCompraPublicacion(s).obtener_por_buy_order(buy_order)
        assert otra is not None
        assert otra.estado == ESTADO_AUTORIZADO


def test_exige_pago_si_app_env_test_sin_pytest(monkeypatch):
    from app.api.v1.negocios import _exige_pago_publicacion
    from app.configuracion import obtener_configuracion

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("SERVICHILE_SKIP_PAGO_PUBLICACION", raising=False)
    obtener_configuracion.cache_clear()
    try:
        assert _exige_pago_publicacion(obtener_configuracion()) is True
    finally:
        obtener_configuracion.cache_clear()


def test_alta_atomica_no_deja_ficha_si_consumir_falla(
    client: TestClient, monkeypatch
):
    """Si falla el consumo tras flush, rollback: sin ficha huérfana."""
    from app.configuracion import obtener_configuracion
    from app.dominio.errores import PublicacionSinPago
    from app.servicios.pago_publicacion import ServicioPagoPublicacion

    headers = _proveedor(client, f"pub.tx.{uuid.uuid4().hex[:8]}@example.com")
    conf = _pagar_cupon(client, headers)
    buy_order = conf["buy_order"]

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    obtener_configuracion.cache_clear()

    real = ServicioPagoPublicacion.consumir_para_publicar

    def _boom(self, usuario_id, buy_order, business_id, *, commit=True):
        raise PublicacionSinPago("forzado en test")

    monkeypatch.setattr(
        ServicioPagoPublicacion, "consumir_para_publicar", _boom
    )
    try:
        r = client.post(
            "/v1/businesses",
            headers=headers,
            json=_ficha_minima(
                buy_order=buy_order, rut_empresa="76.999.111-5", nombre="Tx SpA"
            ),
        )
        assert r.status_code == 402, r.text
        mias = client.get("/v1/businesses/mias", headers=headers)
        assert mias.status_code == 200
        assert mias.json() == []
        acceso = client.get("/v1/pagos/publicacion/acceso", headers=headers)
        assert acceso.status_code == 200, acceso.text
        assert acceso.json()["estado"] == "autorizado"
        assert acceso.json()["consumido"] is False
    finally:
        monkeypatch.setattr(
            ServicioPagoPublicacion, "consumir_para_publicar", real
        )
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()


def test_confirmar_publicacion_avisa_correo(client: TestClient, monkeypatch):
    from app.api import dependencias
    from app.infraestructura.correo_plataforma import EnviadorMemoria
    from app.principal import app

    enviador = EnviadorMemoria(simular=True)
    app.dependency_overrides[dependencias.obtener_enviador] = lambda: enviador
    try:
        headers = _proveedor(client, f"pub.mail.{uuid.uuid4().hex[:8]}@example.com")
        ini = client.post("/v1/pagos/publicacion", json={}, headers=headers).json()
        conf = client.post(
            "/v1/pagos/publicacion/confirmar",
            json={"token": ini["token"]},
            headers=headers,
        )
        assert conf.status_code == 200, conf.text
        assert any("publicación" in m.asunto.lower() for m in enviador.enviados)
    finally:
        app.dependency_overrides.pop(dependencias.obtener_enviador, None)


def test_alta_libera_reserva_si_rut_duplicado(
    client: TestClient, monkeypatch
):
    from app.configuracion import obtener_configuracion

    headers = _proveedor(client, f"pub.lib.{uuid.uuid4().hex[:8]}@example.com")
    # Primera ficha sin pago (APP_ENV=test).
    previa = client.post(
        "/v1/businesses",
        headers=headers,
        json=_ficha_minima(rut_empresa="76.123.456-0", nombre="Primera SpA"),
    )
    assert previa.status_code == 201, previa.text
    assert previa.json().get("rut_empresa") == "76123456-0"

    conf = _pagar_cupon(client, headers)
    buy_order = conf["buy_order"]

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    obtener_configuracion.cache_clear()
    try:
        # Reserva ocurre; crear falla por RUT en uso → libera cupón.
        fallo = client.post(
            "/v1/businesses",
            headers=headers,
            json=_ficha_minima(
                buy_order=buy_order,
                rut_empresa="76.123.456-0",
                nombre="Duplicada SpA",
            ),
        )
        assert fallo.status_code == 409, fallo.text
        acceso = client.get("/v1/pagos/publicacion/acceso", headers=headers)
        assert acceso.status_code == 200, acceso.text
        assert acceso.json()["buy_order"] == buy_order
        assert acceso.json()["estado"] == "autorizado"
        assert acceso.json()["consumido"] is False
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()


def test_alta_integrity_error_no_rut_da_409_alta_conflicto(
    client: TestClient, monkeypatch
):
    """IntegrityError no-RUT → 409 alta_conflicto; cupón reusable tras rollback."""
    from sqlalchemy.exc import IntegrityError

    from app.configuracion import obtener_configuracion
    from app.servicios.negocio import ServicioNegocio

    headers = _proveedor(client, f"pub.ie.{uuid.uuid4().hex[:8]}@example.com")
    conf = _pagar_cupon(client, headers)
    buy_order = conf["buy_order"]

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    obtener_configuracion.cache_clear()

    real_crear = ServicioNegocio.crear

    def _boom(self, *args, **kwargs):
        raise IntegrityError("INSERT", {}, Exception("unique constraint faux"))

    monkeypatch.setattr(ServicioNegocio, "crear", _boom)
    try:
        r = client.post(
            "/v1/businesses",
            headers=headers,
            json=_ficha_minima(
                buy_order=buy_order,
                rut_empresa="76.444.555-6",
                nombre="Conflicto SpA",
            ),
        )
        assert r.status_code == 409, r.text
        detail = r.json()["detail"]
        assert detail["codigo"] == "alta_conflicto"
        assert "conflicto" in detail["mensaje"].lower()

        mias = client.get("/v1/businesses/mias", headers=headers)
        assert mias.status_code == 200
        assert mias.json() == []

        acceso = client.get("/v1/pagos/publicacion/acceso", headers=headers)
        assert acceso.status_code == 200, acceso.text
        assert acceso.json()["buy_order"] == buy_order
        assert acceso.json()["estado"] == "autorizado"
        assert acceso.json()["consumido"] is False

        # Cupón reusable: alta real tras quitar el boom.
        monkeypatch.setattr(ServicioNegocio, "crear", real_crear)
        ok = client.post(
            "/v1/businesses",
            headers=headers,
            json=_ficha_minima(
                buy_order=buy_order,
                rut_empresa="76.444.555-6",
                nombre="Conflicto SpA",
            ),
        )
        assert ok.status_code == 201, ok.text
    finally:
        monkeypatch.setattr(ServicioNegocio, "crear", real_crear)
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()


def test_reconciliar_publicacion_avisa_correo(client: TestClient, session_factory):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.ensamblado.pagos import armar_servicio_publicacion
    from app.infraestructura.correo_plataforma import EnviadorMemoria
    from app.infraestructura.persistencia import modelos as orm
    from app.infraestructura.persistencia.repositorios import (
        RepositorioCompraPublicacion,
        RepositorioUsuario,
    )
    from app.infraestructura.transbank_webpay import PasarelaWebpayMemoria

    headers = _proveedor(client, f"pub.recw.{uuid.uuid4().hex[:8]}@example.com")
    ini = client.post("/v1/pagos/publicacion", json={}, headers=headers).json()
    buy_order = ini["buy_order"]
    token = ini["token"]

    with session_factory() as s:
        row = s.scalars(
            select(orm.CompraPublicacion).where(
                orm.CompraPublicacion.buy_order == buy_order
            )
        ).first()
        assert row is not None
        row.creado_en = datetime.now(timezone.utc) - timedelta(minutes=10)
        s.commit()

        enviador = EnviadorMemoria(simular=True)
        servicio = armar_servicio_publicacion(s)
        servicio.enviador = enviador
        servicio.usuarios = RepositorioUsuario(s)
        pasarela = servicio.pasarela
        if isinstance(pasarela, PasarelaWebpayMemoria):
            pasarela._tokens[token] = buy_order

        n = servicio.reconciliar_pendientes(min_edad_seg=60, max_edad_seg=7200)
        assert n >= 1
        assert any("publicación" in m.asunto.lower() for m in enviador.enviados)

        compra = RepositorioCompraPublicacion(s).obtener_por_buy_order(buy_order)
        assert compra is not None
        assert compra.estado == "autorizado"
