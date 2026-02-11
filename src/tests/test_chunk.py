"""Testes para o step de chunking de texto."""

from dexter_eng.pipeline.steps.step_chunk import chunk_text


class TestChunkText:
    def test_single_chunk_when_text_fits(self):
        text = "Linha 1\nLinha 2\nLinha 3\n"
        chunks = chunk_text(text, max_chars=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_splits_into_multiple_chunks(self):
        # 3 linhas de 10 chars cada, max_chars=15 -> deve gerar múltiplos chunks
        text = "AAAAAAAAAA\nBBBBBBBBBB\nCCCCCCCCCC\n"
        chunks = chunk_text(text, max_chars=15)
        assert len(chunks) >= 2
        # Reconstruído deve ser igual ao original
        assert "".join(chunks) == text

    def test_empty_text(self):
        chunks = chunk_text("", max_chars=100)
        assert chunks == []

    def test_single_long_line(self):
        """Uma linha maior que max_chars deve virar um chunk sozinha."""
        line = "X" * 200 + "\n"
        chunks = chunk_text(line, max_chars=50)
        # A linha é adicionada ao chunk mesmo ultrapassando o limite
        assert len(chunks) == 1
        assert chunks[0] == line

    def test_preserves_all_content(self):
        text = "=== PAGE 1 ===\nConteúdo da página 1.\n=== PAGE 2 ===\nConteúdo da página 2.\n"
        chunks = chunk_text(text, max_chars=30)
        reconstructed = "".join(chunks)
        assert reconstructed == text
