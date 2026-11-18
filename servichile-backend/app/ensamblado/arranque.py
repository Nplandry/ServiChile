"""Precargas de arranque (fuera de servicios)."""

from __future__ import annotations

import logging

from app.configuracion import Configuracion
from app.infraestructura.trust_vault import (
    obtener_contexto_validacion,
    ruta_ca_default,
)

log = logging.getLogger(__name__)


def precargar_pades_ca(config: Configuracion) -> None:
    """Bóveda CA Chile en RAM al arrancar (sin red; sin descarga remota)."""
    try:
        obtener_contexto_validacion(str(config.pades_ca_ruta()))
    except Exception:
        try:
            obtener_contexto_validacion(str(ruta_ca_default()))
        except Exception:
            log.warning(
                "No se pudo precargar ca_chile.pem; se intentará en la primera validación PAdES."
            )
