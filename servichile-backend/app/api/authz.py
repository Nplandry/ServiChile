from fastapi import HTTPException, status
from app.domain.entidades import Usuario
SOLO_EMPRESA = 'Solo una cuenta empresa puede crear o reclamar fichas en el marketplace.'

def exige_cuenta_empresa(usuario: Usuario) -> None:
    tipo = usuario.perfil.tipo_cuenta if usuario.perfil else None
    if tipo != 'empresa':
        raise HTTPException(status.HTTP_403_FORBIDDEN, SOLO_EMPRESA)
