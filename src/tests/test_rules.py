"""Testes para as regras de pós-processamento do edital."""

from dexter_eng.core.rules.edital_rules import apply_edital_rules
from dexter_eng.core.schemas.edital import EditalExtraction


class TestApplyEditalRules:
    def test_strips_whitespace(self):
        ex = EditalExtraction(pendencias=["  item com espaços  ", "ok"])
        result = apply_edital_rules(ex)
        assert result.pendencias == ["item com espaços", "ok"]

    def test_removes_empty_strings(self):
        ex = EditalExtraction(pendencias=["válido", "", "  ", "outro válido"])
        result = apply_edital_rules(ex)
        assert result.pendencias == ["válido", "outro válido"]

    def test_empty_pendencias_unchanged(self):
        ex = EditalExtraction(pendencias=[])
        result = apply_edital_rules(ex)
        assert result.pendencias == []

    def test_preserves_other_fields(self):
        ex = EditalExtraction(orgao="Teste", pendencias=["  a  "])
        result = apply_edital_rules(ex)
        assert result.orgao == "Teste"
        assert result.pendencias == ["a"]
