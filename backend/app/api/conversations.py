"""
Conversations API Endpoint
==========================
CRUD operations for chat conversations
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import get_db, Conversation, Message
from app.models.schemas import (
    ConversationCreate,
    ConversationSummary,
    ConversationDetail,
    ConversationMessage,
    ConversationList
)


router = APIRouter()


@router.get("/conversations", response_model=ConversationList)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List all conversations with pagination
    Returns summary info including message preview
    """
    # Count total
    count_result = await db.execute(select(func.count(Conversation.id)))
    total = count_result.scalar()
    
    # Get paginated conversations
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .order_by(desc(Conversation.updated_at))
        .offset(offset)
        .limit(page_size)
    )
    conversations = result.scalars().all()
    
    # Build summaries for pagination cards
    summaries = []
    for conv in conversations:
        # Derive preview from the latest user message for better context in listings
        preview = ""
        message_count = len(conv.messages)
        if conv.messages:
            for msg in reversed(conv.messages):
                if msg.role == "user":
                    preview = msg.content[:100] + ("..." if len(msg.content) > 100 else "")
                    break
        
        summaries.append(ConversationSummary(
            id=conv.id,
            title=conv.title,
            preview=preview,
            message_count=message_count,
            created_at=conv.created_at,
            updated_at=conv.updated_at
        ))
    
    return ConversationList(
        conversations=summaries,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single conversation with all messages
    """
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = [
        ConversationMessage(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at
        )
        for msg in sorted(conversation.messages, key=lambda m: m.created_at)
    ]
    
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        messages=messages,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )


@router.post("/conversations", response_model=ConversationSummary)
async def create_conversation(
    request: ConversationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new empty conversation
    """
    conversation = Conversation(
        title=request.title or "New Conversation"
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return ConversationSummary(
        id=conversation.id,
        title=conversation.title,
        preview="",
        message_count=0,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at
    )


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    title: str = Query(..., min_length=1, max_length=255),
    db: AsyncSession = Depends(get_db)
):
    """
    Update conversation title
    """
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Update conversation title endpoint: simple metadata update only
    conversation.title = title
    await db.commit()
    
    return {"message": "Conversation updated", "id": conversation_id}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a conversation and all its messages
    """
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Delete conversation: cascades delete messages via relationship config
    await db.delete(conversation)
    await db.commit()
    
    return {"message": "Conversation deleted", "id": conversation_id}
