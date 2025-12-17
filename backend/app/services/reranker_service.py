"""
Reranker Service
================
Cross-encoder reranking for improved retrieval accuracy
"""

from typing import List, Tuple, Optional
from sentence_transformers import CrossEncoder

from app.config import settings


class RerankerService:
    """
    Service for reranking retrieved documents using cross-encoder
    """
    
    _instance: Optional['RerankerService'] = None
    _model: Optional[CrossEncoder] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self):
        """Load the reranker model"""
        if self._model is None:
            self._model = CrossEncoder(
                settings.reranker_model,
                max_length=512
            )
    
    @property
    def model(self) -> CrossEncoder:
        """Get the loaded model"""
        if self._model is None:
            self.initialize()
        return self._model
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, str, float]]:
        """
        Rerank documents by relevance to query
        
        Args:
            query: The search query
            documents: List of documents to rerank
            top_k: Number of top results to return
            
        Returns:
            List of tuples (original_index, document, score) sorted by score
        """
        if not documents:
            return []
        
        # Create query-document pairs
        pairs = [(query, doc) for doc in documents]
        
        # Get scores from cross-encoder
        scores = self.model.predict(pairs)
        
        # Combine with original indices
        scored_docs = [
            (idx, doc, float(score))
            for idx, (doc, score) in enumerate(zip(documents, scores))
        ]
        
        # Sort by score descending
        scored_docs.sort(key=lambda x: x[2], reverse=True)
        
        # Return top-k
        return scored_docs[:top_k]


# Singleton instance
reranker_service = RerankerService()
