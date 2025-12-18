"""
Reranker Service
================
Uses CrossEncoder model for reranking retrieved documents.
"""

from typing import Optional, List, Tuple
from sentence_transformers import CrossEncoder
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)


class RerankerService:
    """
    Singleton service for reranking using a CrossEncoder model.
    """
    _instance: Optional['RerankerService'] = None
    _model: Optional[CrossEncoder] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """Load the CrossEncoder reranker model with persistent cache and larger timeouts"""
        if self._model is None:
            try:
                cache_dir = "/app/data/hf_cache"
                os.makedirs(cache_dir, exist_ok=True)
                os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
                os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "60")
                self._model = CrossEncoder(
                    settings.reranker_model,
                    cache_folder=cache_dir
                )
                logger.info(f"✅ Reranker model loaded: {settings.reranker_model} (cache: {cache_dir})")
            except Exception as e:
                logger.error(f"❌ Failed to load reranker model '{settings.reranker_model}': {e}")
                raise

    @property
    def model(self) -> CrossEncoder:
        if self._model is None:
            self.initialize()
        return self._model

    def rerank(
        self,
        query: str,
        contents: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, str, float]]:
        """
        Rerank documents using CrossEncoder model

        Args:
            query: The search query
            contents: List of document contents to rerank
            top_k: Number of top results to return

        Returns:
            List of tuples (original_index, content, score) sorted by score (highest first)
        """
        if not contents:
            return []

        # Prepare query-document pairs
        pairs = [[query, content] for content in contents]

        # Get scores from CrossEncoder
        scores = self.model.predict(pairs)

        # Create list of (index, content, score) tuples
        results = [(i, content, float(score)) for i, (content, score) in enumerate(zip(contents, scores))]

        # Sort by score in descending order
        results.sort(key=lambda x: x[2], reverse=True)

        # Return top_k results
        return results[:top_k]


# Singleton instance
reranker_service = RerankerService()
