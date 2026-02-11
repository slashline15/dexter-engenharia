"""Testes de migração automática do SQLite legado."""

import sqlite3

from dexter_eng.persistence import db


def _create_legacy_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
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
    )
    conn.commit()
    conn.close()


def _table_columns(conn, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_migration_adds_new_columns(tmp_path):
    db_path = tmp_path / "legacy.db"
    _create_legacy_db(str(db_path))

    db.init_db(db_path)
    conn = db._get_conn()

    runs_columns = _table_columns(conn, "runs")
    assert "prompt_chars" in runs_columns
    assert "response_chars" in runs_columns
    assert "cache_hit" in runs_columns
    assert "llm_model" in runs_columns
    assert "request_id" in runs_columns

    llm_cache_columns = _table_columns(conn, "llm_cache")
    assert "prompt_chars" in llm_cache_columns
    assert "response_chars" in llm_cache_columns
    assert "response_sha256" in llm_cache_columns


def test_migration_preserves_legacy_data(tmp_path):
    db_path = tmp_path / "legacy_with_data.db"
    _create_legacy_db(str(db_path))

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO runs (document_id, pipeline_version, model, started_at, status) VALUES (?, ?, ?, ?, ?)",
        (1, "0.2", "gpt-4o", "2026-01-01T00:00:00+00:00", "running"),
    )
    conn.commit()
    conn.close()

    db.init_db(db_path)
    conn2 = db._get_conn()
    row = conn2.execute("SELECT model, status FROM runs WHERE id = 1").fetchone()
    assert row["model"] == "gpt-4o"
    assert row["status"] == "running"
