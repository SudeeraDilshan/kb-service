from fastapi import FastAPI
from src.routers import knowledgebase, auth  # Use absolute import path
from src.database import engine  # Use absolute import path
import src.models as models  # Use absolute import path

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Knowledge Base Service")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])  # Add auth router
app.include_router(knowledgebase.router, prefix="/api", tags=["Knowledge Base"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Knowledge Base Service"}
