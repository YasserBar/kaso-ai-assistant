"""
Unit Tests for Database Models
==============================
Tests for Pydantic schemas and database models
"""

import pytest
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPydanticSchemas:
    """Tests for Pydantic request/response schemas"""
    
    def test_chat_request_valid(self):
        """Test valid chat request"""
        from app.models.schemas import ChatRequest
        
        request = ChatRequest(
            message="Hello, what is Kaso?",
            conversation_id=None,
            stream=True
        )
        
        assert request.message == "Hello, what is Kaso?"
        assert request.stream is True
    
    def test_chat_request_validation_min_length(self):
        """Test chat request message min length validation"""
        from app.models.schemas import ChatRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ChatRequest(message="", stream=True)
    
    def test_chat_request_validation_max_length(self):
        """Test chat request message max length validation"""
        from app.models.schemas import ChatRequest
        from pydantic import ValidationError
        
        long_message = "x" * 4001  # Max is 4000
        
        with pytest.raises(ValidationError):
            ChatRequest(message=long_message, stream=True)
    
    def test_chat_message_valid_roles(self):
        """Test chat message role validation"""
        from app.models.schemas import ChatMessage
        
        user_msg = ChatMessage(role="user", content="Hello")
        assert user_msg.role == "user"
        
        assistant_msg = ChatMessage(role="assistant", content="Hi")
        assert assistant_msg.role == "assistant"
        
        system_msg = ChatMessage(role="system", content="You are helpful")
        assert system_msg.role == "system"
    
    def test_chat_message_invalid_role(self):
        """Test chat message rejects invalid role"""
        from app.models.schemas import ChatMessage
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ChatMessage(role="invalid", content="Hello")
    
    def test_search_request_valid(self):
        """Test valid search request"""
        from app.models.schemas import SearchRequest
        
        request = SearchRequest(
            query="Kaso funding",
            search_type="hybrid",
            limit=10
        )
        
        assert request.query == "Kaso funding"
        assert request.search_type == "hybrid"
        assert request.limit == 10
    
    def test_search_request_invalid_type(self):
        """Test search request with invalid search type"""
        from app.models.schemas import SearchRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            SearchRequest(
                query="test",
                search_type="invalid"
            )
    
    def test_conversation_summary(self):
        """Test conversation summary schema"""
        from app.models.schemas import ConversationSummary
        
        summary = ConversationSummary(
            id="123",
            title="Test Chat",
            preview="Hello...",
            message_count=5,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert summary.id == "123"
        assert summary.message_count == 5


class TestDatabaseModels:
    """Tests for SQLAlchemy database models"""
    
    def test_conversation_model(self):
        """Test Conversation model creation"""
        from app.models.database import Conversation
        
        conv = Conversation(title="Test Conv")
        
        assert conv.title == "Test Conv"
        # ID is generated on flush/commit by default, so it's None initially without a session
        # assert conv.id is not None
    
    def test_message_model(self):
        """Test Message model creation"""
        from app.models.database import Message
        
        msg = Message(
            conversation_id="conv-123",
            role="user",
            content="Hello"
        )
        
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.conversation_id == "conv-123"
    
    def test_conversation_repr(self):
        """Test Conversation string representation"""
        from app.models.database import Conversation
        
        conv = Conversation(title="Test")
        repr_str = repr(conv)
        
        assert "Conversation" in repr_str
        assert "Test" in repr_str
    
    def test_message_repr(self):
        """Test Message string representation"""
        from app.models.database import Message
        
        msg = Message(conversation_id="123", role="user", content="Hi")
        repr_str = repr(msg)
        
        assert "Message" in repr_str
        assert "user" in repr_str
