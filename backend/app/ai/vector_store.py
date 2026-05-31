from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings

client = QdrantClient(url=settings.QDRANT_URL)

COLLECTION_NAME = "cortex_chunks"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output size

def ensure_collection():
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
        )

def store_embedding(chunk_id: int, document_id: int, text: str, embedding: list[float]):
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=chunk_id,
                vector=embedding,
                payload={"chunk_id": chunk_id, "document_id": document_id, "text": text}
            )
        ]
    )

def search_similar(query_embedding: list[float], limit: int = 5) -> list[dict]:
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=limit
    )
    return [{"chunk_id": r.id, "text": r.payload["text"], "score": r.score} for r in results.points]