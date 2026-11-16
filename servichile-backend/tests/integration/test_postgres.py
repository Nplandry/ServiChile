import os

import pathlib

import pytest

from fastapi.testclient import TestClient

from sqlalchemy import create_engine, text

from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import sessionmaker

from app.api import dependencias

from app.infraestructura.persistencia.modelos import get_session

from app.infraestructura.limite_solicitudes import MemoryRateLimiter

from app.principal import app

URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL no definido")

INIT_SQL = pathlib.Path(__file__).resolve().parents[2] / "db" / "init_script.sql"

TABLAS = (
    "reservas",
    "business_reputation_metrics",
    "business_entities",
    "usuario_xp_eventos",
    "perfiles",
    "usuarios",
)


@pytest.fixture(scope="module")
def engine():

    if "servichile_test" not in URL:

        pytest.fail(
            "TEST_DATABASE_URL debe apuntar a una base llamada servichile_test: estas pruebas borran tablas"
        )

    eng = create_engine(URL)

    with eng.begin() as c:

        for t in TABLAS:

            c.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE"))

        c.execute(text("DROP TABLE IF EXISTS consultas CASCADE"))

        c.execute(text("DROP TABLE IF EXISTS fragmentos CASCADE"))

        c.execute(text("DROP TABLE IF EXISTS documentos CASCADE"))

    sql = INIT_SQL.read_text(encoding="utf-8")

    with eng.connect() as c:

        c.exec_driver_sql(sql)

        c.commit()

    yield eng

    eng.dispose()


@pytest.fixture
def db(engine):

    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with engine.begin() as c:

        c.execute(text("TRUNCATE " + ", ".join(TABLAS) + " CASCADE"))

    return Session


@pytest.fixture
def client(db):

    def _session():

        with db() as s:

            yield s

    limiter = MemoryRateLimiter()

    app.dependency_overrides[get_session] = _session

    app.dependency_overrides[dependencias.get_rate_limiter] = lambda: limiter

    with TestClient(app) as c:

        yield c

    app.dependency_overrides.clear()


def test_restricciones_email_minusculas(db):

    with db() as s:

        with pytest.raises(IntegrityError):

            s.execute(
                text(
                    "insert into usuarios (email, nombre, password_hash) values ('Mayus@X.cl','A','h')"
                )
            )

        s.rollback()


def test_perfil_constraints_y_cascade(db):

    with db() as s:

        uid = s.scalar(
            text(
                "insert into usuarios (email, nombre, password_hash) values ('p@x.cl','A','h') returning id"
            )
        )

        s.execute(
            text("insert into perfiles (usuario_id, edad) values (:u, 70)"),
            {"u": uid},
        )

        s.commit()

        with pytest.raises(IntegrityError):
            s.execute(text("update perfiles set edad = 13"))
            s.rollback()

        s.execute(text("delete from usuarios where id = :u"), {"u": uid})

        s.commit()

        assert s.scalar(text("select count(*) from perfiles")) == 0


def test_registro_y_patch_perfil_en_postgres(client, db):

    datos = {
        "email": "perfil.pg@servichile.cl",
        "nombre": "Rosa",
        "password": "clave-perfil-pg",
        "perfil": {
            "tipo_cuenta": "persona",
            "edad": 68,
        },
    }

    assert client.post("/v1/auth/registro", json=datos).status_code == 201

    t = client.post(
        "/v1/auth/login", json={"email": datos["email"], "password": datos["password"]}
    ).json()

    h = {"Authorization": f"Bearer {t['access_token']}"}

    perfil = client.get("/v1/auth/yo", headers=h).json()["perfil"]

    assert perfil["edad"] == 68

    assert perfil["tipo_cuenta"] == "persona"

    assert "preocupacion" not in perfil

    with db() as s:

        fila = s.execute(text("select edad, tipo_cuenta from perfiles")).one()

    assert tuple(fila) == (68, "persona")
