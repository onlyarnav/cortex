from fastapi import APIRouter, Depends
from app.schemas.search import SearchRequest, SearchResult
from app.ai.embeddings import generate_embedding
from app.ai.vector_store import search_similar
from app.db.models.user import User
from app.api.dependencies.auth import get_current_user

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/", response_model=list[SearchResult])
def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    embedding = generate_embedding(request.query)
    results = search_similar(embedding, limit=request.limit)
    return results