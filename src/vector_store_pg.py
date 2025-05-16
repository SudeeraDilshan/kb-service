import os
from dotenv import load_dotenv
from dialdeskai.src.integrations.embeddings.openai import OpenAIEmbeddings
from dialdeskai.src.integrations.vector_store.pgvector import PGVector
from dialdeskai.src.types import Message, MessageRole
from dialdeskai.src.queue.mosquitto_queue import MosquittoQueue
from dialdeskai.src.queue.trigger import EventTrigger

load_dotenv()

embedding_model = OpenAIEmbeddings(
    model_name=os.getenv("EMBEDDING_MODEL"),
    api_key=os.getenv("EMBEDDING_MODEL_API_KEY")
)

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

def add_to_db(knowledge_base:str,chunk_list:list[str]):

    # Initialize PGVector
    vector_store = PGVector(
        host="157.230.43.112",
        port=5432,
        username="dialdesk_admin",
        password="D_d3sk_adm1n@2025",
        database="dialdesk_db",
        embedding_model=embedding_model,
        table=f"{knowledge_base}_vector"
    )
    
    try:
        vector_store.clear()

        # Insert data
        for chunk in chunk_list:
               vector_store.insert(Message(content=chunk, role=MessageRole.USER), metadata={})
        print("Data inserted successfully")
            
    except Exception as e:
        print("Error is ",e)
    
        