"""Premios de experiencia del Pasaporte. Código puro: sin DB ni red.

Los eventos one-shot usan la clave fija. Los repetibles (p. ej. asistencia)
usan una clave con id: asistencia:<reserva_id>.
"""

# Premios por hitos ya implementados de punta a punta.
XP_REGISTRO = 10
XP_PERFIL_BASICO = 20  # edad + teléfono
XP_RUT = 50
XP_BIOMETRIA = 80
XP_ASISTENCIA = 25

EVENTO_REGISTRO = "registro"
EVENTO_PERFIL_BASICO = "perfil_basico"
EVENTO_RUT = "rut_verificado"
EVENTO_BIOMETRIA = "biometria"


def evento_asistencia(reserva_id: str) -> str:
    return f"asistencia:{reserva_id}"


def nivel_por_xp(xp: int) -> int:
    """Nivel de progreso 1–3 derivado del XP acumulado (UI Subir Confianza)."""
    if xp >= 250:
        return 3
    if xp >= 100:
        return 2
    return 1
