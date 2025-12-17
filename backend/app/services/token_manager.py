"""
Token Manager Service
======================
Intelligent token budget management for conversations.

This module implements a hybrid sliding window + summarization strategy:
- Keeps recent N messages in full (sliding window)
- Summarizes older messages to preserve key context
- Dynamically adjusts based on available token budget

This prevents context window overflow and reduces costs while maintaining
conversation quality.
"""

import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Intelligent token budget management for conversations.

    Strategy:
    - Keep recent N messages in full (sliding window)
    - Summarize older messages to preserve key context
    - Dynamically adjust based on available budget

    This ensures conversations never exceed the model's context window
    while preserving important information from the conversation history.
    """

    def __init__(self):
        """Initialize token manager with budget limits"""

        # Try to import tiktoken for accurate token counting
        try:
            import tiktoken
            # llama-3.1 uses a different tokenizer, but we approximate with GPT-3.5
            # This is okay for estimation purposes
            try:
                self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
            except:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")

            self._tiktoken_available = True
            logger.info("Token manager: Using tiktoken for accurate token counting")

        except ImportError:
            self._tiktoken_available = False
            logger.warning(
                "tiktoken not available. Using approximate token counting. "
                "Install with: pip install tiktoken"
            )

        # Token budgets (conservative estimates for llama-3.1-8b-instant)
        self.MAX_CONTEXT_WINDOW = 8000  # Model's maximum context window
        self.SYSTEM_PROMPT_BUFFER = 1000  # System prompt + RAG context
        self.RESPONSE_BUFFER = 1024  # Max tokens for response
        self.SAFETY_MARGIN = 500  # Safety buffer

        # Available for conversation history
        self.HISTORY_BUDGET = (
            self.MAX_CONTEXT_WINDOW
            - self.SYSTEM_PROMPT_BUFFER
            - self.RESPONSE_BUFFER
            - self.SAFETY_MARGIN
        )  # ~5500 tokens

        # Sliding window configuration
        self.RECENT_MESSAGES_KEEP = 10  # Keep last 10 messages in full
        self.SUMMARIZE_BATCH_SIZE = 10  # Summarize every 10 old messages

        logger.info(
            f"Token manager initialized: "
            f"max_context={self.MAX_CONTEXT_WINDOW}, "
            f"history_budget={self.HISTORY_BUDGET}, "
            f"recent_keep={self.RECENT_MESSAGES_KEEP}"
        )

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        if self._tiktoken_available:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"tiktoken encoding failed: {e}. Using approximation.")

        # Fallback: Rough approximation (1 token ≈ 4 characters for English/Arabic)
        return len(text) // 4

    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count total tokens in message list.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Total token count including message overhead
        """
        total = 0

        for msg in messages:
            # Message format overhead: role + content + formatting
            content = msg.get("content", "")
            total += self.count_tokens(content)
            total += 4  # Role overhead and formatting tokens

        return total

    def optimize_history(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = ""
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        Optimize conversation history to fit within token budget.

        This is the main entry point for token management. It analyzes the
        conversation history and applies the appropriate optimization strategy.

        Args:
            messages: Full conversation history
            system_prompt: System prompt to account for (optional)

        Returns:
            Tuple of (optimized_messages, metadata)
            - optimized_messages: Token-optimized message list
            - metadata: Dict with optimization stats
        """
        if not messages:
            return [], {
                'original_count': 0,
                'optimized_count': 0,
                'original_tokens': 0,
                'optimized_tokens': 0,
                'strategy_used': 'none_empty',
                'summary_created': False
            }

        original_count = len(messages)
        original_tokens = self.count_messages_tokens(messages)

        # Account for system prompt
        system_tokens = self.count_tokens(system_prompt) if system_prompt else 0
        available_budget = self.HISTORY_BUDGET - system_tokens

        metadata = {
            'original_count': original_count,
            'original_tokens': original_tokens,
            'system_tokens': system_tokens,
            'available_budget': available_budget,
            'summary_created': False
        }

        # ============================================
        # STRATEGY 1: No optimization needed
        # ============================================
        if original_tokens <= available_budget:
            metadata['optimized_count'] = original_count
            metadata['optimized_tokens'] = original_tokens
            metadata['strategy_used'] = 'none_needed'

            logger.debug(
                f"Token optimization: No optimization needed. "
                f"tokens={original_tokens}/{available_budget}"
            )

            return messages, metadata

        # ============================================
        # STRATEGY 2: Sliding window (keep recent N messages)
        # ============================================
        if original_count > self.RECENT_MESSAGES_KEEP:
            recent_messages = messages[-self.RECENT_MESSAGES_KEEP:]
            recent_tokens = self.count_messages_tokens(recent_messages)

            if recent_tokens <= available_budget:
                metadata['optimized_count'] = len(recent_messages)
                metadata['optimized_tokens'] = recent_tokens
                metadata['strategy_used'] = 'sliding_window'
                metadata['messages_dropped'] = original_count - len(recent_messages)

                logger.info(
                    f"Token optimization: Sliding window applied. "
                    f"kept={len(recent_messages)}, dropped={metadata['messages_dropped']}, "
                    f"tokens={recent_tokens}/{available_budget}"
                )

                return recent_messages, metadata

        # ============================================
        # STRATEGY 3: Sliding window + Summarization
        # ============================================
        # Split into: [old_messages] + [recent_messages]
        old_messages = messages[:-self.RECENT_MESSAGES_KEEP] if len(messages) > self.RECENT_MESSAGES_KEEP else []
        recent_messages = messages[-self.RECENT_MESSAGES_KEEP:]

        if old_messages:
            # Summarize old messages
            summary = self._summarize_messages(old_messages)

            summary_message = {
                "role": "system",
                "content": f"[Previous Conversation Summary - {len(old_messages)} messages]: {summary}"
            }

            optimized = [summary_message] + recent_messages
            optimized_tokens = self.count_messages_tokens(optimized)

            # Check if summary + recent fits
            if optimized_tokens <= available_budget:
                metadata['optimized_count'] = len(optimized)
                metadata['optimized_tokens'] = optimized_tokens
                metadata['strategy_used'] = 'summarization_hybrid'
                metadata['summary_created'] = True
                metadata['messages_summarized'] = len(old_messages)
                metadata['messages_kept_full'] = len(recent_messages)

                logger.info(
                    f"Token optimization: Summarization hybrid applied. "
                    f"summarized={len(old_messages)}, kept_full={len(recent_messages)}, "
                    f"tokens={optimized_tokens}/{available_budget}"
                )

                return optimized, metadata

        # ============================================
        # STRATEGY 4: Aggressive truncation (last resort)
        # ============================================
        # Keep reducing recent messages until it fits
        for n in range(self.RECENT_MESSAGES_KEEP, 0, -2):
            truncated = messages[-n:]
            truncated_tokens = self.count_messages_tokens(truncated)

            if truncated_tokens <= available_budget:
                metadata['optimized_count'] = len(truncated)
                metadata['optimized_tokens'] = truncated_tokens
                metadata['strategy_used'] = 'aggressive_truncation'
                metadata['messages_dropped'] = original_count - len(truncated)

                logger.warning(
                    f"Token optimization: Aggressive truncation applied! "
                    f"kept={len(truncated)}, dropped={metadata['messages_dropped']}, "
                    f"tokens={truncated_tokens}/{available_budget}"
                )

                return truncated, metadata

        # ============================================
        # EXTREME FALLBACK: Just last 2 messages
        # ============================================
        fallback = messages[-2:] if len(messages) >= 2 else messages
        fallback_tokens = self.count_messages_tokens(fallback)

        metadata['optimized_count'] = len(fallback)
        metadata['optimized_tokens'] = fallback_tokens
        metadata['strategy_used'] = 'extreme_fallback'
        metadata['messages_dropped'] = original_count - len(fallback)

        logger.error(
            f"Token optimization: EXTREME FALLBACK triggered! "
            f"kept={len(fallback)}, dropped={metadata['messages_dropped']}, "
            f"tokens={fallback_tokens}/{available_budget}. "
            f"This should rarely happen."
        )

        return fallback, metadata

    def _summarize_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Summarize a batch of messages into a concise summary.

        This uses the LLM to create an extractive summary preserving key facts.

        Args:
            messages: List of messages to summarize

        Returns:
            Summary string
        """
        # Build conversation text
        conversation_text = ""
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"

        # Truncate if too long (prevent summary from being too expensive)
        if len(conversation_text) > 4000:
            conversation_text = conversation_text[:4000] + "...[truncated]"

        summary_prompt = f"""Summarize the following conversation between a user and Kaso restaurant chatbot.

CRITICAL REQUIREMENTS:
1. Extract and preserve KEY FACTS mentioned (locations, prices, menu items, hours, contact info, etc.)
2. Keep the summary under 200 words
3. Use the SAME LANGUAGE as the conversation (Arabic or English)
4. Focus on INFORMATION, not chit-chat or greetings
5. Format as concise bullet points for clarity

CONVERSATION TO SUMMARIZE:
{conversation_text}

CONCISE SUMMARY (bullet points with key facts only):"""

        try:
            from app.services.llm_service import llm_service

            messages_for_llm = [{"role": "user", "content": summary_prompt}]
            summary = llm_service.generate(
                messages=messages_for_llm,
                system_prompt="You are a precise conversation summarizer. Extract only key facts in bullet points."
            )

            # Validate summary length (shouldn't be too long)
            summary = summary.strip()
            if len(summary) > 1000:
                summary = summary[:1000] + "..."

            logger.debug(f"Conversation summary created: {len(summary)} chars")
            return summary

        except Exception as e:
            # Fallback: simple truncation if summarization fails
            logger.error(f"Message summarization failed: {e}. Using simple fallback.")
            return f"[Previous conversation: {len(messages)} messages about Kaso restaurant. Key context may be incomplete due to summarization failure.]"

    def estimate_prompt_tokens(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> Dict[str, int]:
        """
        Estimate total prompt tokens for transparency and debugging.

        Args:
            system_prompt: System prompt text
            messages: Message list

        Returns:
            Dict with token breakdown
        """
        system_tokens = self.count_tokens(system_prompt)
        messages_tokens = self.count_messages_tokens(messages)
        total = system_tokens + messages_tokens

        return {
            'system_prompt_tokens': system_tokens,
            'messages_tokens': messages_tokens,
            'total_prompt_tokens': total,
            'budget_remaining': self.HISTORY_BUDGET - total,
            'budget_total': self.HISTORY_BUDGET,
            'budget_utilization_pct': int((total / self.HISTORY_BUDGET) * 100)
        }


# Singleton instance
token_manager = TokenManager()
