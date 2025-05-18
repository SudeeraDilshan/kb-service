# Knowledge Base Service

A FastAPI service for managing knowledge bases with PostgreSQL database integration.

## Features

- Create knowledge bases with unique IDs
- Upload files to knowledge bases
- Delete knowledge bases and their associated files
- Automatic folder structure creation for each knowledge base
- PostgreSQL integration for data persistence
- JWT authentication with role-based access control

## Setup

1. Install dependencies:
```bash
# Using pip
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv python-jose passlib bcrypt

# Or using uv (recommended)
uv pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv python-jose passlib bcrypt

# Alternatively with uv add
uv add fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv python-jose passlib bcrypt
```

2. Set up environment variables in `.env`:
```
DATABASE_URL=postgresql://username:password@localhost/kb_service
SECRET_KEY=your_secret_key_for_jwt
```

3. Run the application:
```bash
uvicorn src.main:app --reload
```

## Authentication

The API uses JWT token-based authentication with the OAuth2 password flow.

### Register a New User

**POST** `/api/auth/register`

Request body:
```json
{
  "username": "user1",
  "email": "user1@example.com",
  "full_name": "User One",
  "password": "password123"
}
```

### Login to Get Access Token

**POST** `/api/auth/token`

Form data:
- username: user1
- password: password123

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV...",
  "token_type": "bearer"
}
```

### Authenticated API Calls

Include the access token in the Authorization header:
```
Authorization: Bearer eyJ0eXAiOiJKV...
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

### Delete Knowledge Base (Admin only)

**DELETE** `/api/knowledgebases/{kb_id}`

Response:
```json
{
  "kb_id": "kb_1",
  "message": "Knowledge base kb_1 has been successfully deleted",
  "deleted_files": 3
}
```

### Delete File from Knowledge Base

**DELETE** `/api/knowledgebases/{kb_id}/files/{file_id}`

Response:
```json
{
  "kb_id": "kb_1",
  "file_id": "file_abc123",
  "filename": "document.pdf",
  "message": "File document.pdf has been successfully deleted from knowledge base kb_1"
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
│   ├── security/
│   │   ├── __init__.py
│   │   └── utils.py
│   ├── routers/
│   │   ├── auth.py
│   │   └── knowledgebase.py
│   └── resources/
│       └── kb_1/
│           └── sources/
├── .env
└── README.md
```
