from typing import (
    Annotated,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
)


class BibtexCitationResponse(BaseModel):
    format: Literal["bibtex"] = "bibtex"
    content: str


class CitationErrorResponse(BaseModel):
    format: Literal["error"] = "error"
    error: str
    tool_id: str


CitationItem = Annotated[BibtexCitationResponse | CitationErrorResponse, Field(discriminator="format")]
