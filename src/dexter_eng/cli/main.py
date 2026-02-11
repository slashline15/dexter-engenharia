from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import typer

from dexter_eng.config.settings import Settings
from dexter_eng.pipeline.edital_pipeline import run_edital_pipeline
from dexter_eng.adapters.llm.openai_client import OpenAILLMClient

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


@app.command()
def edital(
    pdf: str = typer.Argument(..., help="Caminho para o PDF do edital"),
    prompt: Path = typer.Option(DEFAULT_PROMPT, help="Caminho para o template de prompt"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Ativa logs detalhados"),
) -> None:
    """Processa um edital PDF e gera resumo estruturado em Markdown."""
    _setup_logging(verbose)
    logger.info("Iniciando processamento: %s", pdf)

    settings = Settings()
    llm = OpenAILLMClient(model=settings.llm_model, api_key=settings.llm_api_key)
    prompt_template = _read_prompt(prompt)

    out = run_edital_pipeline(
        pdf_path=pdf,
        llm=llm,
        prompt_template=prompt_template,
        out_dir=settings.out_dir,
        max_chars=settings.max_chars_per_chunk,
    )
    logger.info("Arquivo gerado: %s", out)
    typer.echo(f"[OK] Gerado: {out}")


if __name__ == "__main__":
    app()
