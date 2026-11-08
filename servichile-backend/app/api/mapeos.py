"""Conversión de entidades y resultados del dominio a schemas de respuesta de la API.

Único lugar donde se decide qué datos sale hacia el cliente.
"""
from app.api.schemas import InmobiliariaScoring, PerfilOut, UsuarioOut
from app.domain.entidades import EstadoPasaporte, Usuario, VerificacionArriendo


def _inmobiliaria(arriendo: VerificacionArriendo | None) -> InmobiliariaScoring | None:
    if arriendo is None:
        return None
    return InmobiliariaScoring(
        estado_verificacion=arriendo.estado,
        score_financiero=arriendo.score,
        actualizado_en=arriendo.verificado_en or arriendo.creado_en,
    )


def to_perfil_out(estado: EstadoPasaporte) -> PerfilOut:
    return PerfilOut(
        rut_verificado=estado.rut_verificado,
        telefono=estado.telefono,
        nivel_pasaporte=estado.nivel_pasaporte,
        estado_pasaporte=estado.estado_pasaporte,
        score_confiabilidad=estado.score_confiabilidad,
        inmobiliaria_scoring=_inmobiliaria(estado.arriendo),
        edad=estado.edad,
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
