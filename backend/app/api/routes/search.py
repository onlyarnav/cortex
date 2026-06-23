from fastapi import APIRouter, Depends, HTTPException
from app.schemas.search import SearchRequest, SearchResult
from app.ai.embeddings import generate_embedding
from app.ai.vector_store import search_similar
from app.db.models.user import User
from app.api.dependencies.auth import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=list[SearchResult])
def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    embedding = generate_embedding(request.query)
    results = search_similar(
        embedding,
        limit=request.limit,
        document_id=request.document_id,
    )
    return results