import logging

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, negocios, perfil, reporte, reservas

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="ServiChile API",
    version="0.1.0",
    description="Autenticación, marketplace B2B, Índice de Transparencia y reporte verificable.",
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

app.include_router(negocios.router)

app.include_router(reservas.router)

app.include_router(reporte.router)

_RUTAS_SILENCIOSAS = ("GET / ", "GET /json/version ")


class _FiltroAccessSilencioso(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:

        msg = record.getMessage()

        return not any((ruta in msg for ruta in _RUTAS_SILENCIOSAS))


logging.getLogger("uvicorn.access").addFilter(_FiltroAccessSilencioso())


@app.get("/", include_in_schema=False)
def raiz() -> dict[str, str]:

    return {"estado": "ok"}


@app.get("/json/version", include_in_schema=False)
def json_version() -> dict[str, str]:

    return {
        "Browser": "ServiChile",
        "Protocol-Version": "1.0",
        "webSocketDebuggerUrl": "",
    }


@app.get("/salud", tags=["Sistema"])
def salud() -> dict[str, str]:

    return {"estado": "ok"}
