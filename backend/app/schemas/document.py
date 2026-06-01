from datetime import datetime
from pydantic import BaseModel

class DocumentResponse(BaseModel):
    id: int
    filename: str
    upload_status: str
    created_at: datetime

    class Config:
        from_attributes = True