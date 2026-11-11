"""Presentación del marketplace: CTA por categoría, logo e imagen por defecto."""
from __future__ import annotations

import re

CTA_POR_CATEGORIA = {
    "gimnasio": "Agendar pase",
    "clinica-dental": "Agendar cita",
    "restaurante": "Reservar mesa",
    "arriendo": "Postular",
    "evento": "Reservar ticket",
    "comercio": "Ver comercio",
    "automotriz": "Ver servicio",
    "otro": "Ver más",
}

IMAGEN_POR_CATEGORIA = {
    "gimnasio": "https://images.unsplash.com/photo-1571902943202-507ec2618e8f?auto=format&fit=crop&w=800&h=360&q=80",
    "clinica-dental": "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=800&h=500&q=80",
    "restaurante": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=800&h=500&q=80",
    "comercio": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=800&h=500&q=80",
    "arriendo": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&h=500&q=80",
    "evento": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=800&h=500&q=80",
    "automotriz": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?auto=format&fit=crop&w=800&h=500&q=80",
    "otro": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&h=500&q=80",
}


def cta_texto(categoria: str) -> str:
    return CTA_POR_CATEGORIA.get(categoria, CTA_POR_CATEGORIA["otro"])


def imagen_por_defecto(categoria: str) -> str:
    return IMAGEN_POR_CATEGORIA.get(categoria, IMAGEN_POR_CATEGORIA["otro"])


def logo_texto(nombre: str) -> str:
    partes = re.sub(r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s]", " ", nombre or "").split()
    partes = [p for p in partes if p]
    if not partes:
        return "S"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()


def imagen_efectiva(imagen_url: str | None, categoria: str) -> str:
    return imagen_url or imagen_por_defecto(categoria)
