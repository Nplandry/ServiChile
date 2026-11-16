"""Pasa entidades del dominio a las respuestas JSON de la API."""

from app.api.esquemas import (
    DocEmpresaMetaOut,
    DocEmpresaOut,
    PerfilOut,
    UsuarioOut,
)

from app.dominio.entidades import DocEmpresaVerificado, EstadoPasaporte, Usuario


def to_perfil_out(estado: EstadoPasaporte) -> PerfilOut:

    return PerfilOut(
        rut_verificado=estado.rut_verificado,
        telefono=estado.telefono,
        nivel_pasaporte=estado.nivel_pasaporte,
        estado_pasaporte=estado.estado_pasaporte,
        score_confiabilidad=estado.score_confiabilidad,
        biometria_verificada=estado.biometria_verificada,
        biometria_verificada_en=estado.biometria_verificada_en,
        biometria_retener_hasta=estado.biometria_retener_hasta,
        biometria_bytes=estado.biometria_bytes,
        cedula_verificada=estado.cedula_verificada,
        cedula_verificada_en=estado.cedula_verificada_en,
        cedula_retener_hasta=estado.cedula_retener_hasta,
        cedula_bytes=estado.cedula_bytes,
        cedula_score=estado.cedula_score,
        antecedentes_verificados=estado.antecedentes_verificados,
        antecedentes_verificados_en=estado.antecedentes_verificados_en,
        antecedentes_anotaciones=estado.antecedentes_anotaciones,
        antecedentes_score=estado.antecedentes_score,
        aval_verificado=estado.aval_verificado,
        aval_verificado_en=estado.aval_verificado_en,
        aval_score=estado.aval_score,
        aval_tipo=estado.aval_tipo,
        xp=estado.xp,
        nivel_xp=estado.nivel_xp,
        edad=estado.edad,
        tipo_cuenta=estado.tipo_cuenta,
    )


def to_usuario_out(usuario: Usuario, estado: EstadoPasaporte) -> UsuarioOut:

    return UsuarioOut(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        creado_en=usuario.creado_en,
        perfil=to_perfil_out(estado),
    )


def to_doc_empresa_out(resultado: DocEmpresaVerificado) -> DocEmpresaOut:
    from app.dominio.docs_empresa import MetaDocEmpresa

    docs: dict[str, DocEmpresaMetaOut] = {}
    for tipo, meta in (resultado.docs_empresa or {}).items():
        if isinstance(meta, MetaDocEmpresa):
            docs[str(tipo)] = DocEmpresaMetaOut.model_validate(meta.a_dict())
    return DocEmpresaOut(
        business_id=resultado.business_id,
        tipo=resultado.tipo,
        verificado=resultado.verificado,
        score=resultado.score,
        senales=list(resultado.senales),
        docs_empresa=docs,
        indice_transparencia=resultado.indice_transparencia,
        indice_pct=resultado.indice_pct,
        docs_verificados=resultado.docs_verificados,
        docs_total=resultado.docs_total,
        verificado_criptograficamente=resultado.verificado_criptograficamente,
        entidad_emisora=resultado.entidad_emisora,
        fecha_emision=resultado.fecha_emision,
        sha256_hash=resultado.sha256_hash,
        glosa=resultado.glosa,
        motivo=resultado.motivo,
    )
