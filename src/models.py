from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.sql import func
from .database import Base
from .schemas import statusEnum

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    
    kb_id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    embedding_model = Column(String, index=True)
    vector_store = Column(String, index=True)
    status = Column(String, default=statusEnum.UNSYNCED)  # Default status set to "unsynced"
    workspace_id = Column(String, nullable=True)  # Optional field for workspace ID


class FileMetadata(Base):
    __tablename__ = "file_metadata"
    
    file_id = Column(String, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_size = Column(Integer)
    file_type = Column(String)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    kb_id = Column(String, ForeignKey("knowledge_bases.kb_id"))
    file_path = Column(String)  # Added column for storing file path
    url = Column(String, nullable=True)  # URL for accessing the file (optional)
    status = Column(String, default=statusEnum.UNSYNCED)  # Default status set to "unsynced"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
