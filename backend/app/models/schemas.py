"""
Pydantic Schemas for API Request/Response
==========================================
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


# ============================================
# Chat Schemas
# ============================================

class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    """Request for chat endpoint
    - message: user prompt
    - conversation_id: optional existing thread id (new one created if missing)
    - stream: whether to use SSE streaming or standard JSON response
    """
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    """Response from chat endpoint (non-streaming)"""
    message: str
    conversation_id: str
    sources: List[str] = []


class StreamChunk(BaseModel):
    """Single chunk in streaming response
    type: one of token|sources|done|error; content may be a token or error text
    sources: optional citations array; conversation_id included on done
    """
    type: str = Field(..., pattern="^(token|sources|done|error)$")
    content: Optional[str] = None
    sources: Optional[List[str]] = None
    conversation_id: Optional[str] = None


# ============================================
# Conversation Schemas
# ============================================

class ConversationCreate(BaseModel):
    """Create new conversation"""
    title: Optional[str] = None


class ConversationMessage(BaseModel):
    """Message in a conversation"""
    id: str
    role: str
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    """Brief conversation info for listing
    preview: clipped text from latest user message for UI cards
    message_count: total messages in the conversation
    """
    id: str
    title: str
    preview: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    """Full conversation with messages"""
    id: str
    title: str
    messages: List[ConversationMessage]
    created_at: datetime
    updated_at: datetime


class ConversationList(BaseModel):
    """Paginated list of conversations"""
    conversations: List[ConversationSummary]
    total: int
    page: int
    page_size: int


# ============================================
# Search Schemas
# ============================================

class SearchRequest(BaseModel):
    """Search request
    search_type: keyword|semantic|hybrid (currently hybrid does KB semantic + keyword history)
    limit: number of results to return per source
    """
    query: str = Field(..., min_length=1, max_length=500)
    search_type: str = Field(default="hybrid", pattern="^(keyword|semantic|hybrid)$")
    limit: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    """Single search result"""
    conversation_id: str
    conversation_title: str
    message_content: str
    message_role: str
    relevance_score: float
    created_at: datetime


class SearchResponse(BaseModel):
    """Search results"""
    query: str
    results: List[SearchHit]
    total: int


# ============================================
# Knowledge Base Schemas
# ============================================

class KnowledgeChunk(BaseModel):
    """Single chunk from knowledge base
    metadata: arbitrary info such as source URL, title, etc.
    """
    id: str
    content: str
    source: str
    metadata: dict = {}


class KnowledgeSource(BaseModel):
    """Data source for knowledge base"""
    id: int
    url: str
    title: Optional[str] = None
    status: str = "pending"
    last_scraped: Optional[datetime] = None
    chunk_count: int = 0
