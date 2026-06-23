from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = None


class Source(BaseModel):
    document: str
    chunk_id: int
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    conversation_id: int