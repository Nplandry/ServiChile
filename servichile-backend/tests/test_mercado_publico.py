from app.domain.transparencia.mercado_publico import (
    HallazgosMercadoPublico,
    formato_rut_chilecompra,
    score_mercado_publico,
)

from app.infrastructure.chilecompra import FakeChileCompra, NullChileCompra


def test_formato_rut_con_puntos():

    assert formato_rut_chilecompra("70017820-K") == "70.017.820-K"

    assert formato_rut_chilecompra("1234567-0") == "1.234.567-0"


def test_score_sin_consulta_o_sin_proveedor_cero():

    assert score_mercado_publico(HallazgosMercadoPublico()) == 0

    assert score_mercado_publico(HallazgosMercadoPublico(consulta_ok=True)) == 0


def test_score_proveedor_con_oc():

    assert (
        score_mercado_publico(
            HallazgosMercadoPublico(
                consulta_ok=True,
                proveedor_encontrado=True,
                codigo_proveedor="1",
                tiene_ordenes_recientes=True,
            )
        )
        == 100
    )


def test_null_y_fake_clientes():

    assert NullChileCompra().score_para_rut("76.543.210-K") == 0

    assert FakeChileCompra().score_para_rut("76.543.210-K") == 100

    assert FakeChileCompra().score_para_rut(None) == 0
