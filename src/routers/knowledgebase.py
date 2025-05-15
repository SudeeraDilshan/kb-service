import os
import uuid
import pathlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from datetime import datetime
from typing import List, Dict
import mimetypes
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import PyPDFLoader
# from langchain.document_loaders import JSONLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.document_loaders import UnstructuredHTMLLoader

from langchain_text_splitters import RecursiveCharacterTextSplitter

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
        created_at=datetime.now(),
        embedding_model=kb.embedding_model,
        vector_store=kb.vector_store,
        status=kb.status
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
    
    try:
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
                    kb_id=kb_id,
                    file_path=str(file_path)  # Store the absolute file path
                )
                
                # Add to database
                db.add(file_metadata)
                uploaded_files.append(file_metadata)
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file {filename}: {str(e)}"
                )
        
        # Update the last_updated_at timestamp and status for the knowledge base
        kb.last_updated_at = datetime.now()
        kb.status = schemas.statusEnum.UPDATED  # Change status to UPDATED
        
        # Commit all changes to the database
        db.commit()
        
        # Refresh to get the updated records
        for file_metadata in uploaded_files:
            db.refresh(file_metadata)
        
        return {
            "files_uploaded": uploaded_files,
            "message": f"Successfully uploaded {len(uploaded_files)} files to knowledge base {kb_id}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload files: {str(e)}"
        )
    
    
@router.get("/knowledgebases/{kb_id}/embeddings", response_model=schemas.EmbeddingResponse)
def made_embeddings(kb_id: str, db: Session = Depends(get_db)):
    # Check if knowledge base exists
    kb = db.query(models.KnowledgeBase).filter(models.KnowledgeBase.kb_id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    
    # Get path to resources directory for this knowledge base
    base_path = pathlib.Path(__file__).parent.parent
    sources_dir = base_path / "resources" / kb_id / "sources"
    
    if not os.path.exists(sources_dir):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Sources directory for knowledge base {kb_id} not found"
        )
    
    all_documents = []
    processed_files = []
    all_content = ""
    
    try:
        for filename in os.listdir(sources_dir):
            file_path = os.path.join(sources_dir, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
                
            # Get file extension
            file_extension = os.path.splitext(filename)[1].lower()
            
            loader = None
            
            # Select appropriate loader based on file extension
            try:
                # if file_extension in ['.txt', '.py', '.js', '.css', '.java', '.c', '.cpp', '.ts']:
                #     loader = TextLoader(file_path)
                if file_extension == '.csv':
                    loader = CSVLoader(file_path)
                # elif file_extension == '.json':
                #     loader = JSONLoader(file_path, jq_schema='.[]')
                elif file_extension in ['.md', '.markdown']:
                    loader = UnstructuredMarkdownLoader(file_path)
                elif file_extension in ['.html', '.htm']:
                    loader = UnstructuredHTMLLoader(file_path)
                elif file_extension == '.pdf':
                    loader = PyPDFLoader(file_path)
                # elif file_extension in ['.docx', '.doc']:
                #     loader = Docx2txtLoader(file_path)
                # elif file_extension in ['.pptx', '.ppt']:
                #     loader = UnstructuredPowerPointLoader(file_path)
                # elif file_extension in ['.xlsx', '.xls']:
                #     loader = UnstructuredExcelLoader(file_path)
                
                # If we have a supported loader, load the document
                if loader:
                    documents = loader.load()
                    all_documents.extend(documents)
                    processed_files.append(filename)
                    
                    # Extract text from documents and add to all_content
                    for doc in documents:
                        all_content += f"\n\n--- File: {filename} ---\n\n"
                        all_content += doc.page_content
                
                # print(all_content) 
                

            
            except Exception as e:
                # Log the error but continue processing other files
                print(f"Error processing {filename}: {str(e)}")
                continue
            
        text_splitter = RecursiveCharacterTextSplitter(
                                chunk_size=800,
                                chunk_overlap=80,
                                length_function=len,
                                is_separator_regex=False,
                                separators=["\n\n", "\n", " ", ""],)
                
        texts = text_splitter.create_documents([all_content]) 
                      
        print(texts[0])
        print("------------------------------------")
        print(texts[1])  
        print("------------------------------------")
        print(texts[2])
        print("------------------------------------")
        print(texts[3])  
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing files: {str(e)}"
        )
    
    # In a real application, you would:
    # 1. Split the documents into chunks
    # text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    # splits = text_splitter.split_documents(all_documents)
    # 
    # 2. Create embeddings with the model specified in the KB
    # 3. Store in the vector store specified in the KB
    
    return {
        "kb_id": kb_id,
        "file_count": len(processed_files),
        "total_content_length": len(all_content),
        "processed_files": processed_files,
        "message": f"Processed {len(processed_files)} files from knowledge base {kb_id}"
    }

