"""Reglas de acceso HTTP: qué tipo de cuenta puede hacer cada acción."""

from fastapi import HTTPException, status

from app.dominio.entidades import Usuario

from app.dominio.tipo_cuenta import es_proveedor, tipo_de_usuario

SOLO_PROVEEDOR = (
    "Solo una cuenta proveedor puede crear o reclamar fichas en el marketplace."
)


def exige_cuenta_proveedor(usuario: Usuario) -> None:

    if not es_proveedor(tipo_de_usuario(usuario)):

        raise HTTPException(status.HTTP_403_FORBIDDEN, SOLO_PROVEEDOR)
