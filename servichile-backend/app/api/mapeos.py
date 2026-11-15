"""Pasa entidades del dominio a las respuestas JSON de la API."""

from app.api.esquemas import PerfilOut, UsuarioOut

from app.dominio.entidades import EstadoPasaporte, Usuario


def to_perfil_out(estado: EstadoPasaporte) -> PerfilOut:

    return PerfilOut(
        rut_verificado=estado.rut_verificado,
        telefono=estado.telefono,
        nivel_pasaporte=estado.nivel_pasaporte,
        estado_pasaporte=estado.estado_pasaporte,
        score_confiabilidad=estado.score_confiabilidad,
        biometria_verificada=estado.biometria_verificada,
        biometria_verificada_en=estado.biometria_verificada_en,
        antecedentes_verificados=estado.antecedentes_verificados,
        antecedentes_verificados_en=estado.antecedentes_verificados_en,
        antecedentes_anotaciones=estado.antecedentes_anotaciones,
        antecedentes_score=estado.antecedentes_score,
        xp=estado.xp,
        nivel_xp=estado.nivel_xp,
        edad=estado.edad,
        tipo_cuenta=estado.tipo_cuenta,
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
