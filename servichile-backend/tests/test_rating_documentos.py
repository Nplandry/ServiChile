from app.dominio.docs_empresa import TIPOS_DOC_EMPRESA, docs_empresa_desde_raw
from app.dominio.transparencia.rating import (
    calcular_indice,
    calcular_rating_documentos,
    observables_documentos,
    score_unificado,
)


def _docs(*tipos: str):
    return docs_empresa_desde_raw({t: {"verificado": True, "score": 100} for t in tipos})


def test_rating_sin_docs_es_cero():
    rating = calcular_rating_documentos(None)
    assert rating.verificados == 0
    assert rating.total == len(TIPOS_DOC_EMPRESA)
    assert rating.pct == 0
    assert rating.indice == 0.0
    assert calcular_indice(None) == 0.0
    assert calcular_rating_documentos(None) is calcular_rating_documentos({})


def test_rating_un_documento_pesa_igual():
    tipo = TIPOS_DOC_EMPRESA[0]
    rating = calcular_rating_documentos(_docs(tipo))
    esperado_pct = int(round(100.0 / len(TIPOS_DOC_EMPRESA)))
    esperado_indice = round(10.0 / len(TIPOS_DOC_EMPRESA), 1)
    assert rating.verificados == 1
    assert rating.pct == esperado_pct
    assert rating.indice == esperado_indice


def test_rating_todos_documentos_llega_a_100():
    completo = _docs(*TIPOS_DOC_EMPRESA)
    rating = calcular_rating_documentos(completo)
    assert rating.verificados == len(TIPOS_DOC_EMPRESA)
    assert rating.pct == 100
    assert rating.indice == 10.0
    assert calcular_rating_documentos(completo) is rating


def test_rating_ignora_docs_no_verificados():
    docs = docs_empresa_desde_raw(
        {
            TIPOS_DOC_EMPRESA[0]: {"verificado": False, "score": 40},
            TIPOS_DOC_EMPRESA[1]: {"verificado": True, "score": 90},
            "tipo_desconocido": {"verificado": True},
        }
    )
    rating = calcular_rating_documentos(docs)
    assert rating.verificados == 1


def test_score_unificado_junta_rater_y_docs():
    indice, pct = score_unificado(rater_pct=80, docs_pct=20)
    assert pct == 50
    assert indice == 5.0


def test_score_unificado_sin_docs_baja_el_indice():
    indice, pct = score_unificado(rater_pct=100, docs_pct=0)
    assert pct == 50
    assert indice == 5.0


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
