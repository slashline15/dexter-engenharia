"""Testes para o módulo de configurações."""

from dexter_eng.config.settings import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.llm_provider == "openai"
        assert s.max_chars_per_chunk == 8000

    def test_override_via_constructor(self):
        s = Settings(llm_model="gpt-4o-mini", max_chars_per_chunk=4000)
        assert s.llm_model == "gpt-4o-mini"
        assert s.max_chars_per_chunk == 4000

    def test_reads_env_vars(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "gpt-3.5-turbo")
        monkeypatch.setenv("OUT_DIR", "/tmp/saida")
        s = Settings()
        assert s.llm_model == "gpt-3.5-turbo"
        assert s.out_dir == "/tmp/saida"

    def test_api_key_from_llm_key(self, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "sk-test-123")
        s = Settings()
        assert s.llm_api_key == "sk-test-123"

    def test_api_key_fallback_to_openai(self, monkeypatch):
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-456")
        s = Settings()
        assert s.llm_api_key == "sk-openai-456"
