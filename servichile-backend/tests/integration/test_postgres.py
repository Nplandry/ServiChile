"""Pruebas de integración contra PostgreSQL real con pgvector.

Requieren una base vacía dedicada a pruebas (se borra y se recrea en cada ejecución):

    createdb -O servichile servichile_test
    psql -d servichile_test -c "CREATE EXTENSION IF NOT EXISTS vector"   # como superusuario
    TEST_DATABASE_URL=postgresql+psycopg://servichile:CLAVE@localhost:5432/servichile_test pytest tests/integration

Sin TEST_DATABASE_URL se omiten.
"""
import os
import pathlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.config import get_settings
from app.infrastructure.db import Documento, Fragmento, get_session
from app.infrastructure.llm import FakeProvider
from app.infrastructure.rate_limit import MemoryRateLimiter
from app.infrastructure.repositories import FragmentoRepository
from app.main import app

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL no definido")

INIT_SQL = pathlib.Path(__file__).resolve().parents[2] / "db" / "init_script.sql"
TABLAS = ("consultas", "fragmentos", "documentos", "perfiles", "usuarios")


@pytest.fixture(scope="module")
def engine():
    if "servichile_test" not in URL:
        pytest.fail("TEST_DATABASE_URL debe apuntar a una base llamada servichile_test: estas pruebas borran tablas")
    eng = create_engine(URL)
    with eng.begin() as c:
        for t in TABLAS:
            c.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE"))
    # Ejecuta el script real, el mismo que se usa para crear la base de producción
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
def llm() -> FakeProvider:
    return FakeProvider(get_settings().embedding_dim)


def _cargar(db, llm, titulo, categoria, textos, sha):
    with db() as s:
        doc = Documento(titulo=titulo, categoria=categoria, hash_sha256=sha.ljust(64, "0"), url_fuente="https://x.cl")
        s.add(doc)
        s.flush()
        vectores = llm.embed(textos, para_consulta=False)
        s.add_all(
            Fragmento(documento_id=doc.id, pagina=i + 1, orden=i, contenido=t, embedding=v)
            for i, (t, v) in enumerate(zip(textos, vectores, strict=True))
        )
        s.commit()


SEGUROS = ["El seguro requiere consentimiento expreso del asegurado.", "La póliza debe entregarse por escrito."]
GENERAL = ["Toda persona puede reclamar ante SERNAC por cobros indebidos."]
TELCO = ["El código SMS autoriza la portabilidad del número."]


@pytest.fixture
def cargado(db, llm):
    _cargar(db, llm, "Norma seguros", "seguros", SEGUROS, "a")
    _cargar(db, llm, "Norma general", None, GENERAL, "b")
    _cargar(db, llm, "Norma telco", "portabilidad", TELCO, "c")
    return db


# Esquema

def test_extension_e_indice_hnsw(engine):
    with engine.connect() as c:
        assert c.scalar(text("select extversion from pg_extension where extname='vector'"))
        indexdef = c.scalar(text("select indexdef from pg_indexes where indexname='fragmentos_embedding_idx'"))
    assert "hnsw" in indexdef and "vector_cosine_ops" in indexdef


def test_restricciones_del_esquema(db):
    with db() as s:
        with pytest.raises(IntegrityError):
            s.execute(text("insert into usuarios (email, nombre, password_hash) values ('Mayus@X.cl','A','h')"))
        s.rollback()
        with pytest.raises(IntegrityError):
            s.execute(
                text("insert into documentos (titulo, categoria, hash_sha256) values ('t','otra',repeat('a',64))")
            )
        s.rollback()


def test_hash_de_documento_unico(db, llm):
    _cargar(db, llm, "Uno", None, ["texto"], "d")
    with pytest.raises(IntegrityError):
        _cargar(db, llm, "Dos", None, ["texto"], "d")


def test_borrar_documento_borra_fragmentos(cargado):
    with cargado() as s:
        s.execute(text("delete from documentos where titulo='Norma seguros'"))
        s.commit()
        assert s.scalar(text("select count(*) from fragmentos")) == len(GENERAL) + len(TELCO)


# Búsqueda vectorial

def test_busqueda_ordena_por_distancia(cargado, llm):
    with cargado() as s:
        [v] = llm.embed([SEGUROS[1]], para_consulta=True)
        r = FragmentoRepository(s).buscar(v, k=4, max_distancia=2.0, categoria=None)
    assert r[0].contenido == SEGUROS[1]
    assert r[0].distancia == pytest.approx(0, abs=1e-6)
    assert [x.distancia for x in r] == sorted(x.distancia for x in r)


def test_busqueda_aplica_umbral(cargado, llm):
    with cargado() as s:
        [v] = llm.embed([SEGUROS[0]], para_consulta=True)
        r = FragmentoRepository(s).buscar(v, k=10, max_distancia=0.5, categoria=None)
    assert [x.contenido for x in r] == [SEGUROS[0]]


def test_filtro_categoria_incluye_documentos_generales(cargado, llm):
    with cargado() as s:
        [v] = llm.embed([GENERAL[0]], para_consulta=True)
        r = FragmentoRepository(s).buscar(v, k=10, max_distancia=2.0, categoria="seguros")
    titulos = {x.titulo for x in r}
    assert titulos == {"Norma seguros", "Norma general"}
    assert r[0].contenido == GENERAL[0]


def test_filtro_categoria_excluye_otras_categorias(cargado, llm):
    with cargado() as s:
        [v] = llm.embed([TELCO[0]], para_consulta=True)
        r = FragmentoRepository(s).buscar(v, k=10, max_distancia=2.0, categoria="seguros")
    assert all(x.titulo != "Norma telco" for x in r)


# API de punta a punta con PostgreSQL

@pytest.fixture
def client(cargado):
    def _session():
        with cargado() as s:
            yield s

    limiter = MemoryRateLimiter()
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[deps.get_rate_limiter] = lambda: limiter
    app.dependency_overrides[deps.get_llm] = lambda: FakeProvider(get_settings().embedding_dim)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _token(client: TestClient) -> str:
    datos = {"email": "Int@Servichile.cl", "nombre": "Prueba", "password": "clave-integracion-1"}
    assert client.post("/v1/auth/registro", json=datos).status_code == 201
    r = client.post("/v1/auth/login", json={"email": datos["email"], "password": datos["password"]})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_flujo_completo_con_fuentes(client, cargado):
    h = {"Authorization": f"Bearer {_token(client)}"}
    r = client.post("/v1/consultas", json={"pregunta": SEGUROS[0], "categoria": "seguros"}, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["requiere_humano"] is False
    assert body["fuentes"][0] == {"n": 1, "titulo": "Norma seguros", "url": "https://x.cl", "pagina": 1}

    with cargado() as s:
        fila = s.execute(text("select fuentes, requiere_humano from consultas")).one()
    assert fila.fuentes[0]["titulo"] == "Norma seguros"  # guardado como jsonb
    assert fila.requiere_humano is False


def test_flujo_sin_fuentes_y_redaccion(client, cargado):
    h = {"Authorization": f"Bearer {_token(client)}"}
    r = client.post(
        "/v1/consultas",
        json={"pregunta": "Mi RUT es 12.345.678-5 y me llaman al +56 9 1234 5678"},
        headers=h,
    )
    assert r.json()["requiere_humano"] is True
    assert r.json()["fuentes"] == []
    historial = client.get("/v1/consultas", headers=h).json()
    assert historial[0]["pregunta_redactada"] == "Mi RUT es [RUT] y me llaman al [TELEFONO]"
    with cargado() as s:
        guardado = s.scalar(text("select pregunta_redactada from consultas"))
    assert "12.345.678" not in guardado and "1234 5678" not in guardado


def test_historial_es_privado_por_usuario(client):
    h1 = {"Authorization": f"Bearer {_token(client)}"}
    client.post("/v1/consultas", json={"pregunta": "Pregunta del usuario uno"}, headers=h1)
    otro = {"email": "otro@servichile.cl", "nombre": "Otro", "password": "clave-otro-123"}
    client.post("/v1/auth/registro", json=otro)
    t2 = client.post("/v1/auth/login", json={"email": otro["email"], "password": otro["password"]}).json()
    h2 = {"Authorization": f"Bearer {t2['access_token']}"}
    assert client.get("/v1/consultas", headers=h2).json() == []
    assert len(client.get("/v1/consultas", headers=h1).json()) == 1


def test_historial_orden_y_limite(client):
    h = {"Authorization": f"Bearer {_token(client)}"}
    for i in range(3):
        client.post("/v1/consultas", json={"pregunta": f"Pregunta número {i}"}, headers=h)
    r = client.get("/v1/consultas?limite=2", headers=h).json()
    assert [c["pregunta_redactada"] for c in r] == ["Pregunta número 2", "Pregunta número 1"]


def test_perfil_constraints_y_cascade(db):
    with db() as s:
        uid = s.scalar(
            text("insert into usuarios (email, nombre, password_hash) values ('p@x.cl','A','h') returning id")
        )
        s.execute(text("insert into perfiles (usuario_id, edad, preocupacion) values (:u, 70, 'seguros')"), {"u": uid})
        s.commit()
        for sql in (
            "update perfiles set edad = 13",
            "update perfiles set preocupacion = 'otra'",
            "update perfiles set proposito = 'otro'",
        ):
            with pytest.raises(IntegrityError):
                s.execute(text(sql))
            s.rollback()
        s.execute(text("delete from usuarios where id = :u"), {"u": uid})
        s.commit()
        assert s.scalar(text("select count(*) from perfiles")) == 0


def test_registro_y_patch_perfil_en_postgres(client, cargado):
    datos = {
        "email": "perfil.pg@servichile.cl", "nombre": "Rosa", "password": "clave-perfil-pg",
        "perfil": {"edad": 68, "preocupacion": "telecom", "proposito": "investigar"},
    }
    assert client.post("/v1/auth/registro", json=datos).status_code == 201
    t = client.post("/v1/auth/login", json={"email": datos["email"], "password": datos["password"]}).json()
    h = {"Authorization": f"Bearer {t['access_token']}"}
    assert client.get("/v1/auth/yo", headers=h).json()["perfil"] == datos["perfil"]
    client.patch("/v1/perfil", json={"preocupacion": "embargo"}, headers=h)
    with cargado() as s:
        fila = s.execute(text("select edad, preocupacion, proposito from perfiles")).one()
    assert tuple(fila) == (68, "embargo", "investigar")
