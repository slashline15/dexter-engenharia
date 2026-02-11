from __future__ import annotations

import logging

from dexter_eng.core.schemas.edital import EditalExtraction

logger = logging.getLogger(__name__)


def to_markdown(ex: EditalExtraction) -> str:
    lines: list[str] = []
    lines.append("# Resumo do Edital\n")
    lines.append(f"**Órgão:** {ex.orgao or '—'}  ")
    lines.append(f"**Objeto:** {ex.objeto or '—'}\n")

    def sec(title: str, items: list) -> None:
        lines.append(f"## {title}\n")
        if not items:
            lines.append("_Nada encontrado._\n")
            return
        for i in items:
            label = i.title if hasattr(i, "title") else i.name
            detail = getattr(i, "description", getattr(i, "date_text", ""))
            lines.append(f"- **{label}**: {detail}")
            if i.citations:
                for c in i.citations[:3]:
                    lines.append(f'  - (p.{c.page}) \u201c{c.excerpt.strip()[:200]}\u201d')
        lines.append("")

    sec("Prazos", ex.prazos)
    sec("Documentos exigidos", ex.documentos_exigidos)
    sec("Critérios de habilitação", ex.criterios_habilitacao)
    sec("Penalidades", ex.penalidades)

    lines.append("## Pendências / Ambiguidades\n")
    if ex.pendencias:
        for p in ex.pendencias:
            lines.append(f"- {p}")
    else:
        lines.append("_Nenhuma._")
    lines.append("")

    md = "\n".join(lines)
    logger.info("Markdown gerado: %d linhas, %d chars", len(lines), len(md))
    return md
