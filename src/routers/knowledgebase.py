import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from datetime import datetime
import pathlib
from typing import List

router = APIRouter()

@router.post("/knowledgebases", response_model=schemas.KnowledgeBase)
def create_knowledge_base(kb: schemas.KnowledgeBaseCreate, db: Session = Depends(get_db)):
    # Get the next KB ID (simple implementation)
    last_kb = db.query(models.KnowledgeBase).order_by(models.KnowledgeBase.kb_id.desc()).first()
    
    if last_kb:
        # Extract the number from kb_id and increment
        last_id = int(last_kb.kb_id.split('_')[1])
        new_id = last_id + 1
    else:
        new_id = 1
    
    kb_id = f"kb_{new_id}"
    
    # Create KB directory structure
    base_path = pathlib.Path(__file__).parent.parent
    kb_dir = base_path / "resources" /kb_id
    sources_dir = kb_dir / "sources"
    
    try:
        os.makedirs(sources_dir, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create directory: {str(e)}")
    
    # Create knowledge base in database
    db_kb = models.KnowledgeBase(
        kb_id=kb_id,
        name=kb.name,
        created_at=datetime.now()
    )
    
    db.add(db_kb)
    db.commit()
    db.refresh(db_kb)
    
    return db_kb

@router.post("/knowledgebases/{kb_id}/upload", response_model=schemas.FileUploadResponse)
async def upload_files(
    kb_id: str, 
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    # Check if knowledge base exists
    kb = db.query(models.KnowledgeBase).filter(models.KnowledgeBase.kb_id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    
    # Define path to save files
    base_path = pathlib.Path(__file__).parent.parent
    sources_dir = base_path / "resources" / kb_id / "sources"
    
    # Make sure the directory exists
    os.makedirs(sources_dir, exist_ok=True)
    
    uploaded_files = []
    
    for file in files:
        # Generate unique file ID
        file_id = f"file_{uuid.uuid4()}"
        
        # Get file extension and determine file type
        filename = file.filename
        file_extension = os.path.splitext(filename)[1].lower()
        
        # Create full path to save the file
        file_path = os.path.join(sources_dir, filename)
        
        # Save the file
        try:
            # Read file content
            contents = await file.read()
            
            # Write file to disk
            with open(file_path, "wb") as f:
                f.write(contents)
            
            # Create file metadata entry
            file_metadata = models.FileMetadata(
                file_id=file_id,
                filename=filename,
                file_size=len(contents),
                file_type=file_extension.replace(".", ""),
                kb_id=kb_id
            )
            
            # Add to database
            db.add(file_metadata)
            db.commit()
            db.refresh(file_metadata)
            
            uploaded_files.append(file_metadata)
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file {filename}: {str(e)}"
            )
    
    return {
        "files_uploaded": uploaded_files,
        "message": f"Successfully uploaded {len(uploaded_files)} files to knowledge base {kb_id}"
    }
