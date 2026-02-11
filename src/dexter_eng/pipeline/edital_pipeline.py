from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from dexter_eng.adapters.llm.client import LLMClient
from dexter_eng.adapters.pdf.extract_text import extract_text_from_pdf
from dexter_eng.core.rules.edital_rules import apply_edital_rules
from dexter_eng.persistence.db import (
    create_run,
    finish_run,
    get_or_create_document,
    init_db,
)
from dexter_eng.pipeline.steps.step_chunk import chunk_text
from dexter_eng.pipeline.steps import step_llm_structured
from dexter_eng.pipeline.steps.step_llm_structured import extract_edital_structured
from dexter_eng.renderers.markdown import to_markdown

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "0.2"


def _file_sha256(path: str) -> str:
    """Calcula SHA-256 do arquivo. Retorna hash do path se arquivo não existir."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return hashlib.sha256(path.encode()).hexdigest()


def _save_artifacts(
    run_dir: Path,
    extracted_text: str,
    prompt: str,
    llm_raw: str,
    validated_json: dict,
    result_md: str,
    meta: dict,
) -> None:
    """Salva artefatos de uma execução no diretório da run."""
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "extracted.txt").write_text(extracted_text, encoding="utf-8")
    (run_dir / "prompt_structured.txt").write_text(prompt, encoding="utf-8")
    (run_dir / "llm_raw.txt").write_text(llm_raw, encoding="utf-8")
    (run_dir / "validated.json").write_text(
        json.dumps(validated_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "result.md").write_text(result_md, encoding="utf-8")
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Artefatos salvos em: %s", run_dir)


def run_edital_pipeline(
    pdf_path: str,
    llm: LLMClient,
    prompt_template: str,
    out_dir: str,
    max_chars: int,
) -> Path:
    logger.info("=== Pipeline v%s iniciado para: %s ===", PIPELINE_VERSION, pdf_path)
    t0 = time.monotonic()

    # Inicializar persistência
    init_db()

    # Registrar documento e run
    file_hash = _file_sha256(pdf_path)
    doc_id = get_or_create_document(path=pdf_path, sha256=file_hash, pages=0, chars=0)
    run_id = create_run(document_id=doc_id, model=llm.model, pipeline_version=PIPELINE_VERSION)

    try:
        # 1. Extrair texto do PDF
        text = extract_text_from_pdf(pdf_path)

        # 2. Dividir em chunks
        chunks = chunk_text(text, max_chars=max_chars)
        merged = "\n\n".join(chunks[:4])  # v1 pragmático; depois vira map-reduce
        logger.info("Usando %d/%d chunks (total %d chars)", min(4, len(chunks)), len(chunks), len(merged))

        # 3. Extrair dados estruturados via LLM
        extraction = extract_edital_structured(llm, prompt_template, merged)

        # 4. Aplicar regras de negócio
        extraction = apply_edital_rules(extraction)

        # 5. Renderizar Markdown
        md = to_markdown(extraction)

        # 6. Salvar resultado principal
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        out_md = out / (Path(pdf_path).stem + "_edital.md")
        out_md.write_text(md, encoding="utf-8")

        # 7. Salvar artefatos da execução
        elapsed = time.monotonic() - t0
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        pdf_stem = Path(pdf_path).stem
        run_dir = out / "runs" / f"{ts}_{pdf_stem}"

        meta = {
            "pipeline_version": PIPELINE_VERSION,
            "model": llm.model,
            "pdf_path": pdf_path,
            "chars_extracted": len(text),
            "chars_prompt": len(step_llm_structured._last_prompt),
            "cache_hit": step_llm_structured._last_cache_hit,
            "elapsed_seconds": round(elapsed, 2),
        }

        _save_artifacts(
            run_dir=run_dir,
            extracted_text=text,
            prompt=step_llm_structured._last_prompt,
            llm_raw=step_llm_structured._last_raw_response,
            validated_json=extraction.model_dump(),
            result_md=md,
            meta=meta,
        )

        finish_run(run_id, status="success")
        logger.info("=== Pipeline concluído: %s (%.1fs) ===", out_md, elapsed)
        return out_md

    except Exception as e:
        finish_run(run_id, status="error", error=str(e))
        raise
