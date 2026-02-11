"""Testes para a integração de cache LLM no step_llm_structured."""

import json

from dexter_eng.adapters.llm.client import LLMClient, LLMResponse
from dexter_eng.pipeline.steps import step_llm_structured
from dexter_eng.pipeline.steps.step_llm_structured import extract_edital_structured
from dexter_eng.persistence.db import get_cached_response


VALID_PAYLOAD = {
    "orgao": "Prefeitura de Cache",
    "objeto": "Teste de cache LLM",
    "prazos": [],
    "documentos_exigidos": [],
    "criterios_habilitacao": [],
    "penalidades": [],
    "pendencias": [],
}

PROMPT_TEMPLATE = "Extraia dados:\n{{TEXT}}"


class CountingLLM(LLMClient):
    """LLM fake que conta quantas vezes complete() foi chamado."""

    def __init__(self, response_text: str):
        super().__init__(model="test-model", api_key="fake")
        self._response_text = response_text
        self.call_count = 0

    def complete(self, prompt: str) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(text=self._response_text)


class TestCacheIntegration:
    def test_first_call_is_cache_miss(self):
        llm = CountingLLM(json.dumps(VALID_PAYLOAD))
        extract_edital_structured(llm, PROMPT_TEMPLATE, "texto original")
        assert llm.call_count == 1
        assert step_llm_structured._last_cache_hit is False

    def test_second_call_is_cache_hit(self):
        llm = CountingLLM(json.dumps(VALID_PAYLOAD))
        extract_edital_structured(llm, PROMPT_TEMPLATE, "texto repetido")
        assert llm.call_count == 1

        # Mesma chamada → cache hit
        extract_edital_structured(llm, PROMPT_TEMPLATE, "texto repetido")
        assert llm.call_count == 1  # NÃO chamou de novo
        assert step_llm_structured._last_cache_hit is True

    def test_different_text_is_cache_miss(self):
        llm = CountingLLM(json.dumps(VALID_PAYLOAD))
        extract_edital_structured(llm, PROMPT_TEMPLATE, "texto A")
        extract_edital_structured(llm, PROMPT_TEMPLATE, "texto B")
        assert llm.call_count == 2  # dois prompts diferentes

    def test_different_template_is_cache_miss(self):
        llm = CountingLLM(json.dumps(VALID_PAYLOAD))
        extract_edital_structured(llm, "Template 1: {{TEXT}}", "mesmo texto")
        extract_edital_structured(llm, "Template 2: {{TEXT}}", "mesmo texto")
        assert llm.call_count == 2

    def test_cache_hit_returns_same_result(self):
        llm = CountingLLM(json.dumps(VALID_PAYLOAD))
        r1 = extract_edital_structured(llm, PROMPT_TEMPLATE, "dados iguais")
        r2 = extract_edital_structured(llm, PROMPT_TEMPLATE, "dados iguais")
        assert r1.orgao == r2.orgao
        assert r1.objeto == r2.objeto

    def test_response_persisted_in_db(self):
        """Verifica que a resposta da LLM é salva no banco SQLite."""
        import hashlib

        llm = CountingLLM(json.dumps(VALID_PAYLOAD))
        text = "conteúdo para persistência"
        extract_edital_structured(llm, PROMPT_TEMPLATE, text)

        prompt = PROMPT_TEMPLATE.replace("{{TEXT}}", text)
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        cached = get_cached_response(prompt_hash, "test-model")
        assert cached is not None
        assert "Prefeitura de Cache" in cached


class TestModuleLevelState:
    def test_last_prompt_populated(self):
        llm = CountingLLM(json.dumps(VALID_PAYLOAD))
        extract_edital_structured(llm, PROMPT_TEMPLATE, "meu edital")
        assert "meu edital" in step_llm_structured._last_prompt
        assert "{{TEXT}}" not in step_llm_structured._last_prompt

    def test_last_raw_response_populated(self):
        raw = json.dumps(VALID_PAYLOAD)
        llm = CountingLLM(raw)
        extract_edital_structured(llm, PROMPT_TEMPLATE, "qualquer")
        assert step_llm_structured._last_raw_response == raw

    def test_last_raw_response_on_cache_hit(self):
        """Mesmo com cache hit, _last_raw_response deve ser preenchido."""
        raw = json.dumps(VALID_PAYLOAD)
        llm = CountingLLM(raw)
        extract_edital_structured(llm, PROMPT_TEMPLATE, "repetido state")
        extract_edital_structured(llm, PROMPT_TEMPLATE, "repetido state")
        assert step_llm_structured._last_raw_response == raw
        assert step_llm_structured._last_cache_hit is True
