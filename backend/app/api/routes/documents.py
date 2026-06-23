import os
import shutil
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.document import Document
from app.db.models.job import Job
from app.db.models.user import User
from app.schemas.document import DocumentResponse
from app.api.dependencies.auth import get_current_user
from app.workers.document_worker import process_document
from app.core.logging import logger

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = "storage/uploads"
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".docx"}
MAX_FILE_SIZE_MB = 25

os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = get_extension(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        logger.error(f"Failed to save uploaded file: {file.filename}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save file")
    finally:
        file.file.close()

    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit")

    doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_type=ext,
        upload_status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    job = Job(document_id=doc.id, status="pending")
    db.add(job)
    db.commit()

    process_document.delay(doc.id)
    logger.info(f"Document uploaded: doc_id={doc.id}, user_id={current_user.id}")

    return doc


@router.get("/", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.ai.vector_store import delete_document_vectors
    delete_document_vectors(document_id)

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    logger.info(f"Document deleted: doc_id={document_id}, user_id={current_user.id}")