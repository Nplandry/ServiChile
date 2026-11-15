from __future__ import annotations

import re

CTA_POR_CATEGORIA = {
    "tecnologia": "Ver ficha de transparencia",
    "industria": "Evaluar proveedor",
    "construccion": "Evaluar contratista",
    "servicios-profesionales": "Ver due diligence",
    "logistica": "Validar operador logístico",
}

IMAGEN_POR_CATEGORIA = {
    "tecnologia": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=800&h=500&q=80",
    "industria": "https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?auto=format&fit=crop&w=800&h=500&q=80",
    "construccion": "https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=800&h=500&q=80",
    "servicios-profesionales": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=800&h=500&q=80",
    "logistica": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=800&h=500&q=80",
}


def cta_texto(categoria: str) -> str:

    return CTA_POR_CATEGORIA.get(categoria, "Ver ficha")


def imagen_por_defecto(categoria: str) -> str:

    return IMAGEN_POR_CATEGORIA.get(categoria, IMAGEN_POR_CATEGORIA["tecnologia"])


def logo_texto(nombre: str) -> str:

    partes = re.sub("[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\\s]", " ", nombre or "").split()

    partes = [p for p in partes if p]

    if not partes:

        return "S"

    if len(partes) == 1:

        return partes[0][:2].upper()

    return (partes[0][0] + partes[1][0]).upper()


def imagen_efectiva(imagen_url: str | None, categoria: str) -> str:

    return imagen_url or imagen_por_defecto(categoria)
