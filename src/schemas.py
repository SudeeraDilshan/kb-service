from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class KnowledgeBaseBase(BaseModel):
    name: str

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBase(KnowledgeBaseBase):
    kb_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True for Pydantic v2

class FileMetadataCreate(BaseModel):
    filename: str
    file_size: int
    file_type: str
    kb_id: str

class FileMetadata(FileMetadataCreate):
    file_id: str
    upload_date: datetime
    
    class Config:
        from_attributes = True

class FileUploadResponse(BaseModel):
    files_uploaded: List[FileMetadata]
    message: str
