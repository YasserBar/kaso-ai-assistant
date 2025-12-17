"""
Embedding Service
=================
Generates embeddings using sentence-transformers
Supports multilingual text (Arabic + English)
"""

from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


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
        """Load the embedding model"""
        if self._model is None:
            self._model = SentenceTransformer(settings.embedding_model)
            # Warm up the model
            _ = self._model.encode(["warmup"], show_progress_bar=False)
    
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
