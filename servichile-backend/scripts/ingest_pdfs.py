"""Carga un PDF de normativa oficial en la base de conocimiento (tablas documentos y fragmentos).

Uso:
    python -m scripts.ingest_pdfs ruta/al/archivo.pdf \
        --titulo "Ley 19.496 sobre Protección de los Derechos de los Consumidores" \
        --url "https://www.bcn.cl/leychile/navegar?idNorma=61438" \
        --categoria seguros

Omita --categoria si el documento aplica a todos los casos.
"""
import argparse
import hashlib
import sys
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.infrastructure.db import Documento, Fragmento, get_engine
from app.infrastructure.llm import build_provider

CHUNK_CHARS = 1200
OVERLAP_CHARS = 200
BATCH = 50


def partir(texto: str) -> list[str]:
    texto = " ".join(texto.split())
    partes, inicio = [], 0
    while inicio < len(texto):
        fin = min(len(texto), inicio + CHUNK_CHARS)
        if fin < len(texto):
            corte = texto.rfind(". ", inicio, fin)
            if corte > inicio + CHUNK_CHARS // 2:
                fin = corte + 1
        partes.append(texto[inicio:fin].strip())
        if fin == len(texto):
            break
        inicio = max(fin - OVERLAP_CHARS, inicio + 1)
    return [p for p in partes if p]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--titulo", required=True)
    parser.add_argument("--url")
    parser.add_argument("--categoria", choices=["embargo-falso", "seguros", "portabilidad"])
    args = parser.parse_args()

    contenido = args.pdf.read_bytes()
    digest = hashlib.sha256(contenido).hexdigest()
    llm = build_provider(get_settings())
    session = sessionmaker(bind=get_engine())()

    if session.scalar(select(Documento).where(Documento.hash_sha256 == digest)):
        print(f"El documento ya estaba cargado (sha256 {digest[:12]}). No se hizo nada.")
        return 0

    reader = PdfReader(args.pdf)
    piezas = [(n, parte) for n, page in enumerate(reader.pages, 1) for parte in partir(page.extract_text() or "")]
    if not piezas:
        print("No se pudo extraer texto. Si el PDF es escaneado, aplique OCR antes de cargarlo.", file=sys.stderr)
        return 1

    documento = Documento(titulo=args.titulo, url_fuente=args.url, categoria=args.categoria, hash_sha256=digest)
    session.add(documento)
    session.flush()

    for i in range(0, len(piezas), BATCH):
        lote = piezas[i : i + BATCH]
        vectores = llm.embed([texto for _, texto in lote], para_consulta=False)
        session.add_all(
            Fragmento(documento_id=documento.id, pagina=pagina, orden=i + j, contenido=texto, embedding=vector)
            for j, ((pagina, texto), vector) in enumerate(zip(lote, vectores, strict=True))
        )
    session.commit()
    print(f"Cargado '{args.titulo}': {len(reader.pages)} páginas, {len(piezas)} fragmentos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
