from __future__ import annotations

import logging
import uuid

from app.dominio.docs_empresa import (
    DOCS_EMPRESA_MAX_BYTES,
    TIPOS_PDF,
    MetaDocEmpresa,
    ResultadoDocEmpresa,
    TipoDocEmpresa,
    es_tipo_doc_empresa,
)
from app.dominio.entidades import (
    DocEmpresaVerificado,
    Metricas,
    Negocio,
    NegocioEnMapa,
    NegocioTitular,
    Reputacion,
)
from app.dominio.errores import (
    DocEmpresaInvalido,
    DocEmpresaMuyGrande,
    NegocioNoEncontrado,
    NoEsTitularDelNegocio,
    RaterIndisponible,
)
from app.dominio.pasaporte import RutInvalido, normalizar_rut
from app.dominio.puertos import (
    AnalizadorDocEmpresa,
    EvaluadorRater,
    RepositorioNegocios,
)
from app.dominio.transparencia.rating import calcular_rating_documentos
from app.servicios.negocio_reputacion import (
    a_mapa,
    a_titular,
    aplicar_rating_docs,
    docs_copia,
    indice_global,
    metricas_de,
    persistir_indice,
    reputacion_de,
)
from app.servicios.pades_anti_replay import registrar_hash_unico
from app.tiempo import ahora_utc

log = logging.getLogger(__name__)

__all__ = [
    "NegocioService",
    "NegocioNoEncontrado",
    "NoEsTitularDelNegocio",
    "RaterIndisponible",
]


def rut_desde_documento(texto: str | None) -> str | None:
    if not texto or not str(texto).strip():
        return None
    try:
        return normalizar_rut(str(texto).strip())
    except RutInvalido:
        return None


def _texto_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    limpio = valor.strip()
    return limpio or None


