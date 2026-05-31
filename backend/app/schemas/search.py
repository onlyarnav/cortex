from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class SearchResult(BaseModel):
    chunk_id: int
    text: str
    score: float