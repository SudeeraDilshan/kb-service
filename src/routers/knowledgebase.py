import os
import uuid
import pathlib
import shutil
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File,status
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from datetime import datetime
from typing import List
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain_community.document_loaders.word_document import Docx2txtLoader
from langchain_community.document_loaders.text import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..vector_stores import add_to_vectorStore
from ..security.utils import get_current_active_user, validate_admin
# from langchain_community.document_loaders import JSONLoader
# import json

router = APIRouter()

@router.post("/knowledgebases", response_model=schemas.KnowledgeBase)
def create_knowledge_base(
    kb: schemas.KnowledgeBaseCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
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
            filename = f"{file_id}_"+file.filename
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
                    filename=file.filename,
                    file_size=len(contents),
                    file_type=file_extension.replace(".", ""),
                    kb_id=kb_id,
                    file_path=str(file_path),
                    # url=file_url  # Store the URL
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
def made_embeddings(
    kb_id: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
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
    all_chunks=[]
    
    try:
        for filename in os.listdir(sources_dir):
            file_path = os.path.join(sources_dir, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
                
            # Get file extension
            name_without_ext,file_extension = os.path.splitext(filename)
            file_extension = file_extension.lower()
            
            main_part = name_without_ext.split('_', 2)[:2]
            file_id = '_'.join(main_part)
            loader = None
            
            # get file data
            file_metadata = db.query(models.FileMetadata).filter(
                models.FileMetadata.file_id == file_id,
                models.FileMetadata.kb_id == kb_id
            ).first()
            if not file_metadata:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"File with ID {file_id} not found in knowledge base {kb_id}"
                )
            
            file_name = file_metadata.filename
            file_size = file_metadata.file_size
            file_type = file_metadata.file_type
            file_path = file_metadata.file_path
            file_url = file_metadata.url if file_metadata.url else None
            kb_id = kb.kb_id
            kb_name = kb.name
            
            
            # Select appropriate loader based on file extension
            try:
                # if file_extension in ['.txt', '.py', '.js', '.css', '.java', '.c', '.cpp', '.ts']:
                #     loader = TextLoader(file_path)
                if file_extension in ['.csv']:
                    loader = CSVLoader(file_path)
                # elif file_extension == '.json':
                #     loader = JSONLoader(file_path, jq_schema='.[]')
                elif file_extension in ['.md', '.markdown']:
                    loader = UnstructuredMarkdownLoader(file_path)
                elif file_extension in ['.html', '.htm']:
                    loader = UnstructuredHTMLLoader(file_path)
                elif file_extension in ['.pdf']:
                    loader = PyPDFLoader(file_path)
                elif file_extension in ['.docx', '.doc']:
                    loader = Docx2txtLoader(file_path)
                elif file_extension in ['.txt']:
                    loader = TextLoader(file_path)
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
                        all_content += doc.page_content

                text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=500,
                        chunk_overlap=100,
                        length_function=len,
                        is_separator_regex=False,
                        separators=["\n\n", "\n", " ", ""],)    
                
                texts = text_splitter.create_documents([all_content])
                for doc in texts:

                    meta = doc.metadata
                    meta['file_name'] = file_name
                    meta['file_id'] = file_id
                    meta['file_size'] = file_size
                    meta['file_type'] = file_type
                    meta['file_url'] = file_url
                    meta["kb_id"] = kb_id
                    meta["kb_name"] = kb_name
                    doc.metadata = meta   
                      
                all_chunks.extend([doc for doc in texts])
            
            except Exception as e:
                # Log the error but continue processing other files
                print(f"Error processing {filename}: {str(e)}")
                continue
      
        config ={
            "knowledge_base":kb.name,
            "embedding_model": kb.embedding_model,
            "vector_store": kb.vector_store
        } 
        
        add_to_vectorStore(config=config,chunk_list=all_chunks)
        
        kb.status = schemas.statusEnum.EMBEDDED
        db.commit()
        db.refresh(kb)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing files: {str(e)}"
        )
    
    return {
        "kb_id": kb_id,
        "file_count": len(processed_files),
        "total_content_length": len(all_content),
        "processed_files": processed_files,
        "message": f"Processed {len(processed_files)} files from knowledge base {kb_id}"
    }

