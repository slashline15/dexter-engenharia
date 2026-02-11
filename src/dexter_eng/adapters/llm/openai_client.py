from __future__ import annotations

import logging
import os

from openai import OpenAI

from dexter_eng.adapters.llm.client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


class OpenAILLMClient(LLMClient):
    def __init__(self, model: str, api_key: str | None = None):
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        super().__init__(model=model, api_key=resolved_key)
        self.client = OpenAI(api_key=resolved_key)
        logger.info("OpenAI client inicializado (model=%s)", model)

    def complete(self, prompt: str) -> LLMResponse:
        logger.debug("Enviando prompt para OpenAI (%d chars)", len(prompt))
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.choices[0].message.content or ""
        logger.info("Resposta recebida da OpenAI (%d chars)", len(text))
        return LLMResponse(text=text, raw=resp.model_dump())
