from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict

class KnowledgeBaseBase(BaseModel):
    name: str

class KnowledgeBaseCreate(KnowledgeBaseBase):
    embedding_model: Optional[str] = None
    vector_store: Optional[str] = None

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
    file_path: str  # Added field for file path

class FileMetadata(FileMetadataCreate):
    file_id: str
    upload_date: datetime
    
    class Config:
        from_attributes = True

class FileUploadResponse(BaseModel):
    files_uploaded: List[FileMetadata]
    message: str

class EmbeddingResponse(BaseModel):
    kb_id: str
    file_count: int
    total_content_length: int
    processed_files: List[str]
    message: str
