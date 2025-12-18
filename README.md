# Kaso AI Assistant 🤖

AI-powered assistant for Kaso. Ask questions about Kaso and get intelligent answers based on collected knowledge.

> **Prototype Designed by:** Yasser Barghouth
> **Developed with:** Claude Code using Opus 4.5 & Antigravity using Gemini 3 Pro

## Features

### Core AI
- 🧠 **RAG-based AI**: Retrieval Augmented Generation for accurate answers
- 🌍 **Multilingual**: Supports 100+ languages (Arabic, English, French, Spanish, German, etc.)
  - Multilingual embedding model: `paraphrase-multilingual-MiniLM-L12-v2`
  - Multilingual reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
- 🔍 **Advanced Retrieval**: Vector search + reranking for better accuracy
- ⚡ **Fast Streaming**: Real-time response streaming with Groq LPU

### Smart Services
- 🎯 **Intent Classification**: Multi-layer filtering to detect off-topic queries
- ✅ **Response Validation**: Hallucination detection and quality checks
- 🔢 **Token Management**: Intelligent context window optimization
- 🏢 **Company Disambiguation**: Distinguishes Kaso B2B from other companies named Kaso
- 💬 **Conversation Context**: Query reformulation for better follow-up handling

### User Experience
- 🌐 **UI Localization**: Full interface support for 3 languages (English, Arabic, German) with RTL support
- 📜 **Chat History**: Persistent conversation history with search
- 🔒 **Secure**: API key authentication
- 📱 **Responsive**: Works on desktop and mobile

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│                   (Next.js + assistant-ui)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ SSE Streaming
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                          Backend                            │
│                    (FastAPI + uvloop)                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │   RAG   │  │  LLM    │  │ History │  │   Reranker      │ │
│  │ Service │  │ Service │  │ Service │  │   Service       │ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬────────┘ │
│       │            │            │                 │         │
│       ▼            ▼            ▼                 ▼         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ChromaDB │  │  Groq   │  │ SQLite  │  │ Cross-Encoder   │ │
│  │(Vectors)│  │   API   │  │   DB    │  │     Model       │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### One-Click Start (Windows)

After initial setup, use the one-click runner:

```bash
# Starts both backend and frontend, opens browser
run_all.bat
```

### Prerequisites

