import os

import pypdf

from app.core.celery_app import celery_app
from app.core.logging import logger
from app.db.session import SessionLocal
from app.db.models.document import Document
from app.db.models.chunk import Chunk
from app.db.models.job import Job
from app.ai.embeddings import generate_embeddings_batch
from app.ai.vector_store import ensure_collection, store_embeddings_batch

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        reader = pypdf.PdfReader(file_path)
        return "".join(page.extract_text() or "" for page in reader.pages)

    if ext in (".md", ".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    if ext == ".docx":
        import docx
        doc = docx.Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)

    raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap

    return chunks


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def process_document(self, document_id: int):
    db = SessionLocal()
    doc = None
    job = None

    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.warning(f"Document not found: doc_id={document_id}")
            return

        job = db.query(Job).filter(Job.document_id == document_id).first()

        doc.upload_status = "processing"
        if job:
            job.status = "processing"
        db.commit()

        text = extract_text(doc.file_path)
        if not text.strip():
            raise ValueError("No extractable text found in document")

        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("Document produced zero chunks")

        chunk_records = [
            Chunk(document_id=doc.id, chunk_index=i, text=chunk)
            for i, chunk in enumerate(chunks)
        ]
        db.add_all(chunk_records)
        db.commit()

        ensure_collection()

        embeddings = generate_embeddings_batch([c.text for c in chunk_records])
        points_data = [
            {
                "chunk_id": chunk.id,
                "document_id": doc.id,
                "text": chunk.text,
                "embedding": embedding,
            }
            for chunk, embedding in zip(chunk_records, embeddings)
        ]
        store_embeddings_batch(points_data)

        doc.upload_status = "done"
        if job:
            job.status = "done"
        db.commit()

        logger.info(f"Document processed successfully: doc_id={doc.id}, chunks={len(chunks)}")

    except Exception as e:
        logger.error(f"Document processing failed: doc_id={document_id}, error={e}", exc_info=True)
        if doc:
            doc.upload_status = "failed"
        if job:
            job.status = "failed"
            job.error = str(e)
        db.commit()

    finally:
        db.close()