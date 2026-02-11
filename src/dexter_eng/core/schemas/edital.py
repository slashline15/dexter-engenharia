from pydantic import BaseModel, Field, BeforeValidator
from typing import List, Optional, Any
from typing_extensions import Annotated

def extract_string_from_dict(v: Any) -> Any:
    """
    Corrige alucinação comum de LLMs locais que retornam
    {'title': '...'} onde deveria ser apenas '...'.
    """
    if isinstance(v, dict):
        # Tenta pegar o primeiro valor string que encontrar
        for key, val in v.items():
            if isinstance(val, str):
                return val
    return v

# Cria um tipo "RobustString" que aceita str ou tenta extrair de dict
RobustString = Annotated[str, BeforeValidator(extract_string_from_dict)]

class Citation(BaseModel):
    page: int = Field(..., ge=1)
    excerpt: RobustString = Field(..., min_length=1)

class Requirement(BaseModel):
    title: RobustString
    description: RobustString
    citations: List[Citation] = Field(default_factory=list)

class Deadline(BaseModel):
    name: RobustString
    date_text: RobustString
    citations: List[Citation] = Field(default_factory=list)

class EditalExtraction(BaseModel):
    orgao: Optional[RobustString] = None
    objeto: Optional[RobustString] = None

    prazos: List[Deadline] = Field(default_factory=list)
    documentos_exigidos: List[Requirement] = Field(default_factory=list)
    criterios_habilitacao: List[Requirement] = Field(default_factory=list)
    penalidades: List[Requirement] = Field(default_factory=list)

    pendencias: List[RobustString] = Field(default_factory=list)  # coisas que faltaram/ambíguas