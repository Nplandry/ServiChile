from datetime import datetime, timedelta, timezone

from app.dominio.docs_empresa import TIPOS_DOC_EMPRESA, docs_empresa_desde_raw
from app.dominio.transparencia.valoracion import (
    calcular_indice,
    calcular_valoracion_documentos,
    observables_documentos,
    score_unificado,
)

def _docs(*tipos: str):
    return docs_empresa_desde_raw({t: {"verificado": True, "score": 100} for t in tipos})

def test_rating_ignora_documento_caducado():
    tipo = TIPOS_DOC_EMPRESA[0]
    pasado = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    docs = docs_empresa_desde_raw(
        {
            tipo: {
                "verificado": True,
                "score": 100,
                "verificado_en": pasado,
                "vence_en": pasado,
            }
        }
    )
    rating = calcular_valoracion_documentos(docs)
    assert rating.verificados == 0
    assert rating.indice == 0.0

def test_rating_sin_docs_es_cero():
    rating = calcular_valoracion_documentos(None)
    assert rating.verificados == 0
    assert rating.total == len(TIPOS_DOC_EMPRESA)
    assert rating.pct == 0
    assert rating.indice == 0.0
    assert calcular_indice(None) == 0.0
    assert calcular_valoracion_documentos(None) is calcular_valoracion_documentos({})

def test_rating_un_documento_pesa_igual():
    tipo = TIPOS_DOC_EMPRESA[0]
    rating = calcular_valoracion_documentos(_docs(tipo))
    esperado_pct = int(round(100.0 / len(TIPOS_DOC_EMPRESA)))
    esperado_indice = round(10.0 / len(TIPOS_DOC_EMPRESA), 1)
    assert rating.verificados == 1
    assert rating.pct == esperado_pct
    assert rating.indice == esperado_indice

def test_rating_todos_documentos_llega_a_100():
    completo = _docs(*TIPOS_DOC_EMPRESA)
    rating = calcular_valoracion_documentos(completo)
    assert rating.verificados == len(TIPOS_DOC_EMPRESA)
    assert rating.pct == 100
    assert rating.indice == 10.0
    assert calcular_valoracion_documentos(completo) is rating

def test_rating_ignora_docs_no_verificados():
    docs = docs_empresa_desde_raw(
        {
            TIPOS_DOC_EMPRESA[0]: {"verificado": False, "score": 40},
            TIPOS_DOC_EMPRESA[1]: {"verificado": True, "score": 90},
            "tipo_desconocido": {"verificado": True},
        }
    )
    rating = calcular_valoracion_documentos(docs)
    assert rating.verificados == 1

def test_score_unificado_junta_evaluador_y_docs():
    indice, pct = score_unificado(pct_evaluador=80, docs_pct=20)
    assert pct == 50
    assert indice == 5.0

def test_score_unificado_sin_docs_baja_el_indice():
    indice, pct = score_unificado(pct_evaluador=100, docs_pct=0)
    assert pct == 50
    assert indice == 5.0

def test_teaser_publico_tres_senales():
    from app.dominio.entidades import ObservableSenal
    from app.dominio.transparencia.valoracion import teaser_observables_publico

    full = [
        ObservableSenal(
            id="fis_reviews",
            etiqueta="Cantidad de reseñas de clientes",
            detalle="",
            score=70,
            peso="1.0",
            grupo="operativa",
            razones=[],
        ),
        ObservableSenal(
            id="cyb_https",
            etiqueta="HTTPS",
            detalle="",
            score=100,
            peso="1.0",
            grupo="ciber",
            razones=[],
        ),
    ]
    teaser, restantes = teaser_observables_publico(full)
    assert [o.id for o in teaser] == [
        "doc_patente",
        "fis_reviews",
        "cyb_referrer",
    ]
    assert teaser[1].score == 70
    assert restantes >= 31

def test_observables_documentos_entran_al_desglose():
    docs = _docs(TIPOS_DOC_EMPRESA[0])
    obs = observables_documentos(docs)
    assert len(obs) == len(TIPOS_DOC_EMPRESA)
    assert obs[0].id == f"doc_{TIPOS_DOC_EMPRESA[0]}"
    assert obs[0].score == 100
    assert obs[0].grupo == "documentos"
    assert all(o.score in (0, 100) for o in obs)
    assert sum(1 for o in obs if o.score == 100) == 1

def test_documentos_van_primero_en_el_indice():
    docs = observables_documentos(_docs(TIPOS_DOC_EMPRESA[0]))
    assert docs[0].id.startswith("doc_")
    assert all(o.id.startswith("doc_") for o in docs)
