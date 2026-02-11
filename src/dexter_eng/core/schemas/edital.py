from pydantic import BaseModel, Field
from typing import List, Optional

class Citation(BaseModel):
    page: int = Field(..., ge=1)
    excerpt: str = Field(..., min_length=1)

class Requirement(BaseModel):
    title: str
    description: str
    citations: List[Citation] = Field(default_factory=list)

class Deadline(BaseModel):
    name: str
    date_text: str
    citations: List[Citation] = Field(default_factory=list)

class EditalExtraction(BaseModel):
    orgao: Optional[str] = None
    objeto: Optional[str] = None

    prazos: List[Deadline] = Field(default_factory=list)
    documentos_exigidos: List[Requirement] = Field(default_factory=list)
    criterios_habilitacao: List[Requirement] = Field(default_factory=list)
    penalidades: List[Requirement] = Field(default_factory=list)

    pendencias: List[str] = Field(default_factory=list)  # coisas que faltaram/ambíguas