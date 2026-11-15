import os

os.environ.setdefault("JWT_SECRET", "test-secret-de-al-menos-32-caracteres-xx")

os.environ.setdefault("APP_ENV", "test")

import pytest

from fastapi.testclient import TestClient

from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

from app.api import dependencias

from app.infraestructura.persistencia.modelos import Base, get_session

from app.infraestructura.limite_solicitudes import MemoryRateLimiter

from app.principal import app


@pytest.fixture
def session_factory():

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    Base.metadata.create_all(
        engine,
        tables=[
            Base.metadata.tables[t]
            for t in (
                "usuarios",
                "usuario_xp_eventos",
                "perfiles",
                "business_entities",
                "business_reputation_metrics",
                "reservas",
            )
        ],
    )

    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client(session_factory):

    def _session():

        with session_factory() as s:

            yield s

    limiter = MemoryRateLimiter()

    app.dependency_overrides[get_session] = _session

    app.dependency_overrides[dependencias.get_rate_limiter] = lambda: limiter

    with TestClient(app) as c:

        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def token(client: TestClient) -> str:

    datos = {
        "email": "Maria@Servichile.cl",
        "nombre": "María González",
        "password": "clave-segura-123",
        "perfil": {"tipo_cuenta": "persona"},
    }

    assert client.post("/v1/auth/registro", json=datos).status_code == 201

    r = client.post(
        "/v1/auth/login", json={"email": datos["email"], "password": datos["password"]}
    )

    return r.json()["access_token"]


@pytest.fixture
def token_empresa(client: TestClient) -> str:

    datos = {
        "email": "Empresa@Servichile.cl",
        "nombre": "Proveedor Demo SpA",
        "password": "clave-segura-123",
        "perfil": {"tipo_cuenta": "proveedor"},
    }

    assert client.post("/v1/auth/registro", json=datos).status_code == 201

    r = client.post(
        "/v1/auth/login", json={"email": datos["email"], "password": datos["password"]}
    )

    return r.json()["access_token"]
