from fastapi import HTTPException, status

from app.domain.entidades import Usuario

from app.domain.tipo_cuenta import es_proveedor, tipo_de_usuario

SOLO_PROVEEDOR = (
    "Solo una cuenta proveedor puede crear o reclamar fichas en el marketplace."
)


def exige_cuenta_proveedor(usuario: Usuario) -> None:

    if not es_proveedor(tipo_de_usuario(usuario)):

        raise HTTPException(status.HTTP_403_FORBIDDEN, SOLO_PROVEEDOR)
