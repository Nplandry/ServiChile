"""Adaptadores de modelos de IA. Para cambiar de proveedor, agregue una clase que cumpla LLMProvider."""
import hashlib
import math
from typing import Protocol

from app.config import Settings


class LLMProvider(Protocol):
    def embed(self, textos: list[str], para_consulta: bool) -> list[list[float]]: ...

    def generate(self, instrucciones: str, prompt: str) -> str: ...


class GeminiProvider:
    """Gemini en Vertex AI. Autentica con las credenciales de la cuenta de servicio (ADC)."""

    def __init__(self, settings: Settings) -> None:
        import google.auth
        from google import genai

        proyecto = settings.gcp_project
        if not proyecto:
            raise RuntimeError("GCP_PROJECT es obligatorio cuando LLM_PROVIDER=gemini")
        if proyecto in settings.gcp_proyectos_prohibidos:
            raise RuntimeError(f"El proyecto {proyecto} está en GCP_PROYECTOS_PROHIBIDOS")
        # Las credenciales locales pueden traer otro proyecto de cuota, y el SDK lo envía en
        # x-goog-user-project. Se fuerza el de ServiChile para que ningún uso se cargue a otro proyecto.
        credenciales, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"], quota_project_id=proyecto
        )
        self._client = genai.Client(
            vertexai=True, project=proyecto, location=settings.gcp_location, credentials=credenciales
        )
        self._model = settings.gemini_model
        self._embedding_model = settings.embedding_model
        self._dim = settings.embedding_dim

    def embed(self, textos: list[str], para_consulta: bool) -> list[list[float]]:
        from google.genai import types

        config = types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY" if para_consulta else "RETRIEVAL_DOCUMENT",
            output_dimensionality=self._dim,
        )
        response = self._client.models.embed_content(model=self._embedding_model, contents=textos, config=config)
        return [list(e.values or []) for e in response.embeddings or []]

    def generate(self, instrucciones: str, prompt: str) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(system_instruction=instrucciones, temperature=0.2, max_output_tokens=1024)
        response = self._client.models.generate_content(model=self._model, contents=prompt, config=config)
        return (response.text or "").strip()


class FakeProvider:
    """Proveedor determinista para desarrollo y pruebas. No envía datos a ningún servicio externo."""

    def __init__(self, dim: int) -> None:
        self._dim = dim

    def embed(self, textos: list[str], para_consulta: bool) -> list[list[float]]:
        vectores = []
        for texto in textos:
            seed = hashlib.sha256(texto.encode()).digest()
            raw = [seed[i % len(seed)] - 127.5 for i in range(self._dim)]
            norma = math.sqrt(sum(v * v for v in raw)) or 1.0
            vectores.append([v / norma for v in raw])
        return vectores

    def generate(self, instrucciones: str, prompt: str) -> str:
        return "Respuesta de prueba basada en [1]. Configure LLM_PROVIDER=gemini para respuestas reales."


def build_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "gemini":
        return GeminiProvider(settings)
    return FakeProvider(settings.embedding_dim)
