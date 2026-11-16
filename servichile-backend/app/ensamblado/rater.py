"""Composición compartida del rater (API + background).

El resto de factories HTTP viven en ``app.api.dependencias``; aquí solo lo
que también arranca fuera de FastAPI (bucle de refresco).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from functools import lru_cache

from sqlalchemy.orm import Session

from app.configuracion import get_settings
from app.infraestructura.persistencia.modelos import get_sessionmaker
from app.infraestructura.persistencia.repositorios import NegocioRepository
from app.infraestructura.rater.adaptador import AdaptadorRater, RaterConfig
from app.dominio.puertos import AnalizadorDocEmpresa
from app.servicios.negocio import NegocioService

log = logging.getLogger(__name__)


@lru_cache
def get_evaluador_rater() -> AdaptadorRater:
    s = get_settings()
    return AdaptadorRater(
        RaterConfig(
            modo=s.rater_mode,
            app_env=s.app_env,
            chilecompra_ticket=s.chilecompra_ticket,
            chilecompra_mode=s.chilecompra_mode,
            google_places_api_key=s.google_places_api_key,
            places_mode=s.places_mode,
            budget_seconds=s.rater_budget_seconds,
        )
    )


def armar_negocio_service(
    session: Session,
    analizador_docs: AnalizadorDocEmpresa | None = None,
) -> NegocioService:
    """Única composición de NegocioService (API y background)."""
    return NegocioService(
        NegocioRepository(session),
        analizador_docs,
        get_evaluador_rater(),
    )


def _refrescar_lote() -> int:
    SessionLocal = get_sessionmaker()
    with SessionLocal() as session:
        return armar_negocio_service(session).refrescar_rater_todos()


async def bucle_rater(stop: asyncio.Event) -> None:
    settings = get_settings()
    minutos = float(settings.rater_refresh_minutes or 0)
    if settings.app_env == "test" or minutos <= 0:
        log.info(
            "Rater background desactivado (env=%s, minutos=%s).",
            settings.app_env,
            minutos,
        )
        return

    intervalo = max(60.0, minutos * 60.0)
    log.info("Rater background cada %.0f min.", minutos)

    try:
        n = await asyncio.to_thread(_refrescar_lote)
        log.info("Rater background inicial: %s empresas.", n)
    except Exception:
        log.exception("Rater background inicial falló.")

    while not stop.is_set():
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=intervalo)
        if stop.is_set():
            break
        try:
            n = await asyncio.to_thread(_refrescar_lote)
            log.info("Rater background: %s empresas refrescadas.", n)
        except Exception:
            log.exception("Rater background falló.")
