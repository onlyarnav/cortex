from pydantic import BaseModel

class ChatRequest(BaseModel):
    question: str
    conversation_id: int | None = None

class Source(BaseModel):
    document: str
    chunk_id: int
    score: float

class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    conversation_id: int