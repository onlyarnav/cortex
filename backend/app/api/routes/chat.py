from fastapi import APIRouter, Depends
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

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get or create conversation
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
    else:
        conversation = Conversation(user_id=current_user.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Save user message
    user_msg = Message(conversation_id=conversation.id, role="user", content=request.question)
    db.add(user_msg)
    db.commit()

    # Retrieve relevant chunks
    query_embedding = generate_embedding(request.question)
    results = search_similar(query_embedding, limit=5)

    context_chunks = [r["text"] for r in results]

    # Generate answer
    answer = generate_answer(request.question, context_chunks)

    # Build sources
    sources = []
    for r in results:
        chunk = db.query(Chunk).filter(Chunk.id == r["chunk_id"]).first()
        if chunk:
            doc = db.query(Document).filter(Document.id == chunk.document_id).first()
            sources.append(Source(document=doc.filename, chunk_id=chunk.id, score=r["score"]))

    # Save assistant message
    assistant_msg = Message(conversation_id=conversation.id, role="assistant", content=answer)
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(answer=answer, sources=sources, conversation_id=conversation.id)