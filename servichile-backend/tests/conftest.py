"""Pruebas sin PostgreSQL ni Vertex AI: SQLite en memoria y proveedor de IA falso."""
import os

os.environ.setdefault("JWT_SECRET", "test-secret-de-al-menos-32-caracteres-xx")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LLM_PROVIDER", "fake")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.infrastructure.db import Base, get_session
from app.infrastructure.rate_limit import MemoryRateLimiter
from app.infrastructure.repositories import FragmentoRecuperado
from app.main import app


class FakeFragmentos:
    def __init__(self) -> None:
        self.resultados: list[FragmentoRecuperado] = [
            FragmentoRecuperado(
                contenido="Las empresas deben contar con el consentimiento expreso del consumidor.",
                titulo="Ley 19.496",
                url="https://www.bcn.cl/leychile",
                pagina=12,
                distancia=0.1,
            )
        ]
        self.ultima_categoria: str | None = None

    def buscar(self, embedding, k, max_distancia, categoria):
        self.ultima_categoria = categoria
        return self.resultados


@pytest.fixture
def fragmentos() -> FakeFragmentos:
    return FakeFragmentos()


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(
        engine,
        tables=[
            Base.metadata.tables[t]
            for t in (
                "usuarios",
                "usuario_xp_eventos",
                "perfiles",
                "consultas",
                "business_entities",
                "business_reputation_metrics",
                "reservas",
                "pasaporte_arriendo",
            )
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def client(fragmentos: FakeFragmentos, session_factory):
    def _session():
        with session_factory() as s:
            yield s

    limiter = MemoryRateLimiter()
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[deps.get_fragmento_repo] = lambda: fragmentos
    app.dependency_overrides[deps.get_rate_limiter] = lambda: limiter
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def token(client: TestClient) -> str:
    datos = {"email": "Maria@Servichile.cl", "nombre": "María González", "password": "clave-segura-123", "perfil": {"tipo_cuenta": "persona"}}
    assert client.post("/v1/auth/registro", json=datos).status_code == 201
    r = client.post("/v1/auth/login", json={"email": datos["email"], "password": datos["password"]})
    return r.json()["access_token"]