@router.delete("/knowledgebases/{kb_id}", response_model=schemas.DeleteResponse)
def delete_knowledge_base(
    kb_id: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(validate_admin)  # Only admins can delete knowledge bases
):
    """
    Delete a knowledge base and all its associated files and metadata.
    """
    # Check if knowledge base exists
    kb = db.query(models.KnowledgeBase).filter(models.KnowledgeBase.kb_id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    
    try:
        # Get all file metadata records for this KB
        file_records = db.query(models.FileMetadata).filter(models.FileMetadata.kb_id == kb_id).all()
        file_count = len(file_records)
        
        # Delete all file metadata records
        db.query(models.FileMetadata).filter(models.FileMetadata.kb_id == kb_id).delete()
        
        # Delete the knowledge base record
        db.delete(kb)
        
        # Commit database changes
        db.commit()
        
        # Delete the directory and all files
        base_path = pathlib.Path(__file__).parent.parent
        kb_dir = base_path / "resources" / kb_id
        
        if os.path.exists(kb_dir):
            shutil.rmtree(kb_dir)
        
        return {
            "kb_id": kb_id,
            "message": f"Knowledge base {kb_id} has been successfully deleted",
            "deleted_files": file_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete knowledge base: {str(e)}"
        )

@router.delete("/knowledgebases/{kb_id}/files/{file_id}", response_model=schemas.DeleteFileResponse)
def delete_file(
    kb_id: str, 
    file_id: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Delete a specific file from a knowledge base.
    """
    # Check if knowledge base exists
    kb = db.query(models.KnowledgeBase).filter(models.KnowledgeBase.kb_id == kb_id).first()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Knowledge base not found"
        )
    
    # Check if file exists and belongs to this knowledge base
    file_metadata = db.query(models.FileMetadata).filter(
        models.FileMetadata.file_id == file_id,
        models.FileMetadata.kb_id == kb_id
    ).first()
    
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"File with ID {file_id} not found in knowledge base {kb_id}"
        )
    
    try:
        # Store values before deletion for response
        filename = file_metadata.filename
        
        # Delete the file from the file system if it exists
        if os.path.exists(file_metadata.file_path):
            os.remove(file_metadata.file_path)
        
        # Delete the file metadata from the database
        db.delete(file_metadata)
        
        # Update the knowledge base last_updated_at timestamp
        kb.last_updated_at = datetime.now()
        
        # If this was the last file, set status back to EMPTY
        remaining_files = db.query(models.FileMetadata).filter(
            models.FileMetadata.kb_id == kb_id
        ).count()
        
        if remaining_files == 0:
            kb.status = schemas.statusEnum.EMPTY
        else:
            kb.status = schemas.statusEnum.UPDATED
        
        # Commit the changes
        db.commit()
        
        return {
            "kb_id": kb_id,
            "file_id": file_id,
            "filename": filename,
            "message": f"File {filename} has been successfully deleted from knowledge base {kb_id}"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )

@router.post("/knowledgebases/{kb_id}/url", response_model=schemas.UrlSubmissionResponse)
def add_url_source(
    kb_id: str,
    url_submission: schemas.UrlSubmission,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Add a website URL as a source to the knowledge base.
    The website will be scraped and its content saved.
    """
    # Check if knowledge base exists
    kb = db.query(models.KnowledgeBase).filter(models.KnowledgeBase.kb_id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    
    try:
        url = str(url_submission.url)
        
        # Parse URL to get domain for filename
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Generate a filename based on the domain
        get_domain = f"{domain}.html"
        
        # Generate unique file ID
        file_id = f"file_{uuid.uuid4()}"
        
        file_name= f"{file_id}_{get_domain}"
        
        # Define path to save file
        base_path = pathlib.Path(__file__).parent.parent  #src directory
        sources_dir = base_path / "resources" / kb_id / "sources"
        
        # Make sure the directory exists
        os.makedirs(sources_dir, exist_ok=True)
        
        file_path = os.path.join(sources_dir, file_name)
        
        # Fetch website content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Get the HTML content
        html_content = response.text
        
        # Use BeautifulSoup to extract and clean text content
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Save original HTML for complete reference
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Create file metadata
        file_metadata = models.FileMetadata(
            file_id=file_id,
            filename=file_path,
            file_size=len(html_content),
            file_type="html",
            kb_id=kb_id,
            file_path=str(file_path),
            url = url
        )
        
        # Add to database
        db.add(file_metadata)
        
        # Update the knowledge base last_updated_at timestamp and status
        kb.last_updated_at = datetime.now()
        kb.status = schemas.statusEnum.UPDATED
        
        # Commit changes
        db.commit()
        db.refresh(file_metadata)
        
        return {
            "kb_id": kb_id,
            "file_id": file_id,
            "url": url,
            "filename": file_name,
            "file_size": len(html_content),
            "message": f"Successfully scraped and added {url} to knowledge base {kb_id}"
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch URL: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process URL: {str(e)}"
        )

