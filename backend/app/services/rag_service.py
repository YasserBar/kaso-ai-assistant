"""
RAG Service
===========
Retrieval Augmented Generation pipeline
Combines retrieval, reranking, and generation
"""

from typing import List, Dict, Any, Tuple
from langdetect import detect, LangDetectException

from app.config import settings
from app.services.chroma_service import chroma_service
from app.services.reranker_service import reranker_service


class RAGService:
    """
    Service for RAG (Retrieval Augmented Generation) pipeline
    """
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of input text
        
        Args:
            text: Input text
            
        Returns:
            Language code ('ar' for Arabic, 'en' for English, etc.)
        """
        try:
            lang = detect(text)
            return lang
        except LangDetectException:
            return "en"  # Default to English
    
    def retrieve(
        self,
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from vector store
        
        Args:
            query: Search query
            top_k: Number of results (default from settings)
            
        Returns:
            List of retrieved documents with metadata
        """
        if top_k is None:
            top_k = settings.rag_top_k
        
        results = chroma_service.query(query, n_results=top_k)
        
        retrieved = []
        for i in range(len(results["documents"])):
            retrieved.append({
                "id": results["ids"][i],
                "content": results["documents"][i],
                "metadata": results["metadatas"][i],
                "distance": results["distances"][i]
            })
        
        return retrieved
    
    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank retrieved documents using cross-encoder
        
        Args:
            query: Original query
            documents: Retrieved documents
            top_k: Number of top results after reranking
            
        Returns:
            Reranked documents
        """
        if top_k is None:
            top_k = settings.rag_rerank_top_k
        
        if not documents:
            return []
        
        # Extract content for reranking
        contents = [doc["content"] for doc in documents]
        
        # Rerank
        reranked = reranker_service.rerank(query, contents, top_k=top_k)
        
        # Rebuild documents with new order and scores
        result = []
        for orig_idx, content, score in reranked:
            doc = documents[orig_idx].copy()
            doc["rerank_score"] = score
            result.append(doc)
        
        return result
    
    def build_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        Build context string from retrieved documents
        
        Args:
            documents: List of retrieved/reranked documents
            
        Returns:
            Formatted context string for LLM
        """
        if not documents:
            return "No relevant information found in the knowledge base."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc["metadata"].get("source", "Unknown")
            content = doc["content"]
            context_parts.append(f"[Source {i}: {source}]\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_sources(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Extract unique sources from documents
        
        Args:
            documents: List of documents
            
        Returns:
            List of unique source URLs/names
        """
        sources = set()
        for doc in documents:
            source = doc["metadata"].get("source", "")
            if source:
                sources.add(source)
        return list(sources)
    
    def process_query(self, query: str) -> Tuple[str, str, List[str]]:
        """
        Orchestrate the full Retrieval-Augmented Generation (RAG) pipeline.

        Steps:
        - Detect the query language (Arabic/English/etc.).
        - Retrieve the most similar document chunks from the vector store.
        - Rerank retrieved chunks with a cross-encoder for better relevance.
        - Build a consolidated context string for the LLM to ground its answer.
        - Extract a unique list of sources for transparency/citations.

        Args:
            query: The user's question or prompt.

        Returns:
            A tuple of:
            - context: Formatted text that the LLM must base its answer on.
            - detected_language: ISO-like language code (e.g., 'ar', 'en').
            - sources: Unique list of content sources used in the context.
        """
        # Detect language: helps the LLM respond in the user's language when set to 'auto'
        language = self.detect_language(query)
        
        # Retrieve: initial semantic search from the vector store
        retrieved = self.retrieve(query)
        
        # Rerank: re-order retrieved chunks by relevance using a cross-encoder
        reranked = self.rerank(query, retrieved)
        
        # Build context: join selected chunks into a single, LLM-friendly context string
        context = self.build_context(reranked)
        
        # Get sources: collect unique metadata sources for UI display and auditing
        sources = self.get_sources(reranked)
        
        return context, language, sources


# Singleton instance
rag_service = RAGService()
