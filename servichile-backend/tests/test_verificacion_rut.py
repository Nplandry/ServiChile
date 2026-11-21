from app.configuracion import Configuracion
from app.infraestructura.verificacion import (
    ChileCompraVerificadorRut,
    EstrictoVerificadorRut,
    MuestraVerificadorRut,
    construir_verificador_rut,
)

def test_muestra_solo_en_test():
    assert isinstance(
        construir_verificador_rut("muestra", app_env="test"), MuestraVerificadorRut
    )
    assert isinstance(
        construir_verificador_rut("muestra", app_env="local"), EstrictoVerificadorRut
    )

def test_estricto_rechaza():
    v = EstrictoVerificadorRut()
    assert v.existe_y_activo("12345678-5") is False

def test_chilecompra_sin_ticket_rechaza():
    v = ChileCompraVerificadorRut("")
    assert v.existe_y_activo("76123456-0") is False

def test_construir_chilecompra():
    v = construir_verificador_rut(
        "chilecompra", app_env="local", chilecompra_ticket="demo-ticket"
    )
    assert isinstance(v, ChileCompraVerificadorRut)

def test_settings_rut_verifier_derivado():
    base = dict(
        jwt_secret="x" * 32,
        database_url="sqlite://",
        chilecompra_ticket="",
        google_places_api_key="",
        redis_url="redis://localhost:6379/0",
    )
    assert Configuracion(**base, app_env="test").rut_verifier == "muestra"
    assert Configuracion(**base, app_env="local").rut_verifier == "estricto"
    con_ticket = {**base, "chilecompra_ticket": "ticket"}
    assert Configuracion(**con_ticket, app_env="local").rut_verifier == "chilecompra"
