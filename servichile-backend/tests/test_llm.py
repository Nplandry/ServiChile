"""El proveedor Gemini debe cargar todo el uso al proyecto de ServicIA, nunca al de las credenciales locales."""
import google.auth
import pytest
from google import genai

from app.config import get_settings
from app.infrastructure.llm import GeminiProvider


class CredencialesFalsas:
    def __init__(self, quota_project_id):
        self.quota_project_id = quota_project_id


@pytest.fixture
def capturado(monkeypatch):
    datos = {}

    def default(scopes=None, quota_project_id=None, **_):
        datos["quota_pedido"] = quota_project_id
        return CredencialesFalsas(quota_project_id or "proyecto-ajeno-de-las-credenciales"), None

    def client(**kwargs):
        datos["client"] = kwargs
        return object()

    monkeypatch.setattr(google.auth, "default", default)
    monkeypatch.setattr(genai, "Client", client)
    return datos


def _settings(**cambios):
    base = {"llm_provider": "gemini", "gcp_project": "servicia-dev", "gcp_proyectos_prohibidos": ["prohibido-cl"]}
    return get_settings().model_copy(update={**base, **cambios})


def test_fuerza_el_proyecto_de_cuota_de_servicia(capturado):
    GeminiProvider(_settings())
    assert capturado["quota_pedido"] == "servicia-dev"
    assert capturado["client"]["credentials"].quota_project_id == "servicia-dev"
    assert capturado["client"]["project"] == "servicia-dev"


def test_rechaza_proyecto_prohibido(capturado):
    with pytest.raises(RuntimeError, match="prohibido-cl"):
        GeminiProvider(_settings(gcp_project="prohibido-cl"))
    assert "client" not in capturado


def test_exige_proyecto(capturado):
    with pytest.raises(RuntimeError, match="GCP_PROJECT"):
        GeminiProvider(_settings(gcp_project=None))


def test_lista_de_prohibidos_desde_variable_de_entorno(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("GCP_PROYECTOS_PROHIBIDOS", "uno-cl, dos-cl")
    assert Settings().gcp_proyectos_prohibidos == ["uno-cl", "dos-cl"]
