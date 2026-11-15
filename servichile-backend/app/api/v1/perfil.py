from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from starlette.concurrency import run_in_threadpool

from app.api.dependencias import (
    CurrentUserDep,
    PasaporteServiceDep,
    RateLimiterDep,
    demasiadas_solicitudes,
)

from app.api.mapeos import to_perfil_out

from app.api.esquemas import AntecedentesOut, BiometriaOut, PerfilIn, PerfilOut

from app.dominio.antecedentes import ANTECEDENTES_MAX_BYTES

from app.dominio.errores import (
    AntecedentesInvalido,
    AntecedentesMuyGrande,
    BiometriaInvalida,
    BiometriaMuyGrande,
    RutEnUso,
    RutRechazado,
    RutYaVerificado,
)

from app.servicios.pasaporte import BIOMETRIA_MAX_BYTES

router = APIRouter(prefix="/v1/perfil", tags=["Perfil"])

BIOMETRIA_POR_MINUTO = 10

ANTECEDENTES_POR_MINUTO = 10


@router.get("", response_model=PerfilOut)
def ver_perfil(usuario: CurrentUserDep, servicio: PasaporteServiceDep):

    return to_perfil_out(servicio.estado(usuario))


@router.patch("", response_model=PerfilOut)
def actualizar_perfil(
    datos: PerfilIn, usuario: CurrentUserDep, servicio: PasaporteServiceDep
):

    cambios = datos.model_dump(exclude_unset=True)

    try:

        actualizado = servicio.actualizar_perfil(usuario, cambios)

    except RutRechazado as error:

        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None

    except (RutEnUso, RutYaVerificado) as error:

        raise HTTPException(status.HTTP_409_CONFLICT, error.mensaje) from None

    return to_perfil_out(servicio.estado(actualizado))


@router.post(
    "/biometria", response_model=BiometriaOut, status_code=status.HTTP_201_CREATED
)
async def verificar_biometria(
    usuario: CurrentUserDep,
    servicio: PasaporteServiceDep,
    limiter: RateLimiterDep,
    foto: Annotated[
        UploadFile, File(description="Selfie o foto de identidad; no se almacena")
    ],
):

    if not limiter.allow(f"biometria:{usuario.id}", BIOMETRIA_POR_MINUTO):

        raise demasiadas_solicitudes()

    contenido = await foto.read(BIOMETRIA_MAX_BYTES + 1)

    try:

        actualizado = await run_in_threadpool(
            servicio.procesar_biometria, usuario, contenido
        )

    except BiometriaMuyGrande as error:

        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, error.mensaje) from None

    except BiometriaInvalida as error:

        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None

    finally:

        del contenido

    estado = servicio.estado(actualizado)

    return BiometriaOut(
        biometria_verificada=actualizado.biometria_verificada,
        biometria_verificada_en=actualizado.biometria_verificada_en,
        xp=estado.xp,
        nivel_xp=estado.nivel_xp,
    )


@router.post(
    "/antecedentes", response_model=AntecedentesOut, status_code=status.HTTP_201_CREATED
)
async def verificar_antecedentes(
    usuario: CurrentUserDep,
    servicio: PasaporteServiceDep,
    limiter: RateLimiterDep,
    archivo: Annotated[
        UploadFile,
        File(description="PDF del certificado de antecedentes; no se almacena"),
    ],
    nombre_archivo: Annotated[str | None, Form()] = None,
):

    if not limiter.allow(f"antecedentes:{usuario.id}", ANTECEDENTES_POR_MINUTO):

        raise demasiadas_solicitudes()

    contenido = await archivo.read(ANTECEDENTES_MAX_BYTES + 1)

    nombre = (nombre_archivo or archivo.filename or "").strip() or None

    try:

        actualizado, resultado = await run_in_threadpool(
            servicio.procesar_antecedentes, usuario, contenido, nombre
        )

    except AntecedentesMuyGrande as error:

        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, error.mensaje) from None

    except AntecedentesInvalido as error:

        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None

    finally:

        del contenido

    estado = servicio.estado(actualizado)

    return AntecedentesOut(
        antecedentes_verificados=actualizado.antecedentes_verificados,
        antecedentes_verificados_en=actualizado.antecedentes_verificados_en,
        antecedentes_anotaciones=actualizado.antecedentes_anotaciones,
        antecedentes_score=actualizado.antecedentes_score,
        xp=estado.xp,
        nivel_xp=estado.nivel_xp,
        senales=list(resultado.senales),
        motivo=resultado.motivo,
    )
