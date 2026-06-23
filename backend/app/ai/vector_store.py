from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings
from app.core.logging import logger
from app.ai.embeddings import EMBEDDING_DIM

COLLECTION_NAME = "cortex_chunks"


@lru_cache
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL)


def ensure_collection() -> None:
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME not in existing:
        logger.info(f"Creating Qdrant collection: {COLLECTION_NAME}")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )


def store_embedding(chunk_id: int, document_id: int, text: str, embedding: list[float]) -> None:
    client = get_qdrant_client()
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=chunk_id,
                vector=embedding,
                payload={
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "text": text,
                },
            )
        ],
    )


def store_embeddings_batch(points_data: list[dict]) -> None:
    """points_data: list of {chunk_id, document_id, text, embedding}"""
    if not points_data:
        return

    client = get_qdrant_client()
    points = [
        PointStruct(
            id=p["chunk_id"],
            vector=p["embedding"],
            payload={
                "chunk_id": p["chunk_id"],
                "document_id": p["document_id"],
                "text": p["text"],
            },
        )
        for p in points_data
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)


def search_similar(query_embedding: list[float], limit: int = 5, document_id: int | None = None) -> list[dict]:
    client = get_qdrant_client()

    query_filter = None
    if document_id is not None:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        query_filter = Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=limit,
        query_filter=query_filter,
    )

    return [
        {"chunk_id": r.id, "text": r.payload["text"], "score": r.score}
        for r in results.points
    ]


def delete_document_vectors(document_id: int) -> None:
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = get_qdrant_client()
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
    )