from __future__ import annotations

import hashlib
import json
import logging
import re

from pydantic import ValidationError

from dexter_eng.adapters.llm.client import LLMClient
from dexter_eng.core.schemas.edital import EditalExtraction
from dexter_eng.persistence.db import get_cached_response, save_cached_response

logger = logging.getLogger(__name__)

# Estado do último call — lido pelo pipeline para salvar artefatos
_last_prompt: str = ""
_last_raw_response: str = ""
_last_cache_hit: bool = False
_last_request_id: str | None = None


def _extract_json(text: str) -> str:
    """Extrai bloco JSON da resposta da LLM, suportando markdown code blocks."""
    # Tenta extrair de code block ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)

    # Fallback: encontra o JSON mais externo
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(
            "LLM não retornou JSON válido. Resposta recebida:\n"
            f"{text[:500]}..."
        )
    return text[start : end + 1]


def extract_edital_structured(
    llm: LLMClient, prompt_template: str, text: str
) -> EditalExtraction:
    global _last_prompt, _last_raw_response, _last_cache_hit, _last_request_id

    prompt = prompt_template.replace("{{TEXT}}", text)
    _last_prompt = prompt
    logger.info("Enviando texto para extração estruturada (%d chars no prompt)", len(prompt))

    # Cache por hash do prompt
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    cached = get_cached_response(prompt_hash, llm.model)

    if cached is not None:
        logger.info("Cache HIT (hash=%s…)", prompt_hash[:12])
        resp = cached
        _last_cache_hit = True
        _last_request_id = None
    else:
        logger.info("Cache MISS (hash=%s…)", prompt_hash[:12])
        llm_response = llm.complete(prompt)
        resp = llm_response.text.strip()
        raw = llm_response.raw or {}
        _last_request_id = raw.get("id") if isinstance(raw, dict) else None
        save_cached_response(
            prompt_hash,
            llm.model,
            resp,
            prompt_chars=len(prompt),
            response_chars=len(resp),
        )
        _last_cache_hit = False

    _last_raw_response = resp
    logger.debug("Resposta bruta da LLM (%d chars)", len(resp))

    json_str = _extract_json(resp)
    payload = json.loads(json_str)
    logger.info("JSON parseado com sucesso")

    try:
        extraction = EditalExtraction.model_validate(payload)
        logger.info(
            "Extração validada: orgao=%s, %d prazos, %d docs, %d pendencias",
            extraction.orgao,
            len(extraction.prazos),
            len(extraction.documentos_exigidos),
            len(extraction.pendencias),
        )
        return extraction
    except ValidationError as e:
        logger.error("Falha na validação do schema: %s", e)
        logger.debug("Payload rejeitado: %s", json.dumps(payload, ensure_ascii=False)[:1000])
        raise
