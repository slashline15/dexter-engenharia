from __future__ import annotations

import json
import time
import uuid
from typing import Any, Optional

import httpx

from dexter_eng.adapters.llm.client import LLMClient, LLMResponse


class LocalOllamaClient(LLMClient):
    """
    Cliente LLM local via Ollama (http://localhost:11434).

    Interface compatível com o teu pipeline:
      - atributo: model (str)
      - método: complete(prompt:str) -> LLMResponse(text, raw)

    Depende de:
      pip install httpx
    """

    def __init__(
        self,
        model: str = "mistral",
        base_url: str = "http://127.0.0.1:11434",
        timeout_s: float = 300.0,
        temperature: float = 0.2,
        num_ctx: int = 8192,
        num_predict: int = 2048,
        seed: Optional[int] = 42,
    ) -> None:
        super().__init__(model=model)
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.num_predict = num_predict
        self.seed = seed

    def _payload(self, prompt: str) -> dict[str, Any]:
        # /api/generate: simples e direto (não-chat), bom pra “retorne APENAS JSON”
        return {
            "model": self.model,
            "prompt": prompt,
            "stream": True,  # ATIVAR STREAMING
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
                **({"seed": self.seed} if self.seed is not None else {}),
            },
        }

    def complete(self, prompt: str) -> LLMResponse:
        from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

        request_id = f"ollama_{uuid.uuid4().hex}"
        t0 = time.monotonic()

        url = f"{self.base_url}/api/generate"
        payload = self._payload(prompt)

        full_text = []
        full_response_debug = {}

        # Contexto de progresso visual
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task(f"[cyan]Gerando com {self.model}...", total=None)

            try:
                with httpx.Client(timeout=self.timeout_s) as client:
                    with client.stream("POST", url, json=payload) as r:
                        r.raise_for_status()

                        for line in r.iter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                                # Capta o pedaço de texto
                                content = chunk.get("response", "")
                                if content:
                                    full_text.append(content)
                                    # Atualiza spinner com contagem parcial (opcional)
                                    # progress.update(task, description=f"[cyan]Gerando... ({len(full_text)} tokens)")
                                
                                if chunk.get("done"):
                                    full_response_debug = chunk
                            except json.JSONDecodeError:
                                pass
            except httpx.ReadTimeout:
                # Se estourar o timeout, retornamos o que temos ou erro
                raise TimeoutError(f"Ollama excedeu o tempo limite de {self.timeout_s}s")

        text = "".join(full_text).strip()

        raw = {
            "id": request_id,
            "provider": "ollama",
            "model": self.model,
            "elapsed_s": round(time.monotonic() - t0, 3),
            "ollama_last_chunk": full_response_debug,
        }
        return LLMResponse(text=text, raw=raw)

    def ping(self) -> bool:
        """Verifica se o Ollama está acessível."""
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False
