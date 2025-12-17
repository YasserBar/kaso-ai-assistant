"""
Unit Tests for Services
=======================
Tests for embedding, RAG, and LLM services
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEmbeddingService:
    """Tests for EmbeddingService"""
    
    def test_singleton_pattern(self):
        """Test that EmbeddingService is a singleton"""
        from app.services.embedding_service import EmbeddingService
        
        service1 = EmbeddingService()
        service2 = EmbeddingService()
        
        assert service1 is service2
    
    @patch('app.services.embedding_service.SentenceTransformer')
    def test_embed_text_returns_list(self, mock_transformer):
        """Test that embed_text returns a list of floats"""
        from app.services.embedding_service import EmbeddingService
        
        # Setup mock
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
        mock_transformer.return_value = mock_model
        
        service = EmbeddingService()
        service._model = mock_model
        
        result = service.embed_text("test text")
        
        assert isinstance(result, list)
        assert len(result) > 0
    
    @patch('app.services.embedding_service.SentenceTransformer')
    def test_embed_texts_batch(self, mock_transformer):
        """Test batch embedding"""
        from app.services.embedding_service import EmbeddingService
        
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(
            tolist=lambda: [[0.1, 0.2], [0.3, 0.4]]
        )
        mock_transformer.return_value = mock_model
        
        service = EmbeddingService()
        service._model = mock_model
        
        result = service.embed_texts(["text1", "text2"])
        
        assert isinstance(result, list)
        assert len(result) == 2


class TestRAGService:
    """Tests for RAGService"""
    
    def test_detect_language_english(self):
        """Test English language detection"""
        from app.services.rag_service import RAGService
        
        service = RAGService()
        
        result = service.detect_language("What is Kaso?")
        assert result == "en"
    
    def test_detect_language_arabic(self):
        """Test Arabic language detection"""
        from app.services.rag_service import RAGService
        
        service = RAGService()
        
        result = service.detect_language("ما هي شركة كاسو؟")
        assert result == "ar"
    
    def test_build_context_empty(self):
        """Test context building with empty documents"""
        from app.services.rag_service import RAGService
        
        service = RAGService()
        
        result = service.build_context([])
        assert "No relevant information" in result
    
    def test_build_context_with_documents(self):
        """Test context building with documents"""
        from app.services.rag_service import RAGService
        
        service = RAGService()
        
        docs = [
            {"content": "Kaso is a foodtech company", "metadata": {"source": "test.com"}},
            {"content": "Founded in 2020", "metadata": {"source": "test2.com"}}
        ]
        
        result = service.build_context(docs)
        
        assert "Kaso is a foodtech company" in result
        assert "Founded in 2020" in result
        assert "test.com" in result
    
    def test_get_sources(self):
        """Test source extraction"""
        from app.services.rag_service import RAGService
        
        service = RAGService()
        
        docs = [
            {"metadata": {"source": "https://example.com/1"}},
            {"metadata": {"source": "https://example.com/2"}},
            {"metadata": {"source": "https://example.com/1"}}  # Duplicate
        ]
        
        sources = service.get_sources(docs)
        
        assert len(sources) == 2
        assert "https://example.com/1" in sources
        assert "https://example.com/2" in sources


class TestLLMService:
    """Tests for LLMService"""
    
    def test_build_system_prompt_auto(self):
        """Test system prompt with auto language"""
        from app.services.llm_service import LLMService
        
        service = LLMService()
        
        context = "Kaso is a foodtech company."
        prompt = service.build_system_prompt(context, "auto")
        
        assert "Kaso" in prompt
        assert context in prompt
        assert "same language" in prompt.lower()
    
    def test_build_system_prompt_arabic(self):
        """Test system prompt for Arabic"""
        from app.services.llm_service import LLMService
        
        service = LLMService()
        
        context = "Kaso is a company"
        prompt = service.build_system_prompt(context, "ar")
        
        assert "العربية" in prompt
    
    def test_build_system_prompt_english(self):
        """Test system prompt for English"""
        from app.services.llm_service import LLMService
        
        service = LLMService()
        
        context = "Kaso is a company"
        prompt = service.build_system_prompt(context, "en")
        
        assert "English" in prompt


class TestRerankerService:
    """Tests for RerankerService"""
    
    def test_rerank_empty_documents(self):
        """Test reranking with empty documents"""
        from app.services.reranker_service import RerankerService
        
        service = RerankerService()
        
        result = service.rerank("query", [], top_k=5)
        
        assert result == []
    
    @patch('app.services.reranker_service.CrossEncoder')
    def test_rerank_returns_sorted(self, mock_encoder):
        """Test that rerank returns sorted results"""
        from app.services.reranker_service import RerankerService
        
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.3, 0.9, 0.1]
        mock_encoder.return_value = mock_model
        
        service = RerankerService()
        service._model = mock_model
        
        docs = ["doc1", "doc2", "doc3"]
        result = service.rerank("query", docs, top_k=2)
        
        assert len(result) == 2
        # Check sorted by score descending
        assert result[0][2] >= result[1][2]
