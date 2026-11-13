from __future__ import annotations
import uuid
from app.domain.ciber_metricas import metricas_necesitan_escaneo, observables_desde_metricas, volcar_scores_en_metricas
from app.domain.entidades import Metricas, Negocio, NegocioEnMapa, Reputacion, ResultadoReclamo
from app.domain.errores import NegocioNoEncontrado, NegocioYaReclamado, NoEsTitularDelNegocio
from app.domain.marketplace import cta_texto, imagen_efectiva, logo_texto
from app.domain.reputacion import EntradaScore, calcular_indice
from app.infrastructure.ciber_sonda import CiberSonda, FakeCiberSonda
from app.infrastructure.repositories import NegocioRepository
from app.utils import ahora_utc
ESTADO_VERIFICADO = 'Perfil Verificado'
ESTADO_NO_VERIFICADO = 'Perfil No Verificado / Índice Básico'
__all__ = ['NegocioService', 'NegocioNoEncontrado', 'NegocioYaReclamado', 'NoEsTitularDelNegocio', 'recalcular_score']

def recalcular_score(metricas: Metricas) -> float:
    return calcular_indice(EntradaScore(google_rating_avg=metricas.google_rating_avg, google_reviews_count=metricas.google_reviews_count or 0, is_verified_profile=metricas.is_verified_profile))

def _metricas_de(negocio: Negocio) -> Metricas:
    if negocio.metricas is None:
        negocio.metricas = Metricas(business_id=negocio.id, google_reviews_count=0, final_score=0.0, is_verified_profile=False, actualizado_en=ahora_utc())
    return negocio.metricas

def _indice_de(negocio: Negocio) -> float:
    m = negocio.metricas
    if m is None:
        return 1.0
    if m.final_score:
        return m.final_score
    return recalcular_score(m)

def _texto_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    limpio = valor.strip()
    return limpio or None

def _a_mapa(negocio: Negocio, *, forzar_claimed: bool | None=None) -> NegocioEnMapa:
    m = negocio.metricas
    claimed = bool(negocio.is_claimed) if forzar_claimed is None else forzar_claimed
    return NegocioEnMapa(id=negocio.id, nombre=negocio.nombre, categoria=negocio.categoria, latitud=negocio.latitud, longitud=negocio.longitud, direccion=negocio.direccion, descripcion=negocio.descripcion, imagen_url=imagen_efectiva(negocio.imagen_url, negocio.categoria), logo_url=negocio.logo_url, logo_texto=logo_texto(negocio.nombre), cta_texto=cta_texto(negocio.categoria), indice_transparencia=_indice_de(negocio), is_verified_profile=bool(m and m.is_verified_profile), requiere_nivel=negocio.requiere_nivel, is_claimed=claimed)

def _quitar_titularidad(negocio: Negocio) -> None:
    negocio.is_claimed = False
    negocio.reclamado_por = None
    metricas = _metricas_de(negocio)
    metricas.is_verified_profile = False
    metricas.final_score = recalcular_score(metricas)

def _aplicar_sonda(metricas: Metricas, sonda: CiberSonda, sitio_web: str | None) -> None:
    volcar_scores_en_metricas(metricas, sonda.escanear(sitio_web).scores, ahora_utc())

def _reputacion_de(negocio: Negocio) -> Reputacion:
    metricas = _metricas_de(negocio)
    verificado = metricas.is_verified_profile
    return Reputacion(business_id=negocio.id, nombre=negocio.nombre, categoria=negocio.categoria, is_verified_profile=verificado, estado_perfil=ESTADO_VERIFICADO if verificado else ESTADO_NO_VERIFICADO, google_rating_avg=metricas.google_rating_avg, google_reviews_count=metricas.google_reviews_count or 0, sentiment_positive_ratio=metricas.sentiment_positive_ratio, response_time_score=metricas.response_time_score, indice_transparencia=_indice_de(negocio), actualizado_en=metricas.actualizado_en, observables_ciber=observables_desde_metricas(metricas))

class NegocioService:

    def __init__(self, negocios: NegocioRepository, ciber_sonda: CiberSonda | None=None) -> None:
        self.negocios = negocios
        self.ciber_sonda = ciber_sonda or FakeCiberSonda()

    def _buscar(self, business_id: uuid.UUID) -> Negocio:
        negocio = self.negocios.get(business_id)
        if negocio is None:
            raise NegocioNoEncontrado()
        return negocio

    def listar_para_mapa(self, categoria: str | None=None, q: str | None=None) -> list[NegocioEnMapa]:
        return [_a_mapa(n) for n in self.negocios.listar(categoria, q)]

    def listar_mios(self, usuario_id: uuid.UUID) -> list[NegocioEnMapa]:
        return [_a_mapa(n, forzar_claimed=True) for n in self.negocios.listar_reclamados_por(usuario_id)]

    def obtener_reputacion(self, business_id: uuid.UUID) -> Reputacion:
        negocio = self._buscar(business_id)
        metricas = _metricas_de(negocio)
        if metricas_necesitan_escaneo(metricas):
            _aplicar_sonda(metricas, self.ciber_sonda, negocio.sitio_web)
            self.negocios.guardar(negocio)
        return _reputacion_de(negocio)

    def escanear_ciber(self, business_id: uuid.UUID, usuario_id: uuid.UUID) -> Reputacion:
        negocio = self._buscar(business_id)
        if not negocio.is_claimed or negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        metricas = _metricas_de(negocio)
        _aplicar_sonda(metricas, self.ciber_sonda, negocio.sitio_web)
        self.negocios.guardar(negocio)
        return _reputacion_de(negocio)

    def crear(self, usuario_id: uuid.UUID, *, nombre: str, categoria: str, direccion: str | None=None, descripcion: str | None=None, telefono: str | None=None, sitio_web: str | None=None, imagen_url: str | None=None, logo_url: str | None=None) -> NegocioEnMapa:
        negocio_id = uuid.uuid4()
        metricas = Metricas(business_id=negocio_id, google_reviews_count=0, final_score=0.0, is_verified_profile=True, actualizado_en=ahora_utc())
        metricas.final_score = recalcular_score(metricas)
        negocio = Negocio(id=negocio_id, nombre=nombre.strip(), categoria=categoria, direccion=_texto_opcional(direccion), descripcion=_texto_opcional(descripcion), telefono=telefono, sitio_web=sitio_web, imagen_url=_texto_opcional(imagen_url), logo_url=_texto_opcional(logo_url), is_claimed=True, reclamado_por=usuario_id, metricas=metricas)
        return _a_mapa(self.negocios.guardar(negocio), forzar_claimed=True)

    def reclamar(self, business_id: uuid.UUID, usuario_id: uuid.UUID, nombre: str | None=None, telefono: str | None=None, sitio_web: str | None=None) -> ResultadoReclamo:
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
        metricas.ciber_escaneado_en = None
        guardado = self.negocios.guardar(negocio)
        return ResultadoReclamo(business_id=guardado.id, is_claimed=guardado.is_claimed, is_verified_profile=bool(guardado.metricas and guardado.metricas.is_verified_profile), reclamado_por=usuario_id)

    def liberar(self, business_id: uuid.UUID, usuario_id: uuid.UUID) -> None:
        negocio = self._buscar(business_id)
        if not negocio.is_claimed or negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        _quitar_titularidad(negocio)
        self.negocios.guardar(negocio)

    def liberar_todos_del_usuario(self, usuario_id: uuid.UUID) -> None:
        for negocio in self.negocios.listar_reclamados_por(usuario_id):
            _quitar_titularidad(negocio)
            self.negocios.guardar(negocio)
