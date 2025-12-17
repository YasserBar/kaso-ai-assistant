"""
Search API Endpoint
===================
Search through conversations and knowledge base
"""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import get_db, Conversation, Message
from app.models.schemas import SearchRequest, SearchResponse, SearchHit
from app.services.embedding_service import embedding_service
from app.services.chroma_service import chroma_service


router = APIRouter()


@router.get("/search/conversations")
async def search_conversations(
    query: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Search through conversation history using keyword matching.

    This endpoint performs a simple LIKE-based search over Message.content
    and returns conversation-level summaries for matches. For semantic
    retrieval across the knowledge base, use POST /search instead.

    Query parameters:
    - query: Text to search for (keyword-based).
    - limit: Maximum number of hits to return.
    """
    # Simple LIKE search on message content
    search_pattern = f"%{query}%"
    
    result = await db.execute(
        select(Message)
        .join(Conversation)
        .where(Message.content.ilike(search_pattern))
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    
    # Build unique conversation hits and avoid duplicates
    hits = []
    seen_conversations = set()
    
    for msg in messages:
        if msg.conversation_id in seen_conversations:
            continue
        seen_conversations.add(msg.conversation_id)
        
        # Load conversation metadata
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == msg.conversation_id)
        )
        conv = conv_result.scalar_one_or_none()
        
        if conv:
            hits.append({
                "conversation_id": conv.id,
                "conversation_title": conv.title,
                "message_content": msg.content[:200] + ("..." if len(msg.content) > 200 else ""),
                "message_role": msg.role,
                "relevance_score": 1.0,  # Keyword match
                "created_at": msg.created_at.isoformat()
            })
    
    return {
        "query": query,
        "results": hits,
        "total": len(hits)
    }


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Semantic search through conversations and knowledge base.

    Behavior:
    - Uses ChromaDB for knowledge base retrieval (semantic similarity).
    - Uses simple keyword search over Message content for conversation history.
    - In production, message embeddings should be stored to enable true semantic history search.

    Request body:
    - query: Text to search for.
    - limit: Max number of results (applied independently to KB and history).
    """
    # Get query embedding for KB semantic search (history currently uses keyword LIKE)
    query_embedding = embedding_service.embed_text(request.query)
    
    # Search knowledge base (semantic similarity)
    kb_results = chroma_service.query(
        request.query,
        n_results=request.limit
    )
    
    # Also search message history using LIKE (for production: store embeddings for true semantic search)
    search_pattern = f"%{request.query}%"
    
    result = await db.execute(
        select(Message)
        .join(Conversation)
        .where(Message.content.ilike(search_pattern))
        .order_by(Message.created_at.desc())
        .limit(request.limit)
    )
    messages = result.scalars().all()
    
    hits = []
    
    # Add message hits mapped to SearchHit schema
    for msg in messages:
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == msg.conversation_id)
        )
        conv = conv_result.scalar_one_or_none()
        
        if conv:
            hits.append(SearchHit(
                conversation_id=conv.id,
                conversation_title=conv.title,
                message_content=msg.content[:200] + ("..." if len(msg.content) > 200 else ""),
                message_role=msg.role,
                relevance_score=0.8,  # Lower score for keyword match
                created_at=msg.created_at
            ))
    
    # Deduplicate by conversation
    seen = set()
    unique_hits = []
    for hit in hits:
        if hit.conversation_id not in seen:
            seen.add(hit.conversation_id)
            unique_hits.append(hit)
    
    return SearchResponse(
        query=request.query,
        results=unique_hits[:request.limit],
        total=len(unique_hits)
    )


@router.get("/search/knowledge")
async def search_knowledge_base(
    query: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Search directly in the knowledge base (ChromaDB).

    Returns raw document chunks with metadata and distance scores.

    Query parameters:
    - query: Text for semantic search.
    - limit: Number of chunks to return.
    """
    results = chroma_service.query(query, n_results=limit)
    
    documents = []
    for i in range(len(results["documents"])):
        documents.append({
            "id": results["ids"][i],
            "content": results["documents"][i],
            "source": results["metadatas"][i].get("source", "Unknown"),
            "distance": results["distances"][i]
        })
    
    return {
        "query": query,
        "results": documents,
        "total": len(documents)
    }
