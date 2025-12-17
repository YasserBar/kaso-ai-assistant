"""
Chat API Endpoint
=================
Streaming chat with RAG support
"""

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, Conversation, Message
from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
import logging

# Module logger for structured diagnostics
logger = logging.getLogger(__name__)

router = APIRouter()


async def stream_response(
    query: str,
    conversation_id: str,
    db: AsyncSession
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response with SSE format.

    This function orchestrates:
    - Retrieval Augmented Generation (RAG) to fetch relevant context and sources.
    - Constructing a system prompt via llm_service based on detected language and context.
    - Reading conversation history from the database and appending the user query.
    - Streaming tokens from the LLM as Server-Sent Events (SSE).

    SSE events emitted:
    - event: sources — metadata about retrieved sources (emitted first).
    - event: token — individual tokens of the assistant's response.
    - event: done — completion signal with the conversation_id.
    - event: error — emitted if an exception occurs during processing.

    Notes:
    - User message is committed to the DB immediately to avoid losing input on errors.
    - Assistant message is saved after streaming completes.
    - Conversation title is updated on first exchange using a preview of the query.
    """
    try:
        # Step 1: RAG - Retrieve and build context
        context, language, sources = rag_service.process_query(query)
        
        # Send sources first so the client can display citations/info early (SSE event: sources)
        yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"
        
        # Step 2: Build system prompt from context and language
        system_prompt = llm_service.build_system_prompt(context, language)
        
        # Step 3: Get conversation history ordered by creation time
        messages = []
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        history = result.scalars().all()
        
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current query
        messages.append({"role": "user", "content": query})
        
        # Step 4: Save user message IMMEDIATELY to avoid losing input on errors
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=query
        )
        db.add(user_msg)
        # Persist user input right away so it appears in history even if generation fails
        await db.commit()  # <--- COMMIT HERE
        
        # Step 5: Stream LLM response as SSE tokens
        full_response = ""
        async for token in llm_service.generate_stream(messages, system_prompt):
            full_response += token
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
        
        # Step 6: Save assistant message after streaming completes
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response
        )
        db.add(assistant_msg)
        # Commit assistant message to persist model output
        await db.commit() # <--- COMMIT HERE
        
        # Update conversation title if it's the first exchange
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv and conv.title == "New Conversation":
            # Use first 50 chars of query as title for readability
            conv.title = query[:50] + ("..." if len(query) > 50 else "")
            await db.commit() # <--- COMMIT HERE
        
        # Step 7: Send done signal
        yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"
        
    except Exception as e:
        # Log the error for debugging without exposing sensitive details
        logger.exception("Error in stream_response")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    
    Request body:
    - message: User's question.
    - conversation_id: Optional existing conversation ID.
    
    Returns SSE stream with events:
    - sources: Retrieved source documents.
    - token: Individual response tokens.
    - done: Completion signal with conversation_id.
    - error: Error message if something fails.

    Authentication:
    - Requires X-API-Key header; enforced by APIKeyMiddleware.
    """
    # Get or create conversation
    conversation_id = request.conversation_id
    
    if conversation_id:
        # Verify conversation exists
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation record
        conversation = Conversation()
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        conversation_id = conversation.id
    
    return StreamingResponse(
        stream_response(request.message, conversation_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_non_streaming(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Non-streaming chat endpoint.

    Flow:
    1) Get or create a conversation record.
    2) Run the RAG pipeline to retrieve relevant context and detect language.
    3) Load conversation history and construct the messages array (system + history + user).
    4) Build a system prompt and request a completion from the LLM.
    5) Persist both the user message and assistant response to the database.
    6) Return a ChatResponse with the model output and sources.

    Notes:
    - Requires X-API-Key authentication via middleware.
    - This endpoint returns a single JSON response (no streaming).
    """
    # Get or create conversation
    conversation_id = request.conversation_id
    
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation()
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        conversation_id = conversation.id
    
    # RAG pipeline: context + language + sources
    context, language, sources = rag_service.process_query(request.message)
    
    # Get history, ordered by creation time
    messages = []
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    history = result.scalars().all()
    
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    
    messages.append({"role": "user", "content": request.message})
    
    # Generate response using system prompt
    system_prompt = llm_service.build_system_prompt(context, language)
    response = llm_service.generate(messages, system_prompt)
    
    # Save messages
    user_msg = Message(conversation_id=conversation_id, role="user", content=request.message)
    assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=response)
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()
    
    return ChatResponse(
        message=response,
        conversation_id=conversation_id,
        sources=sources
    )
