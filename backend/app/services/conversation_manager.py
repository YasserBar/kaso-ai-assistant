"""
Conversation Manager Service
==============================
Manages conversation context and query reformulation for better RAG.

This module improves context awareness by:
1. Reformulating follow-up questions to be self-contained
2. Extracting conversation context for the system prompt
3. Helping the model understand references and pronouns

This solves the problem of vague follow-up questions like:
User: "Where is Kaso branch in Cairo?"
Assistant: "It's in Nasr City..."
User: "What are the hours?" ← needs context: "hours of Nasr City branch"
"""

import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation context and query reformulation for better RAG.
    """

    def __init__(self):
        """Initialize conversation manager with patterns and settings"""

        # Dependency indicators (signals that query needs context from history)
        self.dependency_patterns = [
            # English pronouns and references
            r'\b(it|that|this|these|those|there|here)\b',
            # Arabic pronouns and references
            r'\b(هذا|ذلك|هناك|هنا|فيه|به|منه|عنه|ها|هم)\b',
            # Follow-up question starters
            r'^(what about|how about|and|also|too|أيضا|كمان|كذلك|و)\b',
            # Vague references
            r'\b(one|ones|الواحد|الأول|الثاني)\b',
        ]

        # Entity indicators (signals that query is self-contained)
        self.entity_patterns = [
            r'\b(kaso|كاسو|كازو)\b',
            r'\b(menu|قائمة|منيو|مينو)\b',
            r'\b(branch|فرع|فروع|location|موقع|عنوان)\b',
            r'\b(price|سعر|أسعار|cost|تكلفة)\b',
            r'\b(hours|ساعات|مواعيد|timing|وقت)\b',
            r'\b(delivery|توصيل|طلب|order)\b',
            r'\b(restaurant|مطعم|food|طعام|أكل)\b',
        ]

        logger.info("Conversation manager initialized")

    def reformulate_query(
        self,
        current_query: str,
        chat_history: List[Dict[str, str]],
        max_history: int = 3
    ) -> Tuple[str, str]:
        """
        Reformulate user query by incorporating conversation context.

        This solves the problem of follow-up questions like:
        User: "Where is Kaso branch in Cairo?"
        Assistant: "It's in Nasr City..."
        User: "What are the hours?" ← needs context: "hours of Nasr City branch"

        Args:
            current_query: The new user question
            chat_history: Recent conversation messages (list of dicts with 'role' and 'content')
            max_history: How many previous turns to consider (default: 3)

        Returns:
            Tuple of (original_query, reformulated_query)
            If reformulation isn't needed, both will be the same.
        """
        # Empty check
        if not current_query or not current_query.strip():
            return current_query, current_query

        # If history is empty or very short, no reformulation needed
        if not chat_history or len(chat_history) < 2:
            logger.debug("Reformulation skipped: insufficient history")
            return current_query, current_query

        # Check if query is already self-contained
        if self._is_self_contained(current_query):
            logger.debug(f"Reformulation skipped: query is self-contained")
            return current_query, current_query

        # Get recent conversation turns (last N turns)
        recent_history = chat_history[-max_history * 2:] if len(chat_history) > max_history * 2 else chat_history

        # Build context for reformulation
        history_text = ""
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"]
            # Truncate very long messages
            if len(content) > 300:
                content = content[:300] + "..."
            history_text += f"{role}: {content}\n"

        # Use LLM to reformulate query
        reformulated = self._llm_reformulate(current_query, history_text)

        # Validation: reformulated shouldn't be too different in length
        # (prevents LLM from going rogue and generating a long explanation)
        if len(reformulated) > len(current_query) * 3:
            logger.warning(
                f"Reformulation rejected: too long. "
                f"original={len(current_query)}, reformulated={len(reformulated)}"
            )
            return current_query, current_query

        # Log reformulation for monitoring
        if reformulated != current_query:
            logger.info(
                f"Query reformulated: "
                f"original='{current_query}' → "
                f"reformulated='{reformulated}'"
            )

        return current_query, reformulated

    def _is_self_contained(self, query: str) -> bool:
        """
        Heuristic to detect if query is self-contained.

        A query is self-contained if:
        - It doesn't use pronouns/references that depend on context
        - It contains clear entities (Kaso, menu, branch, etc.)

        Args:
            query: User query to check

        Returns:
            True if self-contained, False if likely needs context
        """
        query_lower = query.lower()

        # Check for dependency indicators
        has_dependency = any(
            re.search(pattern, query_lower, re.IGNORECASE)
            for pattern in self.dependency_patterns
        )

        if has_dependency:
            # Has pronouns/references - likely depends on context
            logger.debug(f"Query has dependency indicators: '{query}'")
            return False

        # Check for entity indicators
        entity_count = sum(
            1 for pattern in self.entity_patterns
            if re.search(pattern, query_lower, re.IGNORECASE)
        )

        # Self-contained if has entities and no dependency indicators
        is_self_contained = entity_count >= 1

        logger.debug(
            f"Query self-contained check: "
            f"entities={entity_count}, "
            f"result={is_self_contained}"
        )

        return is_self_contained

    def _llm_reformulate(self, query: str, history_text: str) -> str:
        """
        Use LLM to reformulate query with context from history.

        Args:
            query: Current user query
            history_text: Recent conversation history as text

        Returns:
            Reformulated query (or original if reformulation fails)
        """
        reformulation_prompt = f"""You are a query reformulation assistant.

