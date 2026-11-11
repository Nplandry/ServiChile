"""Casos de uso del Índice de Transparencia de negocios.

Obtiene la reputación estadística de un comercio, permite a su dueño reclamar el
perfil (Derecho a Réplica) y recalcula el índice con la fórmula ponderada del
dominio. No emite juicios de valor: solo combina métricas públicas.
"""
import uuid

from app.domain.entidades import (
    Metricas,
    Negocio,
    NegocioEnMapa,
    Reputacion,
    ResultadoReclamo,
)
from app.domain.marketplace import cta_texto, imagen_efectiva, logo_texto
from app.domain.reputacion import EntradaScore, calcular_indice
from app.infrastructure.repositories import NegocioRepository
from app.utils import ahora_utc

ESTADO_VERIFICADO = "Perfil Verificado"
ESTADO_NO_VERIFICADO = "Perfil No Verificado / Índice Básico"


class NegocioNoEncontrado(Exception):
    pass


class NegocioYaReclamado(Exception):
    pass


def recalcular_score(metricas: Metricas) -> float:
    """Aplica la fórmula del dominio y devuelve el índice (1.0 a 10.0)."""
    entrada = EntradaScore(
        google_rating_avg=metricas.google_rating_avg,
        google_reviews_count=metricas.google_reviews_count or 0,
        is_verified_profile=metricas.is_verified_profile,
    )
    return calcular_indice(entrada)


def _metricas_de(negocio: Negocio) -> Metricas:
    """Métricas del negocio; si no existen, las crea vacías en memoria."""
    if negocio.metricas is None:
        negocio.metricas = Metricas(
            business_id=negocio.id,
            google_reviews_count=0,
            final_score=0.0,
            is_verified_profile=False,
            actualizado_en=ahora_utc(),
        )
    return negocio.metricas


class NegocioService:
    def __init__(self, negocios: NegocioRepository) -> None:
        self.negocios = negocios

    def _buscar(self, business_id: uuid.UUID) -> Negocio:
        negocio = self.negocios.get(business_id)
        if negocio is None:
            raise NegocioNoEncontrado()
        return negocio

    def listar_para_mapa(self, categoria: str | None = None, q: str | None = None) -> list[NegocioEnMapa]:
        """Negocios para el marketplace, cada uno con su Índice de Transparencia."""
        salida: list[NegocioEnMapa] = []
        for negocio in self.negocios.listar(categoria, q):
            m = negocio.metricas
            if m is not None and m.final_score:
                indice = m.final_score
            elif m is not None:
                indice = recalcular_score(m)
            else:
                indice = 1.0
            salida.append(
                NegocioEnMapa(
                    id=negocio.id,
                    nombre=negocio.nombre,
                    categoria=negocio.categoria,
                    latitud=negocio.latitud,
                    longitud=negocio.longitud,
                    direccion=negocio.direccion,
                    descripcion=negocio.descripcion,
                    imagen_url=imagen_efectiva(negocio.imagen_url, negocio.categoria),
                    logo_url=negocio.logo_url,
                    logo_texto=logo_texto(negocio.nombre),
                    cta_texto=cta_texto(negocio.categoria),
                    indice_transparencia=indice,
                    is_verified_profile=bool(m and m.is_verified_profile),
                    requiere_nivel=negocio.requiere_nivel,
                )
            )
        return salida

    def obtener_reputacion(self, business_id: uuid.UUID) -> Reputacion:
        negocio = self._buscar(business_id)
        metricas = _metricas_de(negocio)
        # El índice guardado lo mantiene el worker; si falta (perfil recién creado),
        # se calcula al vuelo para no devolver un valor obsoleto.
        indice = metricas.final_score if metricas.final_score else recalcular_score(metricas)
        verificado = metricas.is_verified_profile
        return Reputacion(
            business_id=negocio.id,
            nombre=negocio.nombre,
            categoria=negocio.categoria,
            is_verified_profile=verificado,
            estado_perfil=ESTADO_VERIFICADO if verificado else ESTADO_NO_VERIFICADO,
            google_rating_avg=metricas.google_rating_avg,
            google_reviews_count=metricas.google_reviews_count or 0,
            sentiment_positive_ratio=metricas.sentiment_positive_ratio,
            response_time_score=metricas.response_time_score,
            indice_transparencia=indice,
            actualizado_en=metricas.actualizado_en,
        )

    def reclamar(
        self,
        business_id: uuid.UUID,
        usuario_id: uuid.UUID,
        nombre: str | None = None,
        telefono: str | None = None,
        sitio_web: str | None = None,
    ) -> ResultadoReclamo:
        negocio = self._buscar(business_id)
        if negocio.is_claimed:
            raise NegocioYaReclamado()

        negocio.is_claimed = True
        negocio.reclamado_por = usuario_id
        if nombre is not None:
            negocio.nombre = nombre
        if telefono is not None:
            negocio.telefono = telefono
        if sitio_web is not None:
            negocio.sitio_web = sitio_web

        metricas = _metricas_de(negocio)
        metricas.is_verified_profile = True
        metricas.final_score = recalcular_score(metricas)

        guardado = self.negocios.guardar(negocio)
        return ResultadoReclamo(
            business_id=guardado.id,
            is_claimed=guardado.is_claimed,
            is_verified_profile=bool(guardado.metricas and guardado.metricas.is_verified_profile),
            reclamado_por=usuario_id,
        )
