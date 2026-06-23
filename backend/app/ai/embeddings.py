import os
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logging import logger

os.environ["HF_TOKEN"] = settings.HF_TOKEN

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def generate_embedding(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Cannot generate embedding for empty text")

    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return embeddings.tolist()