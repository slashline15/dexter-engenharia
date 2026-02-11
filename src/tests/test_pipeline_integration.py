"""Teste de integração do pipeline completo (sem PDF real, sem LLM real)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from dexter_eng.adapters.llm.client import LLMClient, LLMResponse
from dexter_eng.pipeline.edital_pipeline import run_edital_pipeline


FAKE_PDF_TEXT = """
=== PAGE 1 ===
EDITAL DE LICITAÇÃO N° 001/2025
Órgão: Prefeitura Municipal de Exemplo
Objeto: Contratação de empresa para execução de obras de pavimentação.

=== PAGE 2 ===
Prazo para entrega de propostas: 15/08/2025
Documentos exigidos: CNPJ, Certidão Negativa de Débitos.
"""

FAKE_LLM_RESPONSE = json.dumps({
    "orgao": "Prefeitura Municipal de Exemplo",
    "objeto": "Contratação de empresa para execução de obras de pavimentação",
    "prazos": [
        {
            "name": "Entrega de propostas",
            "date_text": "15/08/2025",
            "citations": [{"page": 2, "excerpt": "Prazo para entrega de propostas: 15/08/2025"}],
        }
    ],
    "documentos_exigidos": [
        {
            "title": "CNPJ",
            "description": "Comprovante de inscrição no CNPJ",
            "citations": [{"page": 2, "excerpt": "Documentos exigidos: CNPJ"}],
        },
        {
            "title": "Certidão Negativa de Débitos",
            "description": "Certidão negativa junto à Receita Federal",
            "citations": [],
        },
    ],
    "criterios_habilitacao": [],
    "penalidades": [],
    "pendencias": ["Valor estimado da contratação não informado", "  "],
})


class FakeLLM(LLMClient):
    def __init__(self):
        super().__init__(model="fake", api_key="fake")

    def complete(self, prompt: str) -> LLMResponse:
        return LLMResponse(text=FAKE_LLM_RESPONSE)


class TestEditalPipeline:
    def test_full_pipeline(self, tmp_path: Path):
        """Executa o pipeline completo com mocks de PDF e LLM."""
        out_dir = str(tmp_path / "output")

        with patch(
            "dexter_eng.pipeline.edital_pipeline.extract_text_from_pdf",
            return_value=FAKE_PDF_TEXT,
        ):
            result = run_edital_pipeline(
                pdf_path="edital_fake.pdf",
                llm=FakeLLM(),
                prompt_template="Extraia:\n{{TEXT}}",
                out_dir=out_dir,
                max_chars=8000,
            )

        assert result.exists()
        assert result.suffix == ".md"
        assert result.name == "edital_fake_edital.md"

        content = result.read_text(encoding="utf-8")
        assert "Prefeitura Municipal de Exemplo" in content
        assert "pavimentação" in content
        assert "15/08/2025" in content
        assert "CNPJ" in content
        # A pendência vazia deve ter sido removida pela regra
        assert "Valor estimado" in content

    def test_output_dir_created(self, tmp_path: Path):
        """Verifica que o diretório de saída é criado automaticamente."""
        out_dir = str(tmp_path / "novo" / "sub" / "dir")

        with patch(
            "dexter_eng.pipeline.edital_pipeline.extract_text_from_pdf",
            return_value=FAKE_PDF_TEXT,
        ):
            result = run_edital_pipeline(
                pdf_path="test.pdf",
                llm=FakeLLM(),
                prompt_template="{{TEXT}}",
                out_dir=out_dir,
                max_chars=8000,
            )

        assert Path(out_dir).exists()
        assert result.exists()
