

from __future__ import annotations

import logging

from app.dominio.puertos import VerificadorIdentidad
from app.infraestructura.evaluador.chilecompra import ClienteChileCompra

log = logging.getLogger(__name__)

class MuestraVerificadorRut:

    def existe_y_activo(self, rut: str) -> bool:
        return bool((rut or "").strip())

class EstrictoVerificadorRut:

    def existe_y_activo(self, rut: str) -> bool:
        return False

class ChileCompraVerificadorRut:

    def __init__(self, ticket: str, *, tiempo_espera: float = 3.0) -> None:
        self.cliente = ClienteChileCompra(ticket)
        self.tiempo_espera = tiempo_espera
        self.ultimo_detalle: str | None = None

    def existe_y_activo(self, rut: str) -> bool:
        self.ultimo_detalle = None
        if not (rut or "").strip():
            self.ultimo_detalle = "RUT vacío"
            return False
        if not self.cliente.configurado:
            log.warning("ChileCompraVerificadorRut sin ticket; rechaza RUT.")
            self.ultimo_detalle = "CHILECOMPRA_TICKET no configurado"
            return False
        ok, data, err = self.cliente.buscar_proveedor(rut, tiempo_espera=self.tiempo_espera)
        if not ok:
            log.info("ChileCompra RUT %s: %s", rut, err)
            self.ultimo_detalle = err or "error al consultar Mercado Público"
            return False
        codigo = ClienteChileCompra.codigo_desde(data if isinstance(data, dict) else None)
        if not codigo:
            self.ultimo_detalle = (
                "el RUT no aparece como proveedor en Mercado Público"
            )
            return False
        return True

def construir_verificador_rut(
    nombre: str,
    *,
    app_env: str = "local",
    chilecompra_ticket: str = "",
) -> VerificadorIdentidad:
    modo = (nombre or "estricto").strip().lower()
    env = (app_env or "local").strip().lower()
    ticket = (chilecompra_ticket or "").strip()

    if modo == "muestra":
        if env in ("test", "local"):
            return MuestraVerificadorRut()
        log.warning(
            "Verificador 'muestra' fuera de APP_ENV=test|local: se usa estricto "
            "(no se marca identidad solo por dígito verificador)."
        )
        return EstrictoVerificadorRut()

    if modo == "estricto":
        return EstrictoVerificadorRut()

    if modo == "chilecompra":
        return ChileCompraVerificadorRut(ticket)

    raise ValueError(f"Verificador de RUT desconocido: {nombre}")

