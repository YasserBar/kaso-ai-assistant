# Kaso AI Assistant - Backend

FastAPI backend with RAG (Retrieval Augmented Generation) for intelligent Q&A.

## Features

- 🚀 **FastAPI** - High-performance async API
- ⚡ **uvloop** - Enhanced async performance (Linux/Mac)
- 🔒 **API Key Auth** - Secure endpoints with X-API-Key header
- 📡 **SSE Streaming** - Real-time response streaming
- 🧠 **RAG Pipeline** - Retrieve, Rerank, Generate
- 🌍 **Multilingual** - Arabic and English support
- 💾 **SQLite** - Async conversation storage
- 🔍 **Vector Search** - ChromaDB for semantic search

## Requirements

- Python 3.10+
- Groq API Key ([Get free key](https://console.groq.com/))

## Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate
# Activate (Linux/Mac)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env with your API keys

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Your Groq API key | Required |
| `API_SECRET_KEY` | Secret key for API authentication | Required |
| `CORS_ORIGINS` | Allowed CORS origins | http://localhost:3000 |
| `LLM_MODEL` | Groq model to use | llama-3.1-8b-instant |
| `EMBEDDING_MODEL` | Embedding model | paraphrase-multilingual-MiniLM-L12-v2 |

## API Endpoints

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat/stream` | Streaming chat (SSE) |
| `POST` | `/api/chat` | Non-streaming chat |

### Conversations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/conversations` | List all conversations |
| `POST` | `/api/conversations` | Create new conversation |
| `GET` | `/api/conversations/{id}` | Get conversation with messages |
| `PATCH` | `/api/conversations/{id}` | Update conversation title |
| `DELETE` | `/api/conversations/{id}` | Delete conversation |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/search/conversations` | Keyword search in history |
| `POST` | `/api/search` | Semantic search |
| `GET` | `/api/search/knowledge` | Search knowledge base |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Basic health check |
| `GET` | `/health` | Detailed health status |

> **Note:** All endpoints except `/` and `/health` require `X-API-Key` header.

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Settings
│   ├── api/                 # API endpoints
│   │   ├── chat.py          # Chat endpoints
│   │   ├── conversations.py # CRUD endpoints
│   │   └── search.py        # Search endpoints
│   ├── middleware/
│   │   └── auth.py          # API key middleware
│   ├── models/
│   │   ├── database.py      # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   └── services/
│       ├── embedding_service.py  # Text embeddings
│       ├── chroma_service.py     # Vector DB
│       ├── reranker_service.py   # Reranking
│       ├── llm_service.py        # Groq API
│       └── rag_service.py        # RAG pipeline
├── data_pipeline/           # Data processing
└── data/                    # Data storage
```

## Data Pipeline

See [Data Pipeline Documentation](data_pipeline/README.md) for details on adding new data sources.

```bash
# Run full pipeline
python -m data_pipeline.run_pipeline

# Or run steps individually
python -m data_pipeline.scraper    # Fetch URLs
python -m data_pipeline.cleaner    # Clean content
python -m data_pipeline.chunker    # Split documents
python -m data_pipeline.indexer    # Index to ChromaDB
```

## Docker

This backend supports Docker & Docker Compose for easy deployment.

### Service Overview

- Base image: `python:3.11-alpine` (lightweight)
- Port: `8000` exposed to host (`8000:8000`)
- Volume: `backend_data` persisted to `/app/data` (ChromaDB, conversation storage)
- Environment: loaded from root `.env` (`API_SECRET_KEY`, `GROQ_API_KEY`, `CORS_ORIGINS`)

### Root .env (example)

```
API_SECRET_KEY=change-me-in-production
GROQ_API_KEY=
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

> Ensure `CORS_ORIGINS` includes the frontend domain. For production, set your real domains (e.g., `https://app.example.com`).

### Build & Run

```bash
docker-compose up --build
```

- Backend API: `http://localhost:8000`
- Health checks:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

### Authentication

- All protected endpoints under `/api/*` require `X-API-Key` header with the value of `API_SECRET_KEY`.
- When using the Next.js frontend via Docker Compose, the frontend server-side proxy injects `X-API-Key` automatically.

### Data Persistence

- Application data (including vector index) is stored in `/app/data` inside the container.
- Docker Compose mounts a named volume `backend_data` so data persists across restarts.
- To reset data, stop services and remove the volume or use the data pipeline utilities.
- You can run `python verify_persistence.py` to quickly verify persistence behavior.

### Alpine Notes

- The backend Dockerfile uses Alpine Linux; system dependencies are installed via `apk add`.
- Alpine is smaller than Debian-based images, which reduces image size and start-up time.

### Production Tips

- Use HTTPS and a reverse proxy (e.g., Nginx) in front of the backend.
- Set strong `API_SECRET_KEY` and keep it out of client-side code.
- Configure `CORS_ORIGINS` with your production frontend domain(s).
- Provide a valid `GROQ_API_KEY` if RAG features require external LLM access.
