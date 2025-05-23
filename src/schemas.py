from pydantic import BaseModel, HttpUrl, EmailStr
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum

class statusEnum(str, Enum):
    EMPTY = "empty"
    UPDATED = "updated"
    EMBEDDED = "embedded"

class KnowledgeBaseBase(BaseModel):
    name: str
    status : statusEnum = statusEnum.EMPTY
    
class KnowledgeBaseCreate(KnowledgeBaseBase):
    embedding_model: Optional[str] = None
    vector_store: Optional[str] = None

class KnowledgeBase(KnowledgeBaseCreate):
    kb_id: str
    created_at: datetime
    last_updated_at: datetime
    
    class Config:
        from_attributes = True  # Updated from orm_mode = True for Pydantic v2

class FileMetadataCreate(BaseModel):
    filename: str
    file_size: int
    file_type: str
    kb_id: str
    file_path: str  # Added field for file path
    url: Optional[str] = None  # Optional URL field

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

class DeleteResponse(BaseModel):
    kb_id: str
    message: str
    deleted_files: int

class DeleteFileResponse(BaseModel):
    kb_id: str
    file_id: str
    filename: str
    message: str

class UrlSubmission(BaseModel):
    url: HttpUrl

class UrlSubmissionResponse(BaseModel):
    kb_id: str
    file_id: str
    url: str
    filename: str
    file_size: int
    message: str

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    is_admin: Optional[bool] = False

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
