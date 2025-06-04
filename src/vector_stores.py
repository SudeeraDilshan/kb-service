import os
from dotenv import load_dotenv
from langchain_core.documents import Document
import time
from dialdeskai_vs.vector_stores.pgvector import PGVector
from dialdeskai_vs.vector_stores.qdrant import Qdrant
from dialdeskai_vs.vector_stores.base import VectorStore
from dialdeskai_vs.embeddings.openai import OpenAIEmbeddings
from dialdeskai_vs.embeddings.google import GoogleGeminiEmbeddings
from dialdeskai_vs.shared.types import EmbeddingModelType, VectorStoreType

load_dotenv()

def get_embedding_model(config: dict):
    if config.get("embedding_model") == EmbeddingModelType.OPENAI:
        embedding_model = OpenAIEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL_OPENAI"),
            api_key=os.getenv("EMBEDDING_MODEL_OPENAI_API_KEY"),
        )

    elif config.get("embedding_model") == EmbeddingModelType.GEMINI:
        embedding_model = GoogleGeminiEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL_GEMINI"),
            api_key=os.getenv("EMBEDDING_MODEL_GEMINI_API_KEY"),
        )
        
    else:
        raise ValueError("Unsupported embedding model type")

    return embedding_model

def get_vector_store(config: dict) -> VectorStore:
    embedding_model = get_embedding_model(config)

    if config.get("vector_store") == VectorStoreType.PGVECTOR:
        table_name = f"{config.get('knowledge_base')}_vector"
        vector_store = PGVector(
            host="157.230.43.112",
            port=5432,
            username="dialdesk_admin",
            password="D_d3sk_adm1n@2025",
            database="dialdesk_db",
            embedding_model=embedding_model,
            table=table_name,
        )

    elif config.get("vector_store") == VectorStoreType.QDRANT:
        collection_name = f"{config.get('knowledge_base')}_vector"
        vector_store = Qdrant(
            host=os.getenv("QDRANT_HOST"),
            port=os.getenv("QDRANT_PORT"),
            collection_name=collection_name,
            embedding_model=embedding_model,
        )
    
    else:
        raise ValueError("Unsupported vector store type")
    return vector_store    

def add_to_vectorStore(config: dict, chunk_list: list[Document]):
    try:
        workspace_id = config.get("workspace_id", os.getenv("WORKSPACE_ID"))
        vector_store = get_vector_store(config)
        vector_store.clear(workspace_id=workspace_id)
        for chunk in chunk_list:
            vector_store.insert(
                data=chunk.page_content, 
                metadata=chunk.metadata, 
                workspace_id=workspace_id
            )
            
        print("Data inserted successfully")

    except Exception as e:
        print("Error is ", e)