- Python 3.10+
- Node.js 18+
- Groq API Key ([Get free key](https://console.groq.com/))

### Setup Scripts

**Full project setup (Linux/Mac):**
```bash
chmod +x setup.sh
./setup.sh
```

**Frontend setup only:**
```bash
cd frontend
# Windows
setup.bat
# Linux/Mac
chmod +x setup.sh && ./setup.sh
```

### Manual Setup

#### 1. Clone and Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment file
copy .env.example .env
# Edit .env with your API keys
```

### 2. Run Data Pipeline

**Important**: You must run the data pipeline to build the knowledge base before starting the backend.

```bash
cd backend

# Option 1: Run complete pipeline (Recommended for first time)
# This will: scrape URLs → clean → chunk → index into ChromaDB
python -m data_pipeline.run_pipeline --markdown ../kaso_research_report.md

# Option 2: Run steps individually
# Step 1: Scrape URLs from kaso_data_sources.csv
python -m data_pipeline.scraper

# Step 2: Clean scraped content
python -m data_pipeline.cleaner

# Step 3: Chunk documents
python -m data_pipeline.chunker
python -m data_pipeline.chunker --markdown ../kaso_research_report.md

# Step 4: Index into ChromaDB
python -m data_pipeline.indexer
```

**Note**: The pipeline will:
- Scrape 25+ URLs from `kaso_data_sources.csv` (some may fail due to anti-bot protection)
- Process the main research report `kaso_research_report.md`
- Create embeddings and index ~165 chunks into ChromaDB

### 3. Start Backend Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Setup and Start Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy and edit environment file
# Create .env.local with:
# NEXT_PUBLIC_API_URL=/api
# API_SECRET_KEY=change-me-in-production
# BACKEND_URL=http://localhost:8000/api
# CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
# Start development server
npm run dev
```

### 5. Open in Browser

Visit [http://localhost:3000](http://localhost:3000)

## Deployment – Approach 2: Docker Compose

Use Docker Compose to run the frontend (Next.js) and backend (FastAPI) together.

### Prerequisites
- Docker and Docker Compose installed
- Root `.env` file at the project root

### Service Overview
- Frontend `frontend`: exposed on port 3000
- Backend `backend`: exposed on port 8000
- Next.js server-side proxy forwards all requests from `/api/*` to the internal service `http://backend:8000/api/*`
- Backend data persisted to a named volume `backend_data` mounted at `/app/data` inside the container

### Root .env (example)
```
API_SECRET_KEY=change-me-in-production
GROQ_API_KEY=
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```
- Ensure `CORS_ORIGINS` includes the frontend domain(s)
- `API_SECRET_KEY` is used for authentication via the `X-API-Key` header and is injected server-side by the Next.js proxy; no API keys are sent from the browser

### Build & Run
```bash
docker-compose up --build
```
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

### Behind the Scenes
- The Next.js route handler at `/api/*` proxies requests to `http://backend:8000/api/*` within the Docker network
- The proxy injects the `X-API-Key` from `API_SECRET_KEY` and transparently supports Server-Sent Events (SSE)

### Data Persistence
- Application data (including the vector index) is stored in `/app/data` inside the backend container
- The named volume `backend_data` keeps data across restarts
- To reset data, stop services and remove the volume or use the data pipeline utilities
- You can run `python backend/verify_persistence.py` to quickly verify persistence behavior

### Useful Commands
- Tail logs:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```
- Stop services:
```bash
docker-compose down
```
- Remove services with volumes (warning: will delete persisted data):
```bash
docker-compose down -v
```

### Production Tips
- Use HTTPS and a reverse proxy (e.g., Nginx) in front of the services
- Set a strong `API_SECRET_KEY` and keep it out of client-side code
- Configure `CORS_ORIGINS` with your production frontend domain(s)
- Provide a valid `GROQ_API_KEY` if external LLM features are required

## Project Structure

```
kaso_ai_assistant/
├── run_all.bat                 # One-click runner (Windows)
├── setup.sh                    # Full project setup (Linux/Mac)
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   ├── middleware/        # Auth middleware
│   │   ├── models/            # Database & Pydantic models
│   │   └── services/          # Business logic
│   │       ├── rag_service.py           # RAG pipeline
│   │       ├── llm_service.py           # Groq API
│   │       ├── embedding_service.py     # Text embeddings
│   │       ├── reranker_service.py      # Reranking
│   │       ├── chroma_service.py        # Vector DB
│   │       ├── intent_classifier.py     # Intent classification
│   │       ├── response_validator.py    # Response validation
│   │       ├── token_manager.py         # Token budget management
│   │       ├── conversation_manager.py  # Context management
│   │       ├── company_disambiguator.py # Company disambiguation
│   │       └── multilingual_service.py  # Multilingual support
│   ├── data_pipeline/         # Data processing
│   │   ├── scraper.py         # URL scraper
│   │   ├── cleaner.py         # Text cleaner
│   │   ├── chunker.py         # Text splitter
│   │   └── indexer.py         # ChromaDB indexer
│   └── data/
│       ├── kaso_data_sources.csv  # URL sources
│       └── chroma_db/         # Vector database
│
├── frontend/                   # Next.js Frontend
│   ├── setup.bat              # Frontend setup (Windows)
│   ├── setup.sh               # Frontend setup (Linux/Mac)
│   └── src/
│       ├── app/               # Next.js app router
│       ├── components/        # React components
│       └── lib/               # Utilities & API client
│
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/stream` | Streaming chat (SSE) |
| POST | `/api/chat` | Non-streaming chat |
| GET | `/api/conversations` | List conversations |
| GET | `/api/conversations/{id}` | Get conversation |
| DELETE | `/api/conversations/{id}` | Delete conversation |
| GET | `/api/search/conversations` | Search history |
| GET | `/api/search/knowledge` | Search knowledge base |

All endpoints require `X-API-Key` header.

## Adding New Data Sources

The knowledge base can be expanded with URLs or Markdown files (research reports, summaries, documentation).

### Method 1: Add Markdown Files (Recommended for Custom Content)

Best for: Research reports, summaries, documentation, custom knowledge

```bash
cd backend

# Add a single markdown file
python -m data_pipeline.run_pipeline --markdown ../kaso_research_report.md

# Or add multiple files manually
python -m data_pipeline.chunker --markdown ../summary1.md
python -m data_pipeline.chunker --markdown ../summary2.md
python -m data_pipeline.indexer
```

**Example markdown structure:**
```markdown
# Topic Title

## Section 1
Content about Kaso...

## Section 2
More details...
```

**Tips for markdown files:**
- Use clear headings (`#`, `##`) for better chunking
- Include keywords in Arabic and English for better search
- Keep paragraphs focused on single topics

### Method 2: Add URLs to scrape

Best for: External web pages, articles, blog posts

1. Add URL to `backend/data/kaso_data_sources.csv`:
```csv
المصادر,الروابط
29,https://new-source.com/article
```

2. Run the pipeline:
```bash
cd backend
python -m data_pipeline.run_pipeline
```

See [Data Pipeline Documentation](backend/data_pipeline/README.md) for more details.

## Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | Groq (llama-3.1-8b-instant) |
| Embeddings | paraphrase-multilingual-MiniLM-L12-v2 |
| Vector DB | ChromaDB |
| Reranker | cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 (Multilingual) |
| Backend | FastAPI + uvloop |
| Frontend | Next.js + Tailwind CSS |
| Database | SQLite (async) |

## License

MIT
