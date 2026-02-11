"""Persistência SQLite para rastreamento de documentos, execuções e cache LLM."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_PATH: Path = Path("dexter.db")
_conn: Optional[sqlite3.Connection] = None
_initialized: bool = False

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
        _conn.commit()
        _initialized = True
    return _conn


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
        "INSERT INTO runs (document_id, pipeline_version, model, started_at, status) VALUES (?, ?, ?, ?, ?)",
        (document_id, pipeline_version, model, now, "running"),
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


def save_cached_response(prompt_hash: str, model: str, response_text: str) -> None:
    """Salva resposta da LLM no cache."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO llm_cache (prompt_hash, model, response_text, created_at) VALUES (?, ?, ?, ?)",
        (prompt_hash, model, response_text, now),
    )
    conn.commit()


def close_db() -> None:
    """Fecha a conexão com o banco."""
    global _conn, _initialized
    if _conn is not None:
        _conn.close()
        _conn = None
        _initialized = False
