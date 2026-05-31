import os
from sentence_transformers import SentenceTransformer
from app.core.config import settings

os.environ["HF_TOKEN"] = settings.HF_TOKEN
model = SentenceTransformer("all-MiniLM-L6-v2")

def generate_embedding(text: str) -> list[float]:
    return model.encode(text).tolist()
