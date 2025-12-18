"""
Embedding Service
=================
Generates embeddings using sentence-transformers
Supports multilingual text (Arabic + English)
"""

from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Singleton service for generating text embeddings.

    Responsibilities:
    - Lazily load SentenceTransformer model from settings.embedding_model.
    - Provide single-text and batch embedding helpers.
    - Normalize embeddings to improve cosine similarity comparability.
    - Expose embedding dimensionality for vector DB configuration.
    Uses multilingual model for Arabic/English support.
    """
    
    _instance: Optional['EmbeddingService'] = None
    _model: Optional[SentenceTransformer] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self):
        """Load the embedding model with robust offline-aware config"""
        if self._model is None:
            try:
                # Determine cache directory based on environment
                # Docker: /app/data/hf_cache, Local: ./data/hf_cache (relative to backend)
                if os.environ.get("HF_HOME"):
                    cache_dir = os.environ["HF_HOME"]
                elif os.path.exists("/app/data"):
                    # Running in Docker
                    cache_dir = "/app/data/hf_cache"
                else:
                    # Running locally - use relative path from backend directory
                    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "hf_cache")

                os.makedirs(cache_dir, exist_ok=True)

                # Increase HF Hub timeouts significantly (5 minutes) to avoid ReadTimeoutError
                os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = os.environ.get("HF_HUB_DOWNLOAD_TIMEOUT", "300")
                os.environ["HF_HUB_ETAG_TIMEOUT"] = os.environ.get("HF_HUB_ETAG_TIMEOUT", "300")

                logger.info(f"⏳ Loading embedding model: {settings.embedding_model} (cache: {cache_dir})")

                # Check if model exists locally first
                model_path = os.path.join(cache_dir, f"sentence-transformers_{settings.embedding_model.replace('/', '_')}")
                local_files_only = os.path.exists(model_path)

                if local_files_only:
                    logger.info(f"📦 Found cached model, loading offline: {model_path}")

                # Try loading with local_files_only first if cached, then fallback to online
                try:
                    self._model = SentenceTransformer(
                        settings.embedding_model,
                        cache_folder=cache_dir,
                        local_files_only=local_files_only
                    )
                except Exception as offline_error:
                    if local_files_only:
                        logger.warning(f"⚠️ Offline load failed, trying online: {offline_error}")
                        self._model = SentenceTransformer(
                            settings.embedding_model,
                            cache_folder=cache_dir,
                            local_files_only=False
                        )
                    else:
                        raise

                logger.info(f"✅ Embedding model loaded: {settings.embedding_model}")
            except Exception as e:
                logger.error(f"❌ Failed to load embedding model '{settings.embedding_model}': {e}")
                raise
    
    @property
    def model(self) -> SentenceTransformer:
        """Get the loaded model"""
        if self._model is None:
            self.initialize()
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        embedding = self.model.encode(
            text,
            show_progress_bar=False,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of input texts
            batch_size: Batch size for encoding
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True
        )
        return embeddings.tolist()
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embedding vectors"""
        return self.model.get_sentence_embedding_dimension()


# Singleton instance
embedding_service = EmbeddingService()
