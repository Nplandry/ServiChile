"""Utilidades compartidas, sin dependencias de otras capas."""
from datetime import UTC, datetime


def ahora_utc() -> datetime:
    """Hora actual con zona horaria UTC. Fuente única para timestamps."""
    return datetime.now(UTC)
