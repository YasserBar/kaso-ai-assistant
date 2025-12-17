"""
LLM Service
===========
Groq API integration with streaming support
"""

import json
from typing import AsyncGenerator, List, Dict, Any, Optional
from groq import Groq, AsyncGroq

from app.config import settings


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
    
    def build_system_prompt(self, context: str, language: str = "auto") -> str:
        """
        Build system prompt with context and language instructions
        
        Args:
            context: Retrieved context from knowledge base
            language: Target response language ('ar', 'en', or 'auto')
        """
        # Language instruction: choose explicit Arabic/English or auto-detect
        lang_instruction = ""
        if language == "ar":
            # Reply in Arabic when explicitly requested
            lang_instruction = "يجب أن ترد باللغة العربية."
        elif language == "en":
            # Reply in English when explicitly requested
            lang_instruction = "You must respond in English."
        else:
            # Auto mode: mirror the user's input language
            lang_instruction = "Respond in the SAME LANGUAGE as the user's question. If they ask in Arabic, respond in Arabic. If in English, respond in English."
        
        return f"""You are a helpful AI assistant for Kaso.

IMPORTANT RULES:
1. Answer ONLY based on the provided context below.
2. If the answer is NOT in the context, say "I don't have this information in my knowledge base."
3. {lang_instruction}
4. Be concise but comprehensive.
5. If asked about other companies named "Kaso" (like Kaso Plastics, Kaso Security, Kaso Group, Kaso Medical), clarify that you only have information about Kaso Foodtech.

CONTEXT:
{context}

Remember: Only answer based on the context above. Do not make up information."""
    
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
