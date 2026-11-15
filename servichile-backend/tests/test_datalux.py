import uuid

from app.dominio.entidades import Metricas
from app.dominio.puertos import NuloSondaCiber
from app.dominio.transparencia.datalux import (
    SCORE_BASE,
    SCORE_MATCH,
    ActividadEconomica,
    FichaDatalux,
    evaluar_match,
    score_domicilio,
    score_huella_digital,
    score_persona_juridica,
    scores_desde_ficha,
)
from app.dominio.transparencia.metricas import necesita_datalux, necesita_extensiones
from app.servicios.completar_metricas import completar_metricas


class _DataluxFijo:
    def __init__(self, ficha: FichaDatalux | None) -> None:
        self.ficha = ficha
        self.consultas: list[str | None] = []

    def consultar(self, consulta: str | None) -> FichaDatalux | None:
        self.consultas.append(consulta)
        return self.ficha


def test_sin_ficha_parte_en_50():
    h = evaluar_match(nombre="Acme", direccion="Santiago", rut_empresa="76123456-7", ficha=None)
    assert score_domicilio(h) == SCORE_BASE
    assert score_huella_digital(h) == SCORE_BASE
    assert score_persona_juridica(None) == 0


def test_sin_rut_no_sube_aunque_haya_ficha():
    ficha = FichaDatalux(
        nombre="Gearlabs SpA",
        rut="76.123.456-7",
        estado="Vigente",
        direccion="Av. Apoquindo 3000",
        comuna="Las Condes",
    )
    out = scores_desde_ficha(
        nombre="Gearlabs SpA",
        direccion="Av. Apoquindo 3000, Las Condes",
        rut_empresa=None,
        ficha=ficha,
    )
    assert out.domicilio == SCORE_BASE
    assert out.huella_digital == SCORE_BASE


def test_rut_distinto_no_da_100_huella():
    ficha = FichaDatalux(
        nombre="Gearlabs SpA",
        rut="76.123.456-7",
        estado="Vigente",
        direccion="Av. Apoquindo 3000",
        comuna="Las Condes",
    )
    h = evaluar_match(
        nombre="Gearlabs SpA",
        direccion="Av. Apoquindo 3000, Las Condes",
        rut_empresa="99999999-9",
        ficha=ficha,
    )
    assert not h.rut_coincide
    assert score_huella_digital(h) == SCORE_BASE


def test_match_estricto_sube_a_100():
    ficha = FichaDatalux(
        nombre="Gearlabs SpA",
        rut="76.123.456-7",
        estado="Vigente",
        direccion="Av. Apoquindo 3000",
        comuna="Las Condes",
        anio_inicio="2018",
        actividades_economicas=(
            ActividadEconomica(nombre="Desarrollo de software", fecha_inicio="01-01-2018"),
        ),
    )
    out = scores_desde_ficha(
        nombre="Gearlabs SpA",
        direccion="Av. Apoquindo 3000, Las Condes",
        rut_empresa="76123456-7",
        ficha=ficha,
    )
    assert out.domicilio == SCORE_MATCH
    assert out.huella_digital == SCORE_MATCH
    assert out.persona_juridica == 100
    assert out.razones["domicilio"]
    assert out.razones["huella-digital"]
    assert out.razones["persona-juridica"]


def test_vigencia_penaliza_quiebra():
    ficha = FichaDatalux(
        nombre="X SpA",
        rut="76123456-7",
        estado="Vigente",
        resumen="Empresa en quiebra declarada",
        anio_inicio="2010",
        actividades_economicas=(ActividadEconomica(nombre="Comercio"),),
    )
    assert score_persona_juridica(ficha) == 60


def test_estado_vacio_no_simula_activa():
    ficha = FichaDatalux(nombre="X", rut="76123456-7", estado="", direccion="Calle 1")
    h = evaluar_match(
        nombre="X", direccion="Calle 1", rut_empresa="76123456-7", ficha=ficha
    )
    assert not h.empresa_activa
    assert score_huella_digital(h) == SCORE_BASE
    assert score_persona_juridica(ficha) == 20


def test_peso_2_por_ciento_efecto_98():
    assert round(0.96 * 100 + 0.02 * 50 + 0.02 * 50, 1) == 98.0


def test_necesita_datalux_independiente_de_extensiones():
    m = Metricas(
        business_id=uuid.uuid4(),
        score_mercado_publico=80,
        score_sii=80,
        score_cmf=80,
        score_incidentes=100,
        incidentes_razones=["ok"],
    )
    assert not necesita_extensiones(m)
    assert necesita_datalux(m)


def test_completar_metricas_aplica_match_datalux():
    ficha = FichaDatalux(
        nombre="Gearlabs SpA",
        rut="76.123.456-7",
        estado="Vigente",
        direccion="Av. Apoquindo 3000",
        comuna="Las Condes",
        anio_inicio="2018",
        actividades_economicas=(
            ActividadEconomica(nombre="Desarrollo de software", fecha_inicio="01-01-2018"),
        ),
    )
    proveedor = _DataluxFijo(ficha)
    m = Metricas(business_id=uuid.uuid4())
    completar_metricas(
        m,
        NuloSondaCiber(),
        None,
        datalux=proveedor,
        rut="76123456-7",
        nombre="Gearlabs SpA",
        direccion="Av. Apoquindo 3000, Las Condes",
    )
    assert proveedor.consultas == ["76123456-7"]
    assert m.score_domicilio == SCORE_MATCH
    assert m.score_huella_digital == SCORE_MATCH
    assert m.score_persona_juridica == 100
    assert m.datalux_razones is not None


def test_completar_metricas_sin_consulta_deja_base():
    proveedor = _DataluxFijo(
        FichaDatalux(nombre="X", rut="1-9", estado="Vigente", direccion="Calle 1")
    )
    m = Metricas(business_id=uuid.uuid4())
    completar_metricas(m, NuloSondaCiber(), None, datalux=proveedor)
    assert proveedor.consultas == []
    assert m.score_domicilio == SCORE_BASE
    assert m.score_huella_digital == SCORE_BASE
    assert m.score_persona_juridica == 0
