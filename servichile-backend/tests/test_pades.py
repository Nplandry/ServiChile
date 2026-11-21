from app.dominio.pades import emisor_coincide, fecha_dentro_ventana, parsear_fecha_emision
from app.infraestructura.pades import verificar_firma_pades
from app.infraestructura.trust_vault import invalidar_cache_confianza, ruta_ca_default
from tests.helpers_pades import (
    crear_ca_y_hoja,
    firmar_pdf_pades,
    pdf_con_texto,
    vault_con_raiz_prueba,
)

def test_emisor_sii_coincide():
    assert emisor_coincide(
        "CN=Servicio de Impuestos Internos",
        "O=Servicio de Impuestos Internos",
        "inicio_actividades",
    )
    assert not emisor_coincide(
        "CN=Random Corp",
        "O=Acepta.com S.A.",
        "inicio_actividades",
    )

def test_fecha_ventana():
    from datetime import date

    hoy = date(2026, 11, 15)
    assert fecha_dentro_ventana(date(2026, 10, 1), hoy=hoy)
    assert not fecha_dentro_ventana(date(2026, 1, 1), hoy=hoy)

def test_parsear_fecha():
    assert parsear_fecha_emision("Fecha 10/11/2026") == __import__("datetime").date(
        2026, 11, 10
    )

def test_fixture_antecedentes_trusted_contra_ca_chile():
    from pathlib import Path

    fixture = (
        Path(__file__).parent / "fixtures" / "ANT_500727268737_21082350.pdf"
    )
    assert ruta_ca_default().is_file()
    invalidar_cache_confianza()
    r = verificar_firma_pades(fixture.read_bytes(), perfil="antecedentes")
    assert r.ok is True
    assert r.intact is True
    assert r.trusted is True
    assert r.coverage_ok is True
    assert r.entidad_emisora == "REGISTRO_CIVIL"

def test_autofirma_sin_ca_rechazada(tmp_path):
    texto = (
        "SERVICIO DE IMPUESTOS INTERNOS inicio de actividades RUT 76.123.456-0 "
        "Fecha 10/11/2026 Empresa vigente contribuyente"
    )

    signed = firmar_pdf_pades(
        pdf_con_texto(texto),
        common_name="Servicio de Impuestos Internos",
        organization="Servicio de Impuestos Internos",
    )
    invalidar_cache_confianza()
    r = verificar_firma_pades(signed, perfil="inicio_actividades")
    assert r.ok is False
    assert "pades-no-confiable" in r.senales or r.trusted is False

def test_verificar_pades_sii_ok_con_vault_prueba(tmp_path):
    texto = (
        "SERVICIO DE IMPUESTOS INTERNOS inicio de actividades RUT 76.123.456-0 "
        "Fecha 10/11/2026 Empresa vigente contribuyente"
    )
    root, leaf, key = crear_ca_y_hoja(
        leaf_cn="Servicio de Impuestos Internos",
        leaf_org="Servicio de Impuestos Internos",
    )
    vault = vault_con_raiz_prueba(tmp_path / "ca.pem", root)
    signed = firmar_pdf_pades(
        pdf_con_texto(texto),
        common_name="Servicio de Impuestos Internos",
        leaf_cert_pem=leaf,
        leaf_key_pem=key,
    )
    invalidar_cache_confianza()
    r = verificar_firma_pades(
        signed, perfil="inicio_actividades", ca_pem_path=str(vault)
    )
    assert r.ok is True
    assert r.intact and r.trusted and r.coverage_ok
    assert r.entidad_emisora == "SII"

def test_verificar_pades_sin_firma():
    invalidar_cache_confianza()
    r = verificar_firma_pades(pdf_con_texto("hola mundo"), perfil="antecedentes")
    assert r.ok is False
    assert "sin-firma-pades" in r.senales
