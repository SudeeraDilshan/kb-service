from fastapi import FastAPI
from src.routers import knowledgebase, auth  # Added auth import
from src.database import engine
from src import models

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Knowledge Base Service")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])  # Add auth router
app.include_router(knowledgebase.router, prefix="/api", tags=["Knowledge Base"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Knowledge Base Service"}
