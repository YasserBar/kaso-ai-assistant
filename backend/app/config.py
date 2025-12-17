"""
Kaso AI Assistant - Configuration Settings
==========================================
Uses pydantic-settings for environment variable management
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Security
    api_secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    # Groq Settings
    groq_api_key: str = ""
    llm_model: str = "llama-3.1-8b-instant"
    
    # Embedding & Reranking Models
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    # reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # English only - OLD
    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"  # Multilingual (100+ languages)
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/chat_history.db"
    
    # ChromaDB
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "kaso_knowledge"
    
    # RAG Settings
    rag_top_k: int = 10
    rag_rerank_top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience export
settings = get_settings()
