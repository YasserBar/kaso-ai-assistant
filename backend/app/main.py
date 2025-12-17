"""
Kaso AI Assistant - FastAPI Application
=======================================
Main entry point configuring:
- uvloop for high-performance async (non-Windows)
- Application lifespan to initialize DB, EmbeddingService, and ChromaService
- CORS, API key middleware, and API routers (/api Chat, Conversations, Search)
- Health check endpoints (/, /health)
"""

import sys
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import chat, conversations, search
from app.middleware.auth import APIKeyMiddleware
from app.services.embedding_service import embedding_service
from app.services.chroma_service import chroma_service
from app.models.database import init_db
import logging

# Configure module logger early to avoid NameError and ensure startup logs are emitted
logger = logging.getLogger(__name__)

# Use uvloop for better async performance (Linux/macOS)
# On Windows, uvloop is not supported, so we fall back to default
if sys.platform != "win32":
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("✅ Using uvloop for enhanced async performance")
    except ImportError:
        logger.warning("⚠️ uvloop not available, using default event loop")
else:
    logger.info("ℹ️ Running on Windows - using default event loop (uvloop not supported)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Responsibilities:
    - On startup: initialize the database, load the embedding model, and initialize the ChromaDB vector store.
    - On shutdown: perform cleanup (currently logs a shutdown message).

    Notes:
    - Embedding and Chroma services are singletons; initialize() prepares models and persistent storage.
    - Database initialization ensures tables exist and sets up the async engine/session factory.
    - Startup logs provide visibility during development; consider structured logging in production.
    """
    logger.info("🚀 Starting Kaso AI Assistant...")
    
    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")
    
    # Load embedding model (this may take a moment first time)
    logger.info("📥 Loading embedding model...")
    embedding_service.initialize()
    logger.info(f"✅ Embedding model loaded: {settings.embedding_model}")
    
    # Initialize ChromaDB
    logger.info("📥 Initializing ChromaDB...")
    chroma_service.initialize()
    logger.info(f"✅ ChromaDB initialized: {settings.chroma_persist_dir}")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("👋 Shutting down Kaso AI Assistant...")


# Create FastAPI application
# The lifespan handler initializes critical resources (DB, embedding model, ChromaDB)
# during startup and gracefully closes them on shutdown.
app = FastAPI(
    title="Kaso AI Assistant API",
    description="AI-powered assistant for Kaso information",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
# allow_origins is read from settings.cors_origins_list to restrict which frontends
# can call the backend. The other flags enable credentials and any HTTP method/headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add API Key authentication middleware
# Protects all /api/* routes by enforcing X-API-Key header.
app.add_middleware(APIKeyMiddleware)

# Include routers
# Grouped under /api with tags for documentation clarity.
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(conversations.router, prefix="/api", tags=["Conversations"])
app.include_router(search.router, prefix="/api", tags=["Search"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Kaso AI Assistant",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "embedding_model": settings.embedding_model,
        "llm_model": settings.llm_model,
        "chroma_collection": settings.chroma_collection_name
    }


if __name__ == "__main__":
    # When running directly via `python app/main.py`, configure basic logging
    logging.basicConfig(level=logging.INFO)
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
