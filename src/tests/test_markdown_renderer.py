"""Testes para o renderer Markdown."""

from dexter_eng.core.schemas.edital import (
    Citation,
    Deadline,
    EditalExtraction,
    Requirement,
)
from dexter_eng.renderers.markdown import to_markdown


class TestToMarkdown:
    def test_minimal_extraction(self):
        ex = EditalExtraction()
        md = to_markdown(ex)
        assert "# Resumo do Edital" in md
        assert "**Órgão:** —" in md
        assert "**Objeto:** —" in md
        assert "_Nada encontrado._" in md

    def test_orgao_and_objeto(self):
        ex = EditalExtraction(orgao="Prefeitura X", objeto="Obra Y")
        md = to_markdown(ex)
        assert "**Órgão:** Prefeitura X" in md
        assert "**Objeto:** Obra Y" in md

    def test_prazos_rendered(self):
        ex = EditalExtraction(
            prazos=[Deadline(name="Abertura", date_text="01/06/2025")]
        )
        md = to_markdown(ex)
        assert "## Prazos" in md
        assert "**Abertura**: 01/06/2025" in md

    def test_documentos_with_citations(self):
        ex = EditalExtraction(
            documentos_exigidos=[
                Requirement(
                    title="CNPJ",
                    description="Comprovante ativo",
                    citations=[Citation(page=5, excerpt="conforme item 8.1")],
                )
            ]
        )
        md = to_markdown(ex)
        assert "**CNPJ**: Comprovante ativo" in md
        assert "(p.5)" in md
        assert "conforme item 8.1" in md

    def test_pendencias_rendered(self):
        ex = EditalExtraction(pendencias=["Item ambíguo A", "Item ambíguo B"])
        md = to_markdown(ex)
        assert "- Item ambíguo A" in md
        assert "- Item ambíguo B" in md

    def test_no_pendencias_message(self):
        ex = EditalExtraction(pendencias=[])
        md = to_markdown(ex)
        assert "_Nenhuma._" in md
