from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def chunk_text(text: str, max_chars: int) -> list[str]:
    """Quebra texto em chunks respeitando limite de caracteres por bloco."""
    chunks: list[str] = []
    cur: list[str] = []
    size = 0
    for line in text.splitlines(True):
        if size + len(line) > max_chars and cur:
            chunks.append("".join(cur))
            cur, size = [], 0
        cur.append(line)
        size += len(line)
    if cur:
        chunks.append("".join(cur))
    logger.info("Texto dividido em %d chunks (max_chars=%d)", len(chunks), max_chars)
    return chunks
