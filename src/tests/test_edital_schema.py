"""Testes para os schemas Pydantic do edital."""

import pytest
from pydantic import ValidationError

from dexter_eng.core.schemas.edital import (
    Citation,
    Deadline,
    EditalExtraction,
    Requirement,
)


class TestCitation:
    def test_valid(self):
        c = Citation(page=1, excerpt="texto de exemplo")
        assert c.page == 1
        assert c.excerpt == "texto de exemplo"

    def test_page_zero_rejected(self):
        with pytest.raises(ValidationError):
            Citation(page=0, excerpt="texto")

    def test_page_negative_rejected(self):
        with pytest.raises(ValidationError):
            Citation(page=-1, excerpt="texto")

    def test_empty_excerpt_rejected(self):
        with pytest.raises(ValidationError):
            Citation(page=1, excerpt="")


class TestRequirement:
    def test_valid_without_citations(self):
        r = Requirement(title="Certidão", description="Certidão negativa de débitos")
        assert r.title == "Certidão"
        assert r.citations == []

    def test_valid_with_citations(self):
        r = Requirement(
            title="Doc",
            description="Desc",
            citations=[Citation(page=3, excerpt="ver item 5.1")],
        )
        assert len(r.citations) == 1
        assert r.citations[0].page == 3


class TestDeadline:
    def test_valid(self):
        d = Deadline(name="Entrega propostas", date_text="15/03/2025")
        assert d.name == "Entrega propostas"
        assert d.date_text == "15/03/2025"


class TestEditalExtraction:
    def test_minimal_valid(self):
        e = EditalExtraction()
        assert e.orgao is None
        assert e.objeto is None
        assert e.prazos == []
        assert e.documentos_exigidos == []
        assert e.pendencias == []

    def test_full_valid(self):
        e = EditalExtraction(
            orgao="Prefeitura Municipal",
            objeto="Construção de ponte",
            prazos=[Deadline(name="Abertura", date_text="01/04/2025")],
            documentos_exigidos=[
                Requirement(title="CNPJ", description="Comprovante de inscrição")
            ],
            criterios_habilitacao=[],
            penalidades=[],
            pendencias=["Valor estimado não informado"],
        )
        assert e.orgao == "Prefeitura Municipal"
        assert len(e.prazos) == 1
        assert len(e.documentos_exigidos) == 1
        assert len(e.pendencias) == 1

    def test_model_validate_from_dict(self):
        """Simula o que step_llm_structured faz com o JSON da LLM."""
        payload = {
            "orgao": "DNIT",
            "objeto": "Pavimentação",
            "prazos": [
                {
                    "name": "Abertura",
                    "date_text": "10/05/2025",
                    "citations": [{"page": 2, "excerpt": "conforme item 3.1"}],
                }
            ],
            "documentos_exigidos": [],
            "criterios_habilitacao": [],
            "penalidades": [],
            "pendencias": [],
        }
        e = EditalExtraction.model_validate(payload)
        assert e.orgao == "DNIT"
        assert e.prazos[0].citations[0].page == 2

    def test_extra_fields_ignored(self):
        """LLM pode retornar campos extras; devem ser ignorados."""
        payload = {
            "orgao": "Teste",
            "campo_inventado": "valor",
        }
        e = EditalExtraction.model_validate(payload)
        assert e.orgao == "Teste"
