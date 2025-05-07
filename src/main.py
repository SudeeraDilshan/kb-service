from fastapi import FastAPI
from src.routers import knowledgebase  # Changed from .routers
from src.database import engine        # Changed from .database
from src import models                 # Changed from . import models

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Knowledge Base Service")

# Include routers
app.include_router(knowledgebase.router, prefix="/api", tags=["Knowledge Base"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Knowledge Base Service"}
