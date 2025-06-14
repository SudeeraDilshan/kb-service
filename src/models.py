from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.sql import func
from .database import Base
from .schemas import statusEnum
from sqlalchemy.orm import relationship

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    
    kb_id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String,index=True)  # Optional description field
    category = Column(String, index=True)  # Optional category field
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    embedding_model = Column(String, index=True)
    vector_store = Column(String, index=True)
    status = Column(String, default=statusEnum.UNSYNCED)  # Default status set to "unsynced"
    workspace_id = Column(String, nullable=True)  # Optional field for workspace ID
    created_by = Column(String, ForeignKey("users.username"), nullable=False)  # Track who created the KB
    
    # Relationship to User
    creator = relationship("User", back_populates="knowledge_bases")
    
class FileMetadata(Base):
    __tablename__ = "file_metadata"
    
    file_id = Column(String, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_size = Column(Integer)
    file_type = Column(String)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by = Column(String, ForeignKey("users.username"), nullable=False)  # Track who uploaded the file
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
    
    # Relationship to KnowledgeBase
    knowledge_bases = relationship("KnowledgeBase", back_populates="creator")