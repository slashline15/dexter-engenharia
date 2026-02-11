"""Persistência SQLite para rastreamento de documentos, execuções e cache LLM."""

from __future__ import annotations

import logging
import sqlite3
from hashlib import sha256
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_PATH: Path = Path("dexter.db")
_conn: Optional[sqlite3.Connection] = None
_initialized: bool = False

_RUNS_ADDITIONAL_COLUMNS = {
    "prompt_chars": "INTEGER",
    "response_chars": "INTEGER",
    "cache_hit": "INTEGER",
    "llm_model": "TEXT",
    "request_id": "TEXT",
}

_LLM_CACHE_ADDITIONAL_COLUMNS = {
    "prompt_chars": "INTEGER",
    "response_chars": "INTEGER",
    "response_sha256": "TEXT",
}

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    path TEXT,
    sha256 TEXT UNIQUE,
    pages INTEGER,
    chars INTEGER,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    document_id INTEGER,
    pipeline_version TEXT,
    model TEXT,
    started_at TEXT,
    ended_at TEXT,
    status TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS llm_cache (
    id INTEGER PRIMARY KEY,
    prompt_hash TEXT UNIQUE,
    model TEXT,
    response_text TEXT,
    created_at TEXT
);
"""


def _get_conn() -> sqlite3.Connection:
    global _conn, _initialized
    if _conn is None:
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    if not _initialized:
        _conn.executescript(_CREATE_TABLES_SQL)
        migrate_db_if_needed(_conn)
        _conn.commit()
        _initialized = True
    return _conn


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def migrate_db_if_needed(conn: sqlite3.Connection | None = None) -> None:
    """Aplica migrações leves com ALTER TABLE quando necessário."""
    active_conn = conn or _get_conn()

    runs_columns = _get_table_columns(active_conn, "runs")
    for col, col_type in _RUNS_ADDITIONAL_COLUMNS.items():
        if col not in runs_columns:
            logger.info("Aplicando migração: runs.%s", col)
            active_conn.execute(f"ALTER TABLE runs ADD COLUMN {col} {col_type}")

    llm_cache_columns = _get_table_columns(active_conn, "llm_cache")
    for col, col_type in _LLM_CACHE_ADDITIONAL_COLUMNS.items():
        if col not in llm_cache_columns:
            logger.info("Aplicando migração: llm_cache.%s", col)
            active_conn.execute(f"ALTER TABLE llm_cache ADD COLUMN {col} {col_type}")


def init_db(db_path: str | Path | None = None) -> None:
    """Inicializa o banco e cria tabelas se não existirem."""
    global _DB_PATH, _conn, _initialized
    if db_path is not None:
        _DB_PATH = Path(db_path)
    # Fecha conexão anterior se houver
    if _conn is not None:
        _conn.close()
        _conn = None
        _initialized = False

    _get_conn()  # Abre conexão e cria tabelas automaticamente
    logger.info("Banco SQLite inicializado: %s", _DB_PATH)


def get_or_create_document(
    path: str, sha256: str, pages: int, chars: int
) -> int:
    """Retorna ID do documento, criando se não existir."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT id FROM documents WHERE sha256 = ?", (sha256,)
    ).fetchone()
    if row:
        return row["id"]

    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO documents (path, sha256, pages, chars, created_at) VALUES (?, ?, ?, ?, ?)",
        (path, sha256, pages, chars, now),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def create_run(document_id: int, model: str, pipeline_version: str) -> int:
    """Cria um registro de execução e retorna o ID."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """
        INSERT INTO runs (document_id, pipeline_version, model, llm_model, started_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (document_id, pipeline_version, model, model, now, "running"),
    )
    conn.commit()
    logger.info("Run #%d criado (doc_id=%d, model=%s)", cur.lastrowid, document_id, model)
    return cur.lastrowid  # type: ignore[return-value]


def finish_run(run_id: int, status: str, error: str | None = None) -> None:
    """Finaliza uma execução com status e possível erro."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE runs SET ended_at = ?, status = ?, error = ? WHERE id = ?",
        (now, status, error, run_id),
    )
    conn.commit()
    logger.info("Run #%d finalizado (status=%s)", run_id, status)


def record_run_metrics(
    run_id: int,
    *,
    prompt_chars: int,
    response_chars: int,
    cache_hit: bool,
    request_id: str | None,
) -> None:
    """Atualiza métricas de uso/custo da etapa de LLM na run."""
    conn = _get_conn()
    conn.execute(
        """
        UPDATE runs
        SET prompt_chars = ?, response_chars = ?, cache_hit = ?, request_id = ?
        WHERE id = ?
        """,
        (prompt_chars, response_chars, int(cache_hit), request_id, run_id),
    )
    conn.commit()


def get_run_history(limit: int = 20) -> list[sqlite3.Row]:
    """Retorna histórico de runs recentes para relatórios CLI."""
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT
            id,
            status,
            cache_hit,
            prompt_chars,
            response_chars,
            COALESCE(llm_model, model) AS model,
            started_at,
            ended_at
        FROM runs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return list(rows)


def get_cache_stats() -> dict[str, float | int]:
    """Retorna estatísticas do cache com base nas runs registradas."""
    conn = _get_conn()
    cache_entries = conn.execute("SELECT COUNT(*) AS total FROM llm_cache").fetchone()["total"]
    total_runs = conn.execute("SELECT COUNT(*) AS total FROM runs").fetchone()["total"]
    cache_hits = conn.execute(
        "SELECT COUNT(*) AS total FROM runs WHERE cache_hit = 1"
    ).fetchone()["total"]
    hit_rate = (cache_hits / total_runs) if total_runs else 0.0
    return {
        "total_entries": int(cache_entries),
        "total_runs": int(total_runs),
        "cache_hits": int(cache_hits),
        "hit_rate": float(hit_rate),
    }


def get_cached_response(prompt_hash: str, model: str) -> Optional[str]:
    """Consulta cache de resposta LLM por hash de prompt."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT response_text FROM llm_cache WHERE prompt_hash = ? AND model = ?",
        (prompt_hash, model),
    ).fetchone()
    if row:
        return row["response_text"]
    return None


def save_cached_response(
    prompt_hash: str,
    model: str,
    response_text: str,
    *,
    prompt_chars: int | None = None,
    response_chars: int | None = None,
) -> None:
    """Salva resposta da LLM no cache."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    resolved_prompt_chars = prompt_chars
    resolved_response_chars = response_chars if response_chars is not None else len(response_text)
    response_digest = sha256(response_text.encode("utf-8")).hexdigest()
    conn.execute(
        """
        INSERT OR IGNORE INTO llm_cache
        (prompt_hash, model, response_text, created_at, prompt_chars, response_chars, response_sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            prompt_hash,
            model,
            response_text,
            now,
            resolved_prompt_chars,
            resolved_response_chars,
            response_digest,
        ),
    )
    conn.commit()


def close_db() -> None:
    """Fecha a conexão com o banco."""
    global _conn, _initialized
    if _conn is not None:
        _conn.close()
        _conn = None
        _initialized = False
