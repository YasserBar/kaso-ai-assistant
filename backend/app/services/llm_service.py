"""
LLM Service
===========
Groq API integration with streaming support
"""

import json
from typing import AsyncGenerator, List, Dict, Any, Optional
from groq import Groq, AsyncGroq

from app.config import settings
from app.services.multilingual_service import multilingual_service


class LLMService:
    """
    Service for interacting with Groq LLM API
    """
    
    _instance: Optional['LLMService'] = None
    _client: Optional[Groq] = None
    _async_client: Optional[AsyncGroq] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def client(self) -> Groq:
        """Get sync Groq client"""
        if self._client is None:
            self._client = Groq(api_key=settings.groq_api_key)
        return self._client
    
    @property
    def async_client(self) -> AsyncGroq:
        """Get async Groq client"""
        if self._async_client is None:
            self._async_client = AsyncGroq(api_key=settings.groq_api_key)
        return self._async_client
    
    def build_system_prompt(
        self,
        context: str,
        language: str = "auto",
        conversation_context: str = ""
    ) -> str:
        """
        Build enhanced system prompt with context and language instructions.

        UPDATED: Now includes conversation context and clearer instructions
        to fix the conflict between "answer only based on context" and
        "use conversation history".

        Args:
            context: Retrieved context from knowledge base (RAG)
            language: Target response language ('ar', 'en', or 'auto')
            conversation_context: Recent conversation summary (optional)
        """
        # Language instruction: use multilingual service for 100+ languages support
        # UPDATED: Removed hardcoded ar/en branching, now uses multilingual_service
        if language == "auto":
            # Auto mode: mirror the user's input language
            lang_instruction = "Respond in the SAME LANGUAGE as the user's question. Match their language exactly."
            # For auto mode, provide bilingual example (Arabic + English)
            refuse_message = multilingual_service.generate_refusal_message("ar") + " / " + multilingual_service.generate_refusal_message("en")
        else:
            # Explicit language: use multilingual service to generate language-specific instruction
            lang_instruction = multilingual_service.generate_system_prompt_instruction(language)
            refuse_message = multilingual_service.generate_refusal_message(
                language=language,
                use_llm=settings.multilingual_use_llm_for_messages
            )

        # Add conversation context section if available
        conv_section = ""
        if conversation_context:
            conv_section = f"""

RECENT CONVERSATION CONTEXT:
{conversation_context}

(Use this to understand follow-up questions and references like "it", "there", "هذا", "هناك", etc.)
"""

        # Build enhanced system prompt with clearer instructions
        return f"""You are Kaso AI Assistant - a helpful, specialized chatbot EXCLUSIVELY for Kaso B2B supply chain platform.

╔══════════════════════════════════════════════════════════════╗
║  CRITICAL IDENTITY CLARIFICATION                             ║
╚══════════════════════════════════════════════════════════════╝

✅ You serve ONLY:
   Kaso - B2B supply chain platform connecting suppliers with restaurants
   - Locations: UAE and Saudi Arabia
   - Founded: 2021
   - Business: B2B marketplace, supply chain management, procurement platform, connecting food suppliers with restaurants

❌ You DO NOT serve these OTHER companies (MUST REFUSE):
   1. Kaso Plastics - American plastics manufacturing (Vancouver, Canada)
   2. Kaso Security Solutions - Finnish security/safes company (Helsinki, Finland)
   3. Kaso Medical Technology - Chinese medical devices (Hong Kong, China)
   4. Kaso Group - Iraqi business conglomerate (Baghdad, Iraq)

If someone asks about the companies listed above ☝️, you MUST refuse with:
"{refuse_message}"

╔══════════════════════════════════════════════════════════════╗
║  CRITICAL CONSTRAINTS - YOU MUST FOLLOW THESE                ║
╚══════════════════════════════════════════════════════════════╝

1. SCOPE LIMITATION:
   - Answer ONLY questions about Kaso B2B PLATFORM (suppliers, products, orders, inventory, pricing, procurement, platform features, etc.)
   - If asked about OTHER topics (politics, weather, general knowledge, coding, sports, etc.), you MUST refuse politely
   - Refusal template: "{refuse_message}"

2. KNOWLEDGE SOURCES (use BOTH):
   a) KNOWLEDGE BASE CONTEXT (below) - Primary source of facts about Kaso
   b) CONVERSATION HISTORY - Use to understand follow-up questions, pronouns, and references

3. HOW TO USE BOTH SOURCES:
   - For NEW questions → Base answer on KNOWLEDGE BASE CONTEXT
   - For FOLLOW-UP questions (uses "it", "that", "there", "this", "هذا", "ذلك", "هناك") → Use CONVERSATION HISTORY to understand what they're referring to, then find answer in KNOWLEDGE BASE CONTEXT
   - If information is NOT in knowledge base → Say: "I don't have this information in my knowledge base"
   - NEVER make up or hallucinate information
   - You CAN use conversation history to understand context and references

4. LANGUAGE MATCHING (CRITICAL - ABSOLUTE RULE):
   {lang_instruction}

   YOU MUST ALWAYS RESPOND IN THE EXACT SAME LANGUAGE AS THE USER'S MESSAGE.
   This is non-negotiable. Examples:
   - User writes in English → You MUST respond in English ONLY
   - User writes in Arabic (العربية) → You MUST respond in Arabic ONLY
   - User writes in French → You MUST respond in French ONLY
   - User writes in Spanish → You MUST respond in Spanish ONLY
   NEVER respond in a different language than the user's input language.

5. BE CONVERSATIONAL AND HELPFUL:
   - Remember what you discussed earlier in the conversation
   - If user refers to something mentioned before ("it", "that branch", etc.), acknowledge it
   - Answer follow-up questions naturally
   - Be concise but comprehensive
   - Be friendly and helpful

KNOWLEDGE BASE CONTEXT:
{context}
{conv_section}

EXAMPLE INTERACTIONS:

Example 1 - Self-contained question:
User: "Where is Kaso branch in Cairo?"
You: "Kaso has a branch in Cairo located in Nasr City, Abbas El Akkad Street." (using knowledge base)

Example 2 - Follow-up question using history:
User: "Where is Kaso branch in Cairo?"
You: "It's in Nasr City, Abbas El Akkad Street."
User: "What are the hours there?" (← "there" refers to Nasr City branch)
You: "The Nasr City branch is open from 10 AM to 11 PM daily." (understood reference from history + used knowledge base for answer)

Example 3 - Off-topic refusal:
User: "What's the weather today?"
You: "{refuse_message}"

Remember:
- Use BOTH knowledge base AND conversation history
- Refuse politely if question is not about Kaso B2B platform
- Be helpful, conversational, and accurate!"""
    
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from Groq
        
        Args:
            messages: Chat history
            system_prompt: System prompt with context
            
        Yields:
            Token strings as they arrive
        """
        # Build full messages list
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages
        ]
        
        try:
            stream = await self.async_client.chat.completions.create(
                model=settings.llm_model,
                messages=full_messages,
                stream=True,
                max_tokens=1024,
                temperature=0.7
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\n\n[Error: {str(e)}]"
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
    ) -> str:
        """
        Generate non-streaming response from Groq
        
        Args:
            messages: Chat history
            system_prompt: System prompt with context
            
        Returns:
            Complete response string
        """
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages
        ]
        
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=full_messages,
            max_tokens=1024,
            temperature=0.7
        )
        
        return response.choices[0].message.content


# Singleton instance
llm_service = LLMService()
