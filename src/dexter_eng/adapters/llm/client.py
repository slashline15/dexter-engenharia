from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LLMResponse:
    text: str
    raw: Optional[Dict[str, Any]] = None


class LLMClient(ABC):
    """Contrato base para qualquer provider de LLM."""

    def __init__(self, model: str, api_key: str | None = None):
        self.model = model
        self.api_key = api_key

    @abstractmethod
    def complete(self, prompt: str) -> LLMResponse:
        """Envia prompt e retorna resposta estruturada."""
