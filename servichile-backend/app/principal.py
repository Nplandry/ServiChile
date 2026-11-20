import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1 import autenticacion, negocios, pagos, perfil, radar, reporte, trabajos

from app.configuracion import obtener_configuracion
from app.ensamblado.arranque import (
    precargar_pades_ca,
    verificar_compras_publicacion,
    verificar_entorno_produccion,
    verificar_fks_compras_informe,
    verificar_redis,
)
from app.ensamblado.evaluador import bucle_evaluador
from app.ensamblado.pagos import bucle_reconciliar_pagos

settings = obtener_configuracion()
verificar_entorno_produccion(settings)
precargar_pades_ca(settings)
verificar_fks_compras_informe(settings)
verificar_compras_publicacion(settings)
verificar_redis(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from contextlib import suppress

    stop = asyncio.Event()
    tarea_eval = asyncio.create_task(
        bucle_evaluador(stop), name="evaluador-segundo-plano"
    )
    tarea_pagos = asyncio.create_task(
        bucle_reconciliar_pagos(stop), name="pagos-reconciliar-tbk"
    )
    try:
        yield
    finally:
        stop.set()
        for tarea in (tarea_eval, tarea_pagos):
            tarea.cancel()
            with suppress(asyncio.CancelledError):
                await tarea


app = FastAPI(
    title="ServiChile API",
    version="0.1.0",
    description="Autenticación, marketplace B2B, Índice de Transparencia y reporte verificable.",
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(GZipMiddleware, minimum_size=800)

app.include_router(autenticacion.router)

app.include_router(perfil.router)

app.include_router(negocios.router)

app.include_router(trabajos.router)

app.include_router(trabajos.titular_router)

app.include_router(reporte.router)
app.include_router(radar.router_radar)
app.include_router(pagos.router)
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
def salud() -> dict:
    from app.ensamblado import evaluador_estado, pagos_estado

    ev = evaluador_estado.snapshot()
    pg = pagos_estado.snapshot()
    ok = bool(ev.get("ok", True)) and bool(pg.get("ok", True))
    return {
        "estado": "ok" if ok else "degradado",
        "evaluador": ev,
        "pagos_reconciliar": pg,
    }
