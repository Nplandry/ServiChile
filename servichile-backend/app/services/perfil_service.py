"""Escritura de los datos del perfil del usuario (edad y, durante la transición, los deprecados)."""
from app.domain.entidades import Perfil, Usuario

# Campos que viven en el perfil. RUT y teléfono viven en el usuario.
CAMPOS_PERFIL = {"edad", "tipo_cuenta", "preocupacion", "proposito"}


def aplicar_perfil(usuario: Usuario, cambios: dict) -> None:
    """Actualiza solo los campos recibidos. Un valor None borra el campo; uno ausente no cambia."""
    relevantes = {campo: valor for campo, valor in cambios.items() if campo in CAMPOS_PERFIL}
    if not relevantes:
        return
    if usuario.perfil is None:
        usuario.perfil = Perfil()
    for campo, valor in relevantes.items():
        setattr(usuario.perfil, campo, valor)
