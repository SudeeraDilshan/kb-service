# Knowledge Base Service

A FastAPI service for managing knowledge bases with PostgreSQL database integration.

## Features

- Create knowledge bases with unique IDs
- Automatic folder structure creation for each knowledge base
- PostgreSQL integration for data persistence

## Setup

1. Install dependencies:
```bash
# Using pip
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv

# Or using uv (recommended)
uv pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv
# Alternatively with uv add
uv add fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv
```

2. Set up environment variables in `.env`:
```
DATABASE_URL=postgresql://username:password@localhost/kb_service
```

3. Run the application:
```bash
uvicorn src.main:app --reload
```

## API Endpoints

### Create Knowledge Base

**POST** `/api/knowledgebases`

Request body:
```json
{
  "name": "My Knowledge Base"
}
```

Response:
```json
{
  "kb_id": "kb_1",
  "name": "My Knowledge Base",
  "created_at": "2023-07-21T10:30:45.123Z"
}
```

## Project Structure

```
kb_service/
├── src/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   └── knowledgebase.py
│   └── kb_1/
│       └── sources/
├── .env
└── README.md
```