class NegocioService:
    def __init__(
        self,
        negocios: RepositorioNegocios,
        analizador_docs: AnalizadorDocEmpresa | None = None,
        rater: EvaluadorRater | None = None,
    ) -> None:
        self.negocios = negocios
        self.analizador_docs = analizador_docs
        self.rater = rater

    def _buscar(self, business_id: uuid.UUID) -> Negocio:
        negocio = self.negocios.get(business_id)
        if negocio is None:
            raise NegocioNoEncontrado()
        return negocio

    def listar_para_mapa(
        self, categoria: str | None = None, q: str | None = None
    ) -> list[NegocioEnMapa]:
        return [a_mapa(n) for n in self.negocios.listar(categoria, q)]

    def listar_mios(self, usuario_id: uuid.UUID) -> list[NegocioTitular]:
        return [a_titular(n) for n in self.negocios.listar_de(usuario_id)]

    def obtener_reputacion(self, business_id: uuid.UUID) -> Reputacion:
        return reputacion_de(self._buscar(business_id))

    def respuesta_doc_empresa(
        self, negocio: Negocio, tipo: str, resultado: ResultadoDocEmpresa
    ) -> DocEmpresaVerificado:
        """Resultado de dominio tras upload (mapeo HTTP en la capa API)."""
        docs = docs_copia(negocio)
        rating = calcular_rating_documentos(docs)
        indice, pct = indice_global(metricas_de(negocio))
        return DocEmpresaVerificado(
            business_id=negocio.id,
            tipo=tipo,
            verificado=True,
            score=resultado.score,
            senales=tuple(resultado.senales),
            docs_empresa=docs,
            indice_transparencia=indice,
            indice_pct=pct,
            docs_verificados=rating.verificados,
            docs_total=rating.total,
            verificado_criptograficamente=bool(
                resultado.verificado_criptograficamente
            ),
            entidad_emisora=resultado.entidad_emisora,
            fecha_emision=resultado.fecha_emision,
            sha256_hash=resultado.sha256_hash,
            glosa=resultado.glosa,
            motivo=resultado.motivo
            or "Documento de empresa validado. El PDF no se almacenó.",
        )

    def _aplicar_rater(
        self, negocio: Negocio, *, exigir_rater: bool = False
    ) -> Negocio:
        """Evalúa el rater, junta documentos y persiste un solo índice."""
        if self.rater is None:
            if exigir_rater:
                raise RaterIndisponible("Evaluador de señales no disponible.")
            persistir_indice(negocio)
            return self.negocios.guardar(negocio)
        try:
            resultado = self.rater.evaluar(negocio)
        except Exception:
            log.exception("Rater falló para negocio %s", negocio.id)
            if exigir_rater:
                raise RaterIndisponible(
                    "Falló la evaluación de señales externas."
                ) from None
            persistir_indice(negocio)
            return self.negocios.guardar(negocio)
        observables = resultado.a_observables()
        metricas = metricas_de(negocio)
        overall = resultado.overall_score
        rater_pct = float(overall) if overall is not None else 0.0
        persistir_indice(negocio, senales=observables, rater_pct=rater_pct)
        metricas.rater_escaneado_en = ahora_utc()
        for obs in observables:
            if obs.id == "fis_rating" and obs.score > 0:
                metricas.google_rating_avg = round((obs.score / 100.0) * 5.0, 1)
            if obs.id == "fis_reviews" and obs.score > 0:
                metricas.google_reviews_count = max(
                    metricas.google_reviews_count or 0, int((obs.score - 20) / 2)
                )
        return self.negocios.guardar(negocio)

    def refrescar_rater(self, business_id: uuid.UUID) -> Negocio:
        return self._aplicar_rater(self._buscar(business_id))

    def refrescar_indice_titular(
        self, business_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> Reputacion:
        """Re-evalúa señales (titular). Falla visible si el rater no responde."""
        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        actualizado = self._aplicar_rater(negocio, exigir_rater=True)
        return reputacion_de(actualizado)

    def refrescar_rater_todos(self, limite: int = 500) -> int:
        n = 0
        for negocio in self.negocios.listar_completos(limite=limite):
            try:
                self._aplicar_rater(negocio)
                n += 1
            except Exception:
                log.exception(
                    "Rater background: fallo en negocio %s", negocio.id
                )
                continue
        return n

    def crear(
        self,
        usuario_id: uuid.UUID,
        *,
        nombre: str,
        categoria: str,
        direccion: str | None = None,
        descripcion: str | None = None,
        telefono: str | None = None,
        sitio_web: str | None = None,
        imagen_url: str | None = None,
        logo_url: str | None = None,
        rut_empresa: str | None = None,
    ) -> NegocioTitular:
        negocio_id = uuid.uuid4()
        negocio = Negocio(
            id=negocio_id,
            nombre=nombre.strip(),
            categoria=categoria,
            direccion=_texto_opcional(direccion),
            descripcion=_texto_opcional(descripcion),
            telefono=telefono,
            sitio_web=sitio_web,
            imagen_url=_texto_opcional(imagen_url),
            logo_url=_texto_opcional(logo_url),
            is_claimed=True,
            reclamado_por=usuario_id,
            rut_empresa=rut_desde_documento(rut_empresa),
            docs_empresa={},
            metricas=Metricas(
                business_id=negocio_id,
                google_reviews_count=0,
                final_score=0.0,
                actualizado_en=ahora_utc(),
            ),
        )
        guardado = self.negocios.guardar(negocio)
        guardado = self._aplicar_rater(guardado)
        return a_titular(guardado)

    def eliminar(self, business_id: uuid.UUID, usuario_id: uuid.UUID) -> None:
        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        self.negocios.eliminar(business_id)

    def actualizar_rut_empresa(
        self, business_id: uuid.UUID, usuario_id: uuid.UUID, rut: str
    ) -> NegocioTitular:
        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        normalizado = rut_desde_documento(rut)
        if not normalizado:
            raise DocEmpresaInvalido("RUT de empresa inválido.")
        negocio.rut_empresa = normalizado
        guardado = self.negocios.guardar(negocio)
        guardado = self._aplicar_rater(guardado)
        return a_titular(guardado)

    @staticmethod
    def _firma_rater(negocio: Negocio) -> tuple[str, ...]:
        """Campos que alimentan Places / crawler / ChileCompra / pesos."""
        return (
            (negocio.nombre or "").strip().casefold(),
            (negocio.categoria or "").strip().casefold(),
            (negocio.direccion or "").strip().casefold(),
            (negocio.telefono or "").strip(),
            (negocio.sitio_web or "").strip().casefold(),
            (negocio.rut_empresa or "").strip().upper(),
        )

    def actualizar(
        self,
        business_id: uuid.UUID,
        usuario_id: uuid.UUID,
        *,
        nombre: str,
        categoria: str,
        direccion: str | None = None,
        descripcion: str | None = None,
        telefono: str | None = None,
        sitio_web: str | None = None,
        imagen_url: str | None = None,
        logo_url: str | None = None,
        rut_empresa: str | None = None,
    ) -> NegocioTitular:
        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        firma_antes = self._firma_rater(negocio)
        negocio.nombre = nombre.strip()
        negocio.categoria = categoria
        negocio.direccion = _texto_opcional(direccion)
        negocio.descripcion = _texto_opcional(descripcion)
        negocio.telefono = telefono
        negocio.sitio_web = sitio_web
        negocio.imagen_url = _texto_opcional(imagen_url)
        negocio.logo_url = _texto_opcional(logo_url)
        if rut_empresa is not None and str(rut_empresa).strip():
            normalizado = rut_desde_documento(rut_empresa)
            if not normalizado:
                raise DocEmpresaInvalido("RUT de empresa inválido.")
            negocio.rut_empresa = normalizado
        guardado = self.negocios.guardar(negocio)
        if self._firma_rater(guardado) != firma_antes:
            guardado = self._aplicar_rater(guardado)
        else:
            persistir_indice(guardado)
            guardado = self.negocios.guardar(guardado)
        return a_titular(guardado)

    def eliminar_todos_del_usuario(self, usuario_id: uuid.UUID) -> None:
        self.negocios.eliminar_de(usuario_id)

    def _aplicar_resultado_doc(
        self,
        negocio: Negocio,
        tipo_doc: TipoDocEmpresa,
        resultado: ResultadoDocEmpresa,
        *,
        usuario_id: uuid.UUID,
    ) -> Negocio:
        registrar_hash_unico(
            self.negocios,
            resultado.sha256_hash,
            scope="empresa",
            tipo=tipo_doc,
            usuario_id=usuario_id,
            business_id=negocio.id,
            al_rechazar=lambda: DocEmpresaInvalido(
                "Este documento (hash) ya fue utilizado. No se admite reutilizar el mismo PDF."
            ),
        )
        docs = docs_copia(negocio)
        meta = MetaDocEmpresa(
            verificado=True,
            score=resultado.score,
            senales=list(resultado.senales),
            verificado_en=ahora_utc().isoformat(),
            rut_detectado=resultado.rut_detectado,
            grupo=resultado.grupo,
        )
        if resultado.verificado_criptograficamente:
            meta.verificado_criptograficamente = True
            meta.entidad_emisora = resultado.entidad_emisora
            meta.fecha_emision = resultado.fecha_emision
            meta.sha256_hash = resultado.sha256_hash
            meta.glosa = resultado.glosa
            meta.documento_tipo = tipo_doc.upper()
        docs[tipo_doc] = meta
        negocio.docs_empresa = docs
        aplicar_rating_docs(negocio)
        return self.negocios.guardar(negocio)

    def procesar_doc_empresa(
        self,
        business_id: uuid.UUID,
        usuario_id: uuid.UUID,
        tipo: str,
        contenido: bytes,
        nombre_archivo: str | None = None,
    ) -> tuple[Negocio, ResultadoDocEmpresa]:
        if not es_tipo_doc_empresa(tipo) or tipo not in TIPOS_PDF:
            raise DocEmpresaInvalido(
                "Tipo PDF inválido. Use los documentos Grupo 1/2 (PDF textual)."
            )
        if self.analizador_docs is None:
            raise DocEmpresaInvalido(
                "Analizador de documentos de empresa no disponible."
            )
        if len(contenido) > DOCS_EMPRESA_MAX_BYTES:
            raise DocEmpresaMuyGrande("El PDF supera el tamaño máximo de 8 MB.")
        if not contenido.startswith(b"%PDF"):
            raise DocEmpresaInvalido(
                "Solo se acepta PDF con texto real. No se admiten fotos ni imágenes."
            )

        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()

        tipo_doc: TipoDocEmpresa = tipo  # type: ignore[assignment]
        resultado = self.analizador_docs.analizar(
            contenido,
            tipo=tipo_doc,
            rut_empresa=negocio.rut_empresa,
            nombre_empresa=negocio.nombre,
            nombre_archivo=nombre_archivo,
        )
        if not resultado.aceptado:
            raise DocEmpresaInvalido(resultado.motivo)

        return (
            self._aplicar_resultado_doc(
                negocio, tipo_doc, resultado, usuario_id=usuario_id
            ),
            resultado,
        )
