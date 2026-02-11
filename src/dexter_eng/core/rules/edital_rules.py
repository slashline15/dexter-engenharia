from __future__ import annotations

import logging

from dexter_eng.core.schemas.edital import EditalExtraction

logger = logging.getLogger(__name__)


def apply_edital_rules(ex: EditalExtraction) -> EditalExtraction:
    """Aplica regras de pós-processamento na extração."""
    original_count = len(ex.pendencias)
    ex.pendencias = [p.strip() for p in ex.pendencias if p.strip()]
    removed = original_count - len(ex.pendencias)
    if removed:
        logger.info("Regras aplicadas: %d pendências vazias removidas", removed)
    else:
        logger.info("Regras aplicadas: nenhuma alteração necessária")
    return ex
