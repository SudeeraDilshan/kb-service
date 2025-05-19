import os
from dotenv import load_dotenv
from dialdeskai.src.integrations.embeddings.openai import OpenAIEmbeddings
from dialdeskai.src.integrations.vector_store.pgvector import PGVector
from dialdeskai.src.types import Message, MessageRole
from dialdeskai.src.queue.mosquitto_queue import MosquittoQueue
from dialdeskai.src.queue.trigger import EventTrigger
from dialdeskai.src.integrations.embeddings.gemini import GoogleGeminiEmbeddings

load_dotenv()

q = MosquittoQueue(
    configuration={
        "host": os.getenv('QUEUE_HOST'),
        "port": int(os.getenv('QUEUE_PORT')),
        "topic": os.getenv('QUEUE_TOPIC'),
        "ack_signal_topic": os.getenv('ACK_SIGNAL_TOPIC'),
        "control_signal_topic": os.getenv('CONTROL_SIGNAL_TOPIC'),
    }
)

EventTrigger.set_queue(q)
EventTrigger.set_agent_id("123")

from dialdeskai.src.integrations.vector_store.qdrant import Qdrant

def add_to_vectorStore(config:dict,chunk_list:list[str]):
    
    if config.get("embedding_model") == "openai":
        embedding_model = OpenAIEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL_OPENAI"),
            api_key=os.getenv("EMBEDDING_MODEL_OPENAI_API_KEY")
        )
        
    elif config.get("embedding_model") == "gemini":
        embedding_model = GoogleGeminiEmbeddings(
            model_name=os.getenv("EMBEDDING_MODEL_GEMINI"),
            api_key=os.getenv("EMBEDDING_MODEL_GEMINI_API_KEY")
        )
    
    if config.get("vector_store") == "pgvector":  
        
            table_name = f"{config.get('knowledge_base')}_vector"
            vector_store = PGVector(
                host="157.230.43.112",
                port=5432,
                username="dialdesk_admin",
                password="D_d3sk_adm1n@2025",
                database="dialdesk_db",
                embedding_model=embedding_model,
                table=table_name
            )
            
    elif config.get("vector_store") == "qdrant":
        
            collection_name = f"{config.get('knowledge_base')}_vector"
            vector_store = Qdrant(
                host=os.getenv("QDRANT_HOST"),
                port=os.getenv("QDRANT_PORT"),
                collection_name=collection_name,
                embedding_model=embedding_model
            )           
            
    try:
        vector_store.clear()

        # Insert data
        if config.get("vector_store") == "pgvector":
            for chunk in chunk_list:
               vector_store.insert(Message(content=chunk, role=MessageRole.USER), metadata={})
               
        elif config.get("vector_store") == "qdrant":
            for chunk in chunk_list:
                vector_store.insert(data=chunk)
                  
        print("Data inserted successfully")
            
    except Exception as e:
        print("Error is ",e)
    
        