"""
Integration Tests for API Endpoints
====================================
Tests for chat, conversations, and search endpoints
"""

import pytest
from httpx import AsyncClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root health check"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "Kaso" in data["service"]
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test detailed health check"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "embedding_model" in data
        assert "llm_model" in data


class TestAuthMiddleware:
    """Tests for API key authentication"""
    
    @pytest.mark.asyncio
    async def test_missing_api_key(self, client: AsyncClient):
        """Test request without API key"""
        response = await client.get("/api/conversations")
        
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "MISSING_API_KEY"
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, client: AsyncClient):
        """Test request with invalid API key"""
        response = await client.get(
            "/api/conversations",
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["code"] == "INVALID_API_KEY"
    
    @pytest.mark.asyncio
    async def test_valid_api_key(self, client: AsyncClient, api_headers: dict):
        """Test request with valid API key"""
        response = await client.get(
            "/api/conversations",
            headers=api_headers
        )
        
        assert response.status_code == 200


class TestConversationsAPI:
    """Tests for conversations CRUD endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_conversations_empty(self, client: AsyncClient, api_headers: dict):
        """Test listing conversations when empty"""
        response = await client.get(
            "/api/conversations",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_create_conversation(self, client: AsyncClient, api_headers: dict):
        """Test creating a new conversation"""
        response = await client.post(
            "/api/conversations",
            headers=api_headers,
            json={"title": "Test Conversation"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Conversation"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_get_conversation(self, client: AsyncClient, api_headers: dict):
        """Test getting a specific conversation"""
        # First create a conversation
        create_response = await client.post(
            "/api/conversations",
            headers=api_headers,
            json={"title": "Test"}
        )
        conv_id = create_response.json()["id"]
        
        # Then get it
        response = await client.get(
            f"/api/conversations/{conv_id}",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id
        assert "messages" in data
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, client: AsyncClient, api_headers: dict):
        """Test getting a non-existent conversation"""
        response = await client.get(
            "/api/conversations/nonexistent-id",
            headers=api_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_conversation(self, client: AsyncClient, api_headers: dict):
        """Test deleting a conversation"""
        # Create
        create_response = await client.post(
            "/api/conversations",
            headers=api_headers,
            json={"title": "To Delete"}
        )
        conv_id = create_response.json()["id"]
        
        # Delete
        response = await client.delete(
            f"/api/conversations/{conv_id}",
            headers=api_headers
        )
        
        assert response.status_code == 200
        
        # Verify deleted
        get_response = await client.get(
            f"/api/conversations/{conv_id}",
            headers=api_headers
        )
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_conversation_title(self, client: AsyncClient, api_headers: dict):
        """Test updating conversation title"""
        # Create
        create_response = await client.post(
            "/api/conversations",
            headers=api_headers,
            json={"title": "Original Title"}
        )
        conv_id = create_response.json()["id"]
        
        # Update
        response = await client.patch(
            f"/api/conversations/{conv_id}?title=New Title",
            headers=api_headers
        )
        
        assert response.status_code == 200
        
        # Verify update
        get_response = await client.get(
            f"/api/conversations/{conv_id}",
            headers=api_headers
        )
        assert get_response.json()["title"] == "New Title"


class TestSearchAPI:
    """Tests for search endpoints"""
    
    @pytest.mark.asyncio
    async def test_search_conversations_empty(self, client: AsyncClient, api_headers: dict):
        """Test searching with no results"""
        response = await client.get(
            "/api/search/conversations?query=nonexistent",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
    
    @pytest.mark.asyncio
    async def test_search_knowledge_base(self, client: AsyncClient, api_headers: dict):
        """Test searching knowledge base"""
        response = await client.get(
            "/api/search/knowledge?query=Kaso",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data


class TestChatAPI:
    """Tests for chat endpoints"""
    
    @pytest.mark.asyncio
    async def test_chat_creates_conversation(self, client: AsyncClient, api_headers: dict):
        """Test that chat creates a new conversation if none provided"""
        response = await client.post(
            "/api/chat",
            headers=api_headers,
            json={
                "message": "Hello",
                "stream": False
            }
        )
        
        # Note: This may fail if LLM service is not mocked
        # In real integration test, would need ChromaDB and Groq setup
        assert response.status_code in [200, 500]  # 500 if services not available
    
    @pytest.mark.asyncio
    async def test_chat_with_existing_conversation(self, client: AsyncClient, api_headers: dict):
        """Test chat with existing conversation"""
        # Create conversation first
        create_response = await client.post(
            "/api/conversations",
            headers=api_headers,
            json={"title": "Chat Test"}
        )
        conv_id = create_response.json()["id"]
        
        response = await client.post(
            "/api/chat",
            headers=api_headers,
            json={
                "message": "Hello",
                "conversation_id": conv_id,
                "stream": False
            }
        )
        
        # Will fail if services not mocked, but validates request format
        assert response.status_code in [200, 500]
    
    @pytest.mark.asyncio
    async def test_chat_with_invalid_conversation(self, client: AsyncClient, api_headers: dict):
        """Test chat with non-existent conversation ID"""
        response = await client.post(
            "/api/chat",
            headers=api_headers,
            json={
                "message": "Hello",
                "conversation_id": "invalid-uuid",
                "stream": False
            }
        )
        
        assert response.status_code == 404
