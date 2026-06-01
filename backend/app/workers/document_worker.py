import os
import pypdf

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.document import Document
from app.db.models.chunk import Chunk
from app.db.models.job import Job
from app.ai.embeddings import generate_embedding
from app.ai.vector_store import ensure_collection, store_embedding


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        reader = pypdf.PdfReader(file_path)
        return "".join([page.extract_text() or "" for page in reader.pages])

    elif ext in (".md", ".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    elif ext == ".docx":
        import docx
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


@celery_app.task
def process_document(document_id: int):
    db = SessionLocal()
    doc = None
    job = None
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        job = db.query(Job).filter(Job.document_id == document_id).first()

        doc.upload_status = "processing"
        job.status = "processing"
        db.commit()

        text = extract_text(doc.file_path)

        chunks = chunk_text(text)

        for i, chunk_text_piece in enumerate(chunks):
            chunk = Chunk(
                document_id=doc.id,
                chunk_index=i,
                text=chunk_text_piece
            )
            db.add(chunk)

        db.commit()

        ensure_collection()

        chunks_in_db = db.query(Chunk).filter(Chunk.document_id == doc.id).all()
        for chunk in chunks_in_db:
            embedding = generate_embedding(chunk.text)
            store_embedding(chunk.id, doc.id, chunk.text, embedding)

        doc.upload_status = "done"
        job.status = "done"
        db.commit()

    except Exception as e:
        if doc:
            doc.upload_status = "failed"
        if job:
            job.status = "failed"
            job.error = str(e)
        db.commit()

    finally:
        db.close()