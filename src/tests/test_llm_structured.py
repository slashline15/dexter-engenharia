"""Testes para o step de extração estruturada via LLM (com mocks)."""

import json

import pytest

from dexter_eng.adapters.llm.client import LLMClient, LLMResponse
from dexter_eng.pipeline.steps.step_llm_structured import (
    _extract_json,
    extract_edital_structured,
)


# --- Mock LLM ---

class MockLLMClient(LLMClient):
    """LLM fake que retorna uma resposta pré-definida."""

    def __init__(self, response_text: str):
        super().__init__(model="mock", api_key="fake")
        self._response_text = response_text

    def complete(self, prompt: str) -> LLMResponse:
        return LLMResponse(text=self._response_text)


# --- Fixtures ---

VALID_PAYLOAD = {
    "orgao": "Prefeitura de Teste",
    "objeto": "Construção de escola",
    "prazos": [
        {
            "name": "Entrega propostas",
            "date_text": "20/07/2025",
            "citations": [{"page": 1, "excerpt": "conforme edital"}],
        }
    ],
    "documentos_exigidos": [
        {"title": "CNPJ", "description": "Inscrição ativa", "citations": []}
    ],
    "criterios_habilitacao": [],
    "penalidades": [],
    "pendencias": ["Valor estimado ausente"],
}

PROMPT_TEMPLATE = "Extraia dados:\n{{TEXT}}"


# --- Tests: _extract_json ---

class TestExtractJson:
    def test_plain_json(self):
        text = json.dumps(VALID_PAYLOAD)
        result = _extract_json(text)
        assert json.loads(result) == VALID_PAYLOAD

    def test_json_in_markdown_code_block(self):
        text = f"Aqui está o resultado:\n```json\n{json.dumps(VALID_PAYLOAD)}\n```"
        result = _extract_json(text)
        assert json.loads(result) == VALID_PAYLOAD

    def test_json_with_surrounding_text(self):
        text = f"Resultado da análise:\n{json.dumps(VALID_PAYLOAD)}\nFim."
        result = _extract_json(text)
        assert json.loads(result) == VALID_PAYLOAD

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="não retornou JSON"):
            _extract_json("Não há JSON aqui, apenas texto.")


# --- Tests: extract_edital_structured ---

class TestExtractEditalStructured:
    def test_valid_response(self):
        llm = MockLLMClient(json.dumps(VALID_PAYLOAD))
        result = extract_edital_structured(llm, PROMPT_TEMPLATE, "texto do edital")
        assert result.orgao == "Prefeitura de Teste"
        assert len(result.prazos) == 1
        assert result.prazos[0].name == "Entrega propostas"
        assert len(result.pendencias) == 1

    def test_template_substitution(self):
        """Verifica que {{TEXT}} é substituído no prompt."""
        captured_prompts = []

        class CaptureLLM(LLMClient):
            def __init__(self):
                super().__init__(model="mock", api_key="fake")

            def complete(self, prompt: str) -> LLMResponse:
                captured_prompts.append(prompt)
                return LLMResponse(text=json.dumps(VALID_PAYLOAD))

        llm = CaptureLLM()
        extract_edital_structured(llm, PROMPT_TEMPLATE, "CONTEÚDO AQUI")
        assert "CONTEÚDO AQUI" in captured_prompts[0]
        assert "{{TEXT}}" not in captured_prompts[0]

    def test_json_in_code_block(self):
        response = f"```json\n{json.dumps(VALID_PAYLOAD)}\n```"
        llm = MockLLMClient(response)
        result = extract_edital_structured(llm, PROMPT_TEMPLATE, "texto")
        assert result.orgao == "Prefeitura de Teste"

    def test_invalid_json_raises(self):
        llm = MockLLMClient("Isso não é JSON nenhum.")
        with pytest.raises(ValueError):
            extract_edital_structured(llm, PROMPT_TEMPLATE, "texto")

    def test_invalid_schema_raises(self):
        """JSON válido mas com schema inválido (page=0 viola ge=1)."""
        bad = {
            "prazos": [
                {
                    "name": "X",
                    "date_text": "Y",
                    "citations": [{"page": 0, "excerpt": "z"}],
                }
            ]
        }
        llm = MockLLMClient(json.dumps(bad))
        with pytest.raises(Exception):
            extract_edital_structured(llm, PROMPT_TEMPLATE, "texto")
