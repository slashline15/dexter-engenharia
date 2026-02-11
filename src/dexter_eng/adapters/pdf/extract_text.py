from __future__ import annotations

import logging
from pathlib import Path

import fitz  # pymupdf

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    p = Path(pdf_path)
    if not p.exists():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    logger.info("Extraindo texto de: %s", p.name)
    parts: list[str] = []
    with fitz.open(str(p)) as doc:
        logger.info("PDF aberto: %d páginas", doc.page_count)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            txt = page.get_text("text")
            parts.append(f"\n\n=== PAGE {i + 1} ===\n{txt}")
            logger.debug("Página %d: %d chars extraídos", i + 1, len(txt))

    full_text = "".join(parts).strip()
    logger.info("Extração concluída: %d chars totais", len(full_text))
    return full_text
