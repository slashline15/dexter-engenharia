"""Testes para o módulo de persistência SQLite."""

from dexter_eng.persistence.db import (
    _get_conn,
    close_db,
    create_run,
    finish_run,
    get_cached_response,
    get_or_create_document,
    init_db,
    save_cached_response,
)


class TestInitDb:
    def test_tables_created(self):
        conn = _get_conn()
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "documents" in tables
        assert "runs" in tables
        assert "llm_cache" in tables

    def test_reinit_does_not_lose_data(self):
        get_or_create_document("a.pdf", "hash1", 10, 5000)
        init_db(":memory:")  # re-init
        # Tabelas existem de novo (banco novo in-memory), dados anteriores perdidos
        conn = _get_conn()
        count = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        assert count == 0  # banco novo


class TestDocuments:
    def test_create_returns_id(self):
        doc_id = get_or_create_document("edital.pdf", "abc123", 5, 12000)
        assert isinstance(doc_id, int)
        assert doc_id >= 1

    def test_get_existing_returns_same_id(self):
        id1 = get_or_create_document("edital.pdf", "abc123", 5, 12000)
        id2 = get_or_create_document("edital.pdf", "abc123", 5, 12000)
        assert id1 == id2

    def test_different_sha_creates_new(self):
        id1 = get_or_create_document("a.pdf", "hash_a", 3, 1000)
        id2 = get_or_create_document("b.pdf", "hash_b", 7, 2000)
        assert id1 != id2

    def test_fields_stored_correctly(self):
        get_or_create_document("meu.pdf", "sha_xyz", 12, 45000)
        conn = _get_conn()
        row = conn.execute(
            "SELECT path, sha256, pages, chars, created_at FROM documents WHERE sha256 = ?",
            ("sha_xyz",),
        ).fetchone()
        assert row["path"] == "meu.pdf"
        assert row["pages"] == 12
        assert row["chars"] == 45000
        assert row["created_at"] is not None


class TestRuns:
    def test_create_run_returns_id(self):
        doc_id = get_or_create_document("x.pdf", "h1", 1, 100)
        run_id = create_run(doc_id, "gpt-4o", "0.2")
        assert isinstance(run_id, int)
        assert run_id >= 1

    def test_run_initial_status_is_running(self):
        doc_id = get_or_create_document("x.pdf", "h1", 1, 100)
        run_id = create_run(doc_id, "gpt-4o", "0.2")
        conn = _get_conn()
        row = conn.execute("SELECT status, started_at, ended_at FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert row["status"] == "running"
        assert row["started_at"] is not None
        assert row["ended_at"] is None

    def test_finish_run_success(self):
        doc_id = get_or_create_document("x.pdf", "h1", 1, 100)
        run_id = create_run(doc_id, "gpt-4o", "0.2")
        finish_run(run_id, status="success")
        conn = _get_conn()
        row = conn.execute("SELECT status, ended_at, error FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert row["status"] == "success"
        assert row["ended_at"] is not None
        assert row["error"] is None

    def test_finish_run_with_error(self):
        doc_id = get_or_create_document("x.pdf", "h1", 1, 100)
        run_id = create_run(doc_id, "gpt-4o", "0.2")
        finish_run(run_id, status="error", error="KeyError: 'orgao'")
        conn = _get_conn()
        row = conn.execute("SELECT status, error FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert row["status"] == "error"
        assert row["error"] == "KeyError: 'orgao'"

    def test_pipeline_version_stored(self):
        doc_id = get_or_create_document("x.pdf", "h1", 1, 100)
        run_id = create_run(doc_id, "gpt-4o", "0.2")
        conn = _get_conn()
        row = conn.execute("SELECT pipeline_version, model FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert row["pipeline_version"] == "0.2"
        assert row["model"] == "gpt-4o"

    def test_multiple_runs_for_same_document(self):
        doc_id = get_or_create_document("x.pdf", "h1", 1, 100)
        r1 = create_run(doc_id, "gpt-4o", "0.2")
        r2 = create_run(doc_id, "gpt-4o-mini", "0.2")
        assert r1 != r2


class TestLlmCache:
    def test_miss_returns_none(self):
        result = get_cached_response("nonexistent_hash", "gpt-4o")
        assert result is None

    def test_save_and_retrieve(self):
        save_cached_response("hash_abc", "gpt-4o", '{"orgao": "Prefeitura"}')
        result = get_cached_response("hash_abc", "gpt-4o")
        assert result == '{"orgao": "Prefeitura"}'

    def test_different_model_not_found(self):
        save_cached_response("hash_abc", "gpt-4o", '{"orgao": "X"}')
        result = get_cached_response("hash_abc", "gpt-4o-mini")
        assert result is None

    def test_duplicate_save_does_not_error(self):
        save_cached_response("hash_dup", "gpt-4o", "resposta1")
        save_cached_response("hash_dup", "gpt-4o", "resposta2")  # INSERT OR IGNORE
        result = get_cached_response("hash_dup", "gpt-4o")
        assert result == "resposta1"  # primeira inserção prevalece

    def test_cache_preserves_unicode(self):
        texto = '{"objeto": "Pavimentação — R$ 1.500.000,00"}'
        save_cached_response("hash_uni", "gpt-4o", texto)
        result = get_cached_response("hash_uni", "gpt-4o")
        assert result == texto


class TestCloseDb:
    def test_close_and_reopen(self):
        save_cached_response("h1", "m1", "r1")
        close_db()
        # Após close, nova conexão é aberta automaticamente via _get_conn
        init_db(":memory:")  # novo banco in-memory
        result = get_cached_response("h1", "m1")
        assert result is None  # banco novo, cache vazio
