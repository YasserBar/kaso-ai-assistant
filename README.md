# Kaso AI Assistant 🤖

AI-powered assistant for Kaso. Ask questions about Kaso and get intelligent answers based on collected knowledge.

> **Prototype Designed by:** Yasser Barghouth
> **Developed with:** Claude Code using Opus 4.5 & Antigravity using Gemini 3 Pro

## Features

- 🧠 **RAG-based AI**: Retrieval Augmented Generation for accurate answers
- 🌍 **Multilingual**: Supports 100+ languages (Arabic, English, French, Spanish, German, etc.)
  - Multilingual embedding model: `paraphrase-multilingual-MiniLM-L12-v2`
  - Multilingual reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
- 🌐 **UI Localization**: Full interface support for 3 languages (English, Arabic, German) with RTL support
- ⚡ **Fast Streaming**: Real-time response streaming with Groq LPU
- 💬 **Chat History**: Persistent conversation history with search
- 🔒 **Secure**: API key authentication
- 📱 **Responsive**: Works on desktop and mobile
- 🔍 **Advanced Retrieval**: Vector search + reranking for better accuracy

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

### Prerequisites

- Python 3.10+
- Node.js 18+
- Groq API Key ([Get free key](https://console.groq.com/))

### 1. Clone and Setup Backend

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
# NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_API_KEY=your_secret_key

# Start development server
npm run dev
```

### 5. Open in Browser

Visit [http://localhost:3000](http://localhost:3000)

## Project Structure

```
kaso_ai_assistant/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   ├── middleware/        # Auth middleware
│   │   ├── models/            # Database & Pydantic models
│   │   └── services/          # Business logic
│   ├── data_pipeline/         # Data processing
│   │   ├── scraper.py         # URL scraper
│   │   ├── cleaner.py         # Text cleaner
│   │   ├── chunker.py         # Text splitter
│   │   └── indexer.py         # ChromaDB indexer
│   └── data/
│       └── kaso_data_sources.csv  # URL sources
│       └── chroma_db/         # Vector database
│
├── frontend/                   # Next.js Frontend
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

### Method 1: Add URLs to scrape

1. Add URL to `backend/data/kaso_data_sources.csv`:
```csv
المصادر,الروابط
29,https://new-source.com/article
```

2. Run the scraper and pipeline:
```bash
cd backend
# Scrape new URLs only
python -m data_pipeline.scraper

# Process and index (skip scraping)
python -m data_pipeline.run_pipeline --no-scrape
```

### Method 2: Add markdown files directly

1. Place your markdown file in the project root or `backend/data/`

2. Run the chunker and indexer:
```bash
cd backend
python -m data_pipeline.chunker --markdown path/to/your/file.md
python -m data_pipeline.indexer
```

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
