"""Fixtures globais de teste — isolamento do banco SQLite."""

import pytest

from dexter_eng.persistence import db


@pytest.fixture(autouse=True)
def _isolate_db():
    """Usa banco in-memory por teste para evitar vazamento de cache entre testes."""
    db.init_db(":memory:")
    yield
    db.close_db()
