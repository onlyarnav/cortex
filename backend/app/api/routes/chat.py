from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.schemas.chat import ChatRequest, ChatResponse, Source
from app.api.dependencies.auth import get_current_user
from app.ai.embeddings import generate_embedding
from app.ai.vector_store import search_similar
from app.ai.llm import generate_answer
from app.core.logging import logger
from app.core.limiter import limiter

router = APIRouter(prefix="/chat", tags=["chat"])

SEARCH_LIMIT = 5


def get_or_create_conversation(db: Session, user_id: int, conversation_id: int | None) -> Conversation:
    if conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    conversation = Conversation(user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/", response_model=ChatResponse)
@limiter.limit("10/minute")
def chat(
    request: Request,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    conversation = get_or_create_conversation(db, current_user.id, body.conversation_id)

    db.add(Message(conversation_id=conversation.id, role="user", content=body.question))
    db.commit()

    query_embedding = generate_embedding(body.question)
    results = search_similar(query_embedding, limit=SEARCH_LIMIT)
    context_chunks = [r["text"] for r in results]

    try:
        answer = generate_answer(body.question, context_chunks)
    except Exception:
        logger.error(f"Chat generation failed for conversation_id={conversation.id}", exc_info=True)
        raise HTTPException(status_code=502, detail="LLM service unavailable, try again")

    sources = []
    for r in results:
        chunk = db.query(Chunk).filter(Chunk.id == r["chunk_id"]).first()
        if chunk:
            doc = db.query(Document).filter(Document.id == chunk.document_id).first()
            if doc:
                sources.append(Source(document=doc.filename, chunk_id=chunk.id, score=r["score"]))

    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()

    return ChatResponse(answer=answer, sources=sources, conversation_id=conversation.id)