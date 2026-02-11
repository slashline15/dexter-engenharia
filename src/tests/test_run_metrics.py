"""Testes para métricas de run e estatísticas de cache."""

from dexter_eng.persistence.db import (
    _get_conn,
    create_run,
    get_cache_stats,
    get_or_create_document,
    get_run_history,
    record_run_metrics,
)


def test_record_run_metrics_updates_run_fields():
    doc_id = get_or_create_document("x.pdf", "sha-x", 2, 200)
    run_id = create_run(doc_id, "gpt-4o", "0.2")

    record_run_metrics(
        run_id,
        prompt_chars=123,
        response_chars=456,
        cache_hit=True,
        request_id="req_123",
    )

    row = _get_conn().execute(
        "SELECT prompt_chars, response_chars, cache_hit, request_id FROM runs WHERE id = ?",
        (run_id,),
    ).fetchone()

    assert row["prompt_chars"] == 123
    assert row["response_chars"] == 456
    assert row["cache_hit"] == 1
    assert row["request_id"] == "req_123"


def test_get_run_history_returns_recent_runs_with_metrics():
    doc_id = get_or_create_document("history.pdf", "sha-history", 1, 100)
    run_a = create_run(doc_id, "model-a", "0.2")
    run_b = create_run(doc_id, "model-b", "0.2")

    record_run_metrics(run_a, prompt_chars=10, response_chars=20, cache_hit=False, request_id=None)
    record_run_metrics(run_b, prompt_chars=30, response_chars=40, cache_hit=True, request_id=None)

    history = get_run_history(limit=2)

    assert len(history) == 2
    assert history[0]["id"] == run_b
    assert history[0]["model"] == "model-b"
    assert history[0]["cache_hit"] == 1
    assert history[1]["id"] == run_a


def test_get_cache_stats_uses_run_cache_hits():
    doc_id = get_or_create_document("stats.pdf", "sha-stats", 1, 100)
    run_1 = create_run(doc_id, "m", "0.2")
    run_2 = create_run(doc_id, "m", "0.2")
    run_3 = create_run(doc_id, "m", "0.2")

    record_run_metrics(run_1, prompt_chars=1, response_chars=2, cache_hit=False, request_id=None)
    record_run_metrics(run_2, prompt_chars=1, response_chars=2, cache_hit=True, request_id=None)
    record_run_metrics(run_3, prompt_chars=1, response_chars=2, cache_hit=True, request_id=None)

    stats = get_cache_stats()

    assert stats["total_runs"] == 3
    assert stats["cache_hits"] == 2
    assert stats["hit_rate"] == 2 / 3
