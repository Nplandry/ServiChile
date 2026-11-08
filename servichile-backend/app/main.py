"""Punto de entrada de la API de ServicIA."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, consultas, negocios, perfil, reservas
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="ServicIA API",
    version="0.1.0",
    description="Autenticación y asistente de orientación con IA basado en normativa oficial.",
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(perfil.router)
app.include_router(consultas.router)
app.include_router(negocios.router)
app.include_router(reservas.router)


@app.get("/salud", tags=["Sistema"])
def salud() -> dict[str, str]:
    return {"estado": "ok"}
