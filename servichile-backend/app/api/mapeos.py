"""Conversión de entidades y resultados del dominio a schemas de respuesta de la API.

Único lugar donde se decide qué datos sale hacia el cliente.
"""
from app.api.schemas import PerfilOut, UsuarioOut
from app.domain.entidades import EstadoPasaporte, Usuario


def to_perfil_out(estado: EstadoPasaporte) -> PerfilOut:
    return PerfilOut(
        rut_verificado=estado.rut_verificado,
        telefono=estado.telefono,
        nivel_pasaporte=estado.nivel_pasaporte,  # type: ignore[arg-type]
        estado_pasaporte=estado.estado_pasaporte,  # type: ignore[arg-type]
        score_confiabilidad=estado.score_confiabilidad,
        biometria_verificada=estado.biometria_verificada,
        biometria_verificada_en=estado.biometria_verificada_en,
        xp=estado.xp,
        nivel_xp=estado.nivel_xp,
        edad=estado.edad,
        tipo_cuenta=estado.tipo_cuenta,  # type: ignore[arg-type]
        # DEPRECADOS: no se devuelven.
        preocupacion=None,
        proposito=None,
    )


def to_usuario_out(usuario: Usuario, estado: EstadoPasaporte) -> UsuarioOut:
    return UsuarioOut(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        creado_en=usuario.creado_en,
        perfil=to_perfil_out(estado),
    )
