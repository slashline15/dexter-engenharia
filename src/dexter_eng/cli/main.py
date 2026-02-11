from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import typer

from dexter_eng.adapters.llm.openai_client import OpenAILLMClient
from dexter_eng.config.settings import Settings
from dexter_eng.persistence.db import get_cache_stats, get_run_history, init_db
from dexter_eng.pipeline.edital_pipeline import run_edital_pipeline

logger = logging.getLogger(__name__)

app = typer.Typer(help="Dexter Engenharia – IA verticalizada para editais")

DEFAULT_PROMPT = Path(__file__).resolve().parent.parent / "core" / "prompts" / "edital_extract.md"


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _read_prompt(path: Path) -> str:
    if not path.exists():
        raise typer.BadParameter(f"Arquivo de prompt não encontrado: {path}")
    return path.read_text(encoding="utf-8")


def _elapsed_display(started_at: str | None, ended_at: str | None) -> str:
    if not started_at or not ended_at:
        return "-"
    try:
        started = datetime.fromisoformat(started_at)
        ended = datetime.fromisoformat(ended_at)
        return f"{(ended - started).total_seconds():.1f}s"
    except ValueError:
        return "-"


def _run_edital(pdf: str, prompt: Path, verbose: bool, ocr: str, local_model: str) -> None:
    _setup_logging(verbose)
    logger.info("Iniciando processamento: %s", pdf)

    if ocr != "off" or local_model != "off":
        logger.info("Flags futuras recebidas (ainda desativadas): ocr=%s, local_model=%s", ocr, local_model)

    settings = Settings()
    if local_model and local_model != "off":
        from dexter_eng.adapters.llm.local_ollama_client import LocalOllamaClient

        logger.info("Usando modelo local via Ollama: %s", local_model)
        # Instancia com defaults seguros conforme solicitado
        llm = LocalOllamaClient(model=local_model)
    else:
        llm = OpenAILLMClient(model=settings.llm_model, api_key=settings.llm_api_key)
    prompt_template = _read_prompt(prompt)

    out = run_edital_pipeline(
        pdf_path=pdf,
        llm=llm,
        prompt_template=prompt_template,
        out_dir=settings.out_dir,
        max_chars=settings.max_chars_per_chunk,
        ocr=ocr,
        local_model=local_model,
    )
    logger.info("Arquivo gerado: %s", out)
    typer.echo(f"[OK] Gerado: {out}")


def _show_history(limit: int) -> None:
    init_db()
    rows = get_run_history(limit=limit)
    typer.echo("id | status | cache_hit | prompt_chars | response_chars | model | started_at | elapsed")
    typer.echo("-" * 98)
    for row in rows:
        elapsed = _elapsed_display(row["started_at"], row["ended_at"])
        typer.echo(
            f"{row['id']} | {row['status'] or '-'} | {row['cache_hit']} | "
            f"{row['prompt_chars']} | {row['response_chars']} | {row['model'] or '-'} | "
            f"{row['started_at'] or '-'} | {elapsed}"
        )


def _show_cache_stats() -> None:
    init_db()
    stats = get_cache_stats()
    typer.echo(f"total_entries_cache: {stats['total_entries']}")
    typer.echo(f"total_runs: {stats['total_runs']}")
    typer.echo(f"cache_hits: {stats['cache_hits']}")
    typer.echo(f"hit_rate: {stats['hit_rate']:.2%}")


@app.command()
def main(
    target: str = typer.Argument(..., help="PDF para processar ou comando: history|cache-stats"),
    prompt: Path = typer.Option(DEFAULT_PROMPT, help="Caminho para o template de prompt"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Ativa logs detalhados"),
    limit: int = typer.Option(20, "--limit", min=1, help="Limite para history"),
    ocr: str = typer.Option("off", "--ocr", help="Modo OCR futuro: auto|off"),
    local_model: str = typer.Option("off", "--local-model", help="Modelo local futuro: auto|off"),
) -> None:
    """Entrada principal: processa PDF ou mostra relatórios de histórico/cache."""
    if target == "history":
        _show_history(limit=limit)
        return
    if target == "cache-stats":
        _show_cache_stats()
        return
    _run_edital(pdf=target, prompt=prompt, verbose=verbose, ocr=ocr, local_model=local_model)


if __name__ == "__main__":
    app()
