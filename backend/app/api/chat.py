"""
Chat API Endpoint
=================
Streaming chat with RAG support

UPDATED: Integrated multi-layer defense system:
- Intent Classification: Filter off-topic queries before processing
- Conversation Management: Query reformulation and context awareness
- Token Management: Prevent context window overflow with smart optimization
- Response Validation: Post-generation quality checks
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
from app.services.intent_classifier import intent_classifier
from app.services.conversation_manager import conversation_manager
from app.services.token_manager import token_manager
from app.services.response_validator import response_validator
from app.services.multilingual_service import multilingual_service
from app.config import settings
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

    UPDATED: Integrated multi-layer defense pipeline with 7 phases:
    1. Intent Classification - Filter off-topic queries
    2. Load History - Retrieve conversation from database
    3. Conversational RAG - Query reformulation + context extraction
    4. Build System Prompt - Enhanced with conversation context
    5. Token Management - Optimize history to prevent overflow
    6. Generate Response - Stream LLM tokens
    7. Validation & Save - Post-generation checks and persistence

    SSE events emitted:
    - event: sources — metadata about retrieved sources (emitted first).
    - event: token — individual tokens of the assistant's response.
    - event: done — completion signal with the conversation_id.
    - event: error — emitted if an exception occurs during processing.
    - event: debug — debug information (only if debug_mode=True in settings)

    Notes:
    - User message is committed to the DB immediately to avoid losing input on errors.
    - Assistant message is saved after streaming completes.
    - Conversation title is updated on first exchange using a preview of the query.
    """
    try:
        # ═══════════════════════════════════════════════════════════════
        # PHASE 1: INTENT CLASSIFICATION + COMPANY DISAMBIGUATION
        # ═══════════════════════════════════════════════════════════════
        logger.info(f"[PHASE 1] Intent classification + company disambiguation for query: '{query[:100]}...'")

        # Step 1a: Company disambiguation (fast layer - <1ms)
        if settings.company_disambiguation_enabled:
            from app.services.company_disambiguator import company_disambiguator

            disambiguation_result = company_disambiguator.analyze_query(query)
            logger.info(
                f"Company disambiguation: is_b2b_platform={disambiguation_result.is_kaso_b2b_platform}, "
                f"confidence={disambiguation_result.confidence:.2f}, reason={disambiguation_result.reason}"
            )

            # If detected non-B2B-platform Kaso company with high confidence, reject immediately
            if (disambiguation_result.is_kaso_b2b_platform == False and
                disambiguation_result.confidence >= settings.company_disambiguation_confidence_threshold):

                logger.info(f"Company disambiguation: REJECTED - {disambiguation_result.reason}")

                detected_language = multilingual_service.detect_language(query)
                refusal_message = multilingual_service.generate_company_disambiguation_refusal(
                    language=detected_language,
                    detected_company=disambiguation_result.detected_company
                )

                # Save refusal and return
                user_msg = Message(conversation_id=conversation_id, role="user", content=query)
                assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=refusal_message)
                db.add(user_msg)
                db.add(assistant_msg)
                await db.commit()

                yield f"event: token\ndata: {json.dumps({'token': refusal_message})}\n\n"
                yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"
                return

        # Step 1b: Standard intent classification (if disambiguation uncertain)
        should_process, reason = intent_classifier.should_process(query)

        if not should_process:
            # Query is off-topic - refuse politely without calling LLM
            logger.info(f"Query rejected: {reason}")

            # UPDATED: Use multilingual service for 100+ languages support
            # Check if rejection reason mentions company confusion
            detected_language = multilingual_service.detect_language(query)

            if "company" in reason.lower() or "kaso" in reason.lower():
                # Use company-specific refusal
                refusal_message = multilingual_service.generate_company_disambiguation_refusal(
                    language=detected_language,
                    detected_company='unknown'
                )
            else:
                # Standard off-topic refusal
                refusal_message = multilingual_service.generate_refusal_message(
                    language=detected_language,
                    use_llm=settings.multilingual_use_llm_for_messages
                )

            logger.info(f"Detected language: {detected_language}, generated refusal message")

            # Save the refusal as a conversation turn
            user_msg = Message(
                conversation_id=conversation_id,
                role="user",
                content=query
            )
            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=refusal_message
            )
            db.add(user_msg)
            db.add(assistant_msg)
            await db.commit()

            # Stream refusal message
            yield f"event: token\ndata: {json.dumps({'token': refusal_message})}\n\n"
            yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"
            return

        logger.info(f"Intent classification passed: {reason}")

        # ═══════════════════════════════════════════════════════════════
        # PHASE 2: LOAD HISTORY
        # ═══════════════════════════════════════════════════════════════
        logger.info(f"[PHASE 2] Loading conversation history")

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        history_records = result.scalars().all()

        # Convert to message format for LLM
        full_history = []
        for msg in history_records:
            full_history.append({"role": msg.role, "content": msg.content})

        logger.info(f"Loaded {len(full_history)} messages from history")

        # ═══════════════════════════════════════════════════════════════
        # PHASE 3: CONVERSATIONAL RAG
        # ═══════════════════════════════════════════════════════════════
        logger.info(f"[PHASE 3] Conversational RAG processing")

        # 3a. Query reformulation (if needed)
        original_query = query
        reformulated_query = query

        if settings.conv_reformulate_queries and len(full_history) >= 2:
            original_query, reformulated_query = conversation_manager.reformulate_query(
                query,
                full_history,
                max_history=settings.conv_max_history_for_reformulation
            )

            if original_query != reformulated_query:
                logger.info(f"Query reformulated: '{original_query}' → '{reformulated_query}'")

                # Send debug event if enabled
                if settings.debug_mode:
                    yield f"event: debug\ndata: {json.dumps({'reformulated_query': reformulated_query})}\n\n"

        # 3b. RAG with reformulated query
        context, language, sources = rag_service.process_query(reformulated_query)

        # Send sources event
        yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"

        # 3c. Extract conversation context for system prompt
        conv_context = ""
        if len(full_history) > 0:
            conv_context = conversation_manager.extract_conversation_context(
                full_history,
                max_messages=settings.conv_context_messages
            )
            logger.debug(f"Extracted conversation context: {len(conv_context)} chars")

        # ═══════════════════════════════════════════════════════════════
        # PHASE 4: BUILD SYSTEM PROMPT
        # ═══════════════════════════════════════════════════════════════
        logger.info(f"[PHASE 4] Building enhanced system prompt")

        system_prompt = llm_service.build_system_prompt(
            context=context,
            language=language,
            conversation_context=conv_context  # NEW: Include conversation context
        )

        # ═══════════════════════════════════════════════════════════════
        # PHASE 5: TOKEN MANAGEMENT
        # ═══════════════════════════════════════════════════════════════
        logger.info(f"[PHASE 5] Token management and optimization")

        optimized_history, metadata = token_manager.optimize_history(
            messages=full_history,
            system_prompt=system_prompt
        )

        logger.info(
            f"Token optimization: "
            f"original={metadata['original_count']} msgs ({metadata['original_tokens']} tokens), "
            f"optimized={metadata['optimized_count']} msgs ({metadata['optimized_tokens']} tokens), "
            f"strategy={metadata['strategy_used']}"
        )

        # Send debug event if enabled
        if settings.debug_mode:
            yield f"event: debug\ndata: {json.dumps(metadata)}\n\n"

        # ═══════════════════════════════════════════════════════════════
        # PHASE 6: GENERATE RESPONSE
        # ═══════════════════════════════════════════════════════════════
        logger.info(f"[PHASE 6] Generating LLM response")

        # Save user message FIRST to avoid losing input on errors
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=query  # Save original query, not reformulated
        )
        db.add(user_msg)
        await db.commit()

        # Append current query to optimized history
        optimized_history.append({"role": "user", "content": query})

        # Stream LLM response
        full_response = ""
        async for token in llm_service.generate_stream(optimized_history, system_prompt):
            full_response += token
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

        logger.info(f"Generated response: {len(full_response)} chars")

        # ═══════════════════════════════════════════════════════════════
        # PHASE 7: VALIDATION & SAVE
        # ═══════════════════════════════════════════════════════════════
        logger.info(f"[PHASE 7] Response validation and saving")

        # Validate response quality
        is_valid, validation_msg = response_validator.validate(
            query=query,
            response=full_response,
            context=context
        )

        if not is_valid:
            logger.warning(f"Response validation failed: {validation_msg}")
            # Note: We still save the response, but log the warning for monitoring
        else:
            logger.info(f"Response validation passed: {validation_msg}")

        # Save assistant message
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response
        )
        db.add(assistant_msg)
        await db.commit()

        # Update conversation title if it's the first exchange
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv and conv.title == "New Conversation":
            conv.title = query[:50] + ("..." if len(query) > 50 else "")
            await db.commit()

        # Send done signal
        yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"

        logger.info(f"Stream completed successfully for conversation {conversation_id}")

    except Exception as e:
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

    UPDATED: Integrated multi-layer defense pipeline with 7 phases:
    1. Intent Classification - Filter off-topic queries
    2. Load History - Retrieve conversation from database
    3. Conversational RAG - Query reformulation + context extraction
    4. Build System Prompt - Enhanced with conversation context
    5. Token Management - Optimize history to prevent overflow
    6. Generate Response - Get complete LLM response
    7. Validation & Save - Post-generation checks and persistence

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

    query = request.message

    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: INTENT CLASSIFICATION + COMPANY DISAMBIGUATION
    # ═══════════════════════════════════════════════════════════════
    logger.info(f"[PHASE 1] Intent classification + company disambiguation for query: '{query[:100]}...'")

    # Step 1a: Company disambiguation (fast layer - <1ms)
    if settings.company_disambiguation_enabled:
        from app.services.company_disambiguator import company_disambiguator

        disambiguation_result = company_disambiguator.analyze_query(query)
        logger.info(
            f"Company disambiguation: is_b2b_platform={disambiguation_result.is_kaso_b2b_platform}, "
            f"confidence={disambiguation_result.confidence:.2f}, reason={disambiguation_result.reason}"
        )

        # If detected non-B2B-platform Kaso company with high confidence, reject immediately
        if (disambiguation_result.is_kaso_b2b_platform == False and
            disambiguation_result.confidence >= settings.company_disambiguation_confidence_threshold):

            logger.info(f"Company disambiguation: REJECTED - {disambiguation_result.reason}")

            detected_language = multilingual_service.detect_language(query)
            refusal_message = multilingual_service.generate_company_disambiguation_refusal(
                language=detected_language,
                detected_company=disambiguation_result.detected_company
            )

            # Save refusal and return
            user_msg = Message(conversation_id=conversation_id, role="user", content=query)
            assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=refusal_message)
            db.add(user_msg)
            db.add(assistant_msg)
            await db.commit()

            return ChatResponse(
                message=refusal_message,
                conversation_id=conversation_id,
                sources=[]
            )

    # Step 1b: Standard intent classification (if disambiguation uncertain)
    should_process, reason = intent_classifier.should_process(query)

    if not should_process:
        logger.info(f"Query rejected: {reason}")

        # UPDATED: Use multilingual service for 100+ languages support
        # Check if rejection reason mentions company confusion
        detected_language = multilingual_service.detect_language(query)

        if "company" in reason.lower() or "kaso" in reason.lower():
            # Use company-specific refusal
            refusal_message = multilingual_service.generate_company_disambiguation_refusal(
                language=detected_language,
                detected_company='unknown'
            )
        else:
            # Standard off-topic refusal
            refusal_message = multilingual_service.generate_refusal_message(
                language=detected_language,
                use_llm=settings.multilingual_use_llm_for_messages
            )

        logger.info(f"Detected language: {detected_language}, generated refusal message")

        # Save the refusal as a conversation turn
        user_msg = Message(conversation_id=conversation_id, role="user", content=query)
        assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=refusal_message)
        db.add(user_msg)
        db.add(assistant_msg)
        await db.commit()

        return ChatResponse(
            message=refusal_message,
            conversation_id=conversation_id,
            sources=[]
        )

    logger.info(f"Intent classification passed: {reason}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: LOAD HISTORY
    # ═══════════════════════════════════════════════════════════════
    logger.info(f"[PHASE 2] Loading conversation history")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    history_records = result.scalars().all()

    full_history = []
    for msg in history_records:
        full_history.append({"role": msg.role, "content": msg.content})

    logger.info(f"Loaded {len(full_history)} messages from history")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: CONVERSATIONAL RAG
    # ═══════════════════════════════════════════════════════════════
    logger.info(f"[PHASE 3] Conversational RAG processing")

    # Query reformulation
    original_query = query
    reformulated_query = query

    if settings.conv_reformulate_queries and len(full_history) >= 2:
        original_query, reformulated_query = conversation_manager.reformulate_query(
            query,
            full_history,
            max_history=settings.conv_max_history_for_reformulation
        )

        if original_query != reformulated_query:
            logger.info(f"Query reformulated: '{original_query}' → '{reformulated_query}'")

    # RAG with reformulated query
    context, language, sources = rag_service.process_query(reformulated_query)

    # Extract conversation context
    conv_context = ""
    if len(full_history) > 0:
        conv_context = conversation_manager.extract_conversation_context(
            full_history,
            max_messages=settings.conv_context_messages
        )

    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: BUILD SYSTEM PROMPT
    # ═══════════════════════════════════════════════════════════════
    logger.info(f"[PHASE 4] Building enhanced system prompt")

    system_prompt = llm_service.build_system_prompt(
        context=context,
        language=language,
        conversation_context=conv_context
    )

    # ═══════════════════════════════════════════════════════════════
    # PHASE 5: TOKEN MANAGEMENT
    # ═══════════════════════════════════════════════════════════════
    logger.info(f"[PHASE 5] Token management and optimization")

    optimized_history, metadata = token_manager.optimize_history(
        messages=full_history,
        system_prompt=system_prompt
    )

    logger.info(
        f"Token optimization: "
        f"original={metadata['original_count']} msgs ({metadata['original_tokens']} tokens), "
        f"optimized={metadata['optimized_count']} msgs ({metadata['optimized_tokens']} tokens), "
        f"strategy={metadata['strategy_used']}"
    )

    # ═══════════════════════════════════════════════════════════════
    # PHASE 6: GENERATE RESPONSE
    # ═══════════════════════════════════════════════════════════════
    logger.info(f"[PHASE 6] Generating LLM response")

    # Append current query to optimized history
    optimized_history.append({"role": "user", "content": query})

    # Generate response
    response = llm_service.generate(optimized_history, system_prompt)

    logger.info(f"Generated response: {len(response)} chars")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 7: VALIDATION & SAVE
    # ═══════════════════════════════════════════════════════════════
    logger.info(f"[PHASE 7] Response validation and saving")

    # Validate response
    is_valid, validation_msg = response_validator.validate(
        query=query,
        response=response,
        context=context
    )

    if not is_valid:
        logger.warning(f"Response validation failed: {validation_msg}")
    else:
        logger.info(f"Response validation passed: {validation_msg}")

    # Save messages
    user_msg = Message(conversation_id=conversation_id, role="user", content=query)
    assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=response)
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()

    logger.info(f"Chat completed successfully for conversation {conversation_id}")

    return ChatResponse(
        message=response,
        conversation_id=conversation_id,
        sources=sources
    )
