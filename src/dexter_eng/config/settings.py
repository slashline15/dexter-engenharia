from __future__ import annotations

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Configurações do sistema carregadas do ambiente.

    Instancie APÓS load_dotenv() para garantir que as variáveis estejam disponíveis.
    """

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_api_key: str = ""
    out_dir: str = "out"
    max_chars_per_chunk: int = 8000

    def __init__(self, **overrides):
        defaults = {
            "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
            "llm_model": os.getenv("LLM_MODEL", "gpt-4o"),
            "llm_api_key": os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
            "out_dir": os.getenv("OUT_DIR", "out"),
            "max_chars_per_chunk": int(os.getenv("MAX_CHARS_PER_CHUNK", "8000")),
        }
        defaults.update(overrides)
        super().__init__(**defaults)
