from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    document_id: int | None = None


class SearchResult(BaseModel):
    chunk_id: int
    text: str
    score: float