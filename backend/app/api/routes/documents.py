from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.document import Document
from app.db.models.user import User
from app.db.models.job import Job
from app.schemas.document import DocumentResponse
from app.api.dependencies.auth import get_current_user
from app.workers.document_worker import process_document
import shutil, uuid, os

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = "storage/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

def get_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()

@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):

    if get_extension(file.filename) not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")

    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_type=get_extension(file.filename),
        upload_status="pending"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    job = Job(document_id=doc.id, status="pending")
    db.add(job)
    db.commit()
    process_document.delay(doc.id)
    
    return doc

@router.get("/", response_model=list[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Document).filter(Document.user_id == current_user.id).all()