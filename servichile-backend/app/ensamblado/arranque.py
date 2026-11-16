"""Precargas de arranque (fuera de servicios)."""

from __future__ import annotations

import logging

from app.configuracion import Settings
from app.infraestructura.trust_vault import (
    obtener_validation_context,
    ruta_ca_default,
)

log = logging.getLogger(__name__)


def precargar_pades_ca(settings: Settings) -> None:
    """Bóveda CA Chile en RAM al arrancar (offline, sin fetch)."""
    try:
        obtener_validation_context(str(settings.pades_ca_ruta()))
    except Exception:
        try:
            obtener_validation_context(str(ruta_ca_default()))
        except Exception:
            log.warning(
                "No se pudo precargar ca_chile.pem; se intentará en la primera validación PAdES."
            )