Given a conversation history and a new user question, your task is to reformulate the question to be SELF-CONTAINED by incorporating necessary context from history.

IMPORTANT RULES:
1. If the new question is already self-contained (has all necessary context), return it UNCHANGED
2. If the question uses pronouns (it, that, there, هذا, ذلك, هناك) or refers to previous context, rewrite it with explicit entities
3. Keep the reformulated question concise and in the SAME LANGUAGE as the original
4. DO NOT answer the question - only reformulate it
5. Return ONLY the reformulated question, nothing else (no explanations, no extra text)
6. Preserve the question type (don't turn "Where?" into "What is the location?")

EXAMPLES:

Example 1:
History: User asked "Where is Kaso branch in Cairo?" Assistant said "It's in Nasr City"
New question: "What are the hours?"
Reformulated: "What are the hours of Kaso branch in Nasr City?"

Example 2:
History: User asked "Do you have burgers?" Assistant said "Yes, we have beef and chicken burgers"
New question: "How much is it?"
Reformulated: "How much is the burger at Kaso?"

Example 3:
History: User asked "أين يقع فرع كاسو؟" Assistant said "يقع في مدينة نصر"
New question: "ما ساعات العمل؟"
Reformulated: "ما ساعات عمل فرع كاسو في مدينة نصر؟"

Example 4 (already self-contained):
History: User discussed burgers
New question: "Where is Kaso restaurant located?"
Reformulated: "Where is Kaso restaurant located?" (unchanged - already self-contained)

CONVERSATION HISTORY:
{history_text}

NEW USER QUESTION: {query}

REFORMULATED QUESTION (same language, no extra text):"""

        try:
            from app.services.llm_service import llm_service

            messages = [{"role": "user", "content": reformulation_prompt}]
            reformulated = llm_service.generate(
                messages=messages,
                system_prompt="You are a precise query reformulation assistant. Return ONLY the reformulated question with no extra text or explanation."
            )

            reformulated = reformulated.strip()

            # Remove any quotes that LLM might have added
            reformulated = reformulated.strip('"\'')

            # Validation: should still be a question (ends with ? or similar)
            # But don't be too strict (some languages don't always use ?)
            if reformulated:
                return reformulated
            else:
                logger.warning("Reformulation returned empty string")
                return query

        except Exception as e:
            # Fail gracefully - return original query
            logger.error(f"Query reformulation failed: {e}")
            return query

    def extract_conversation_context(
        self,
        chat_history: List[Dict[str, str]],
        max_messages: int = 6
    ) -> str:
        """
        Extract key facts from recent conversation to augment system prompt.

        This helps the model remember what was discussed previously.

        Args:
            chat_history: Full conversation history
            max_messages: Maximum number of recent messages to extract (default: 6)

        Returns:
            String summarizing recent conversation context
        """
        if not chat_history:
            return ""

        # Get recent messages
        recent = chat_history[-max_messages:] if len(chat_history) > max_messages else chat_history

        context_lines = []
        for msg in recent:
            role = msg["role"]
            content = msg.get("content", "")

            # Truncate very long messages for context
            if len(content) > 200:
                content = content[:200] + "..."

            if role == "user":
                context_lines.append(f"• User asked: {content}")
            elif role == "assistant":
                context_lines.append(f"• Assistant replied: {content}")

        context = "\n".join(context_lines)

        logger.debug(f"Extracted conversation context: {len(context)} chars, {len(recent)} messages")

        return context


# Singleton instance
conversation_manager = ConversationManager()
