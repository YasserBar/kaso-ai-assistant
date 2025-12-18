"""
Multilingual Service
====================
Centralized service for all multilingual operations.
Handles language detection, message generation, and localization for 100+ languages.

This service enables the system to work with any language supported by the underlying
models (paraphrase-multilingual-MiniLM-L12-v2, llama-3.1-8b-instant).
"""

import logging
from typing import Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class MultilingualService:
    """
    Centralized service for multilingual operations.

    Features:
    - Language detection using langdetect (55+ languages)
    - Message generation with 3-tier caching:
      1. Hardcoded fallbacks (15+ languages) - 0ms
      2. LRU cache (100 entries) - 0.5ms
      3. LLM generation (uncommon languages) - 200-500ms, then cached
    - System prompt localization
    - RTL language detection
    """

    _instance: Optional['MultilingualService'] = None
    _message_cache: Dict[str, str] = {}
    _cache_max_size: int = 100

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize multilingual service"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info("Multilingual service initialized with support for 100+ languages")

    # ════════════════════════════════════════
    # HARDCODED FALLBACKS (15+ languages)
    # ════════════════════════════════════════

    REFUSAL_MESSAGES = {
        'ar': "عذراً، أنا مساعد خاص بمنصة كاسو B2B فقط. لا يمكنني الإجابة على أسئلة خارج نطاق كاسو.",
        'en': "Sorry, I'm a specialized assistant for Kaso B2B supply chain platform only. I cannot answer questions outside Kaso's scope.",
        'fr': "Désolé, je suis un assistant spécialisé uniquement pour la plateforme B2B Kaso. Je ne peux pas répondre aux questions hors du cadre de Kaso.",
        'de': "Entschuldigung, ich bin ein spezialisierter Assistent nur für die Kaso B2B-Plattform. Ich kann Fragen außerhalb des Kaso-Bereichs nicht beantworten.",
        'es': "Lo siento, soy un asistente especializado solo para la plataforma B2B Kaso. No puedo responder preguntas fuera del alcance de Kaso.",
        'it': "Mi dispiace, sono un assistente specializzato solo per la piattaforma B2B Kaso. Non posso rispondere a domande al di fuori dell'ambito di Kaso.",
        'pt': "Desculpe, sou um assistente especializado apenas para a plataforma B2B Kaso. Não posso responder a perguntas fora do escopo da Kaso.",
        'ru': "Извините, я специализированный помощник только для B2B-платформы Kaso. Я не могу отвечать на вопросы вне области Kaso.",
        'zh': "抱歉，我是Kaso B2B供应链平台的专业助手。我无法回答Kaso范围之外的问题。",
        'ja': "申し訳ございません、私はKaso B2Bプラットフォーム専用のアシスタントです。Kasoの範囲外の質問にはお答えできません。",
        'ko': "죄송합니다. 저는 Kaso B2B 플랫폼 전용 어시스턴트입니다. Kaso 범위 밖의 질문에는 답변할 수 없습니다.",
        'hi': "क्षमा करें, मैं केवल Kaso B2B प्लेटफॉर्म के लिए एक विशेष सहायक हूं। मैं Kaso के दायरे से बाहर के प्रश्नों का उत्तर नहीं दे सकता।",
        'tr': "Üzgünüm, sadece Kaso B2B platformu için özel bir asistanım. Kaso'nun kapsamı dışındaki sorulara cevap veremem.",
        'nl': "Sorry, ik ben een gespecialiseerde assistent alleen voor het Kaso B2B-platform. Ik kan geen vragen beantwoorden buiten het bereik van Kaso.",
        'pl': "Przepraszam, jestem specjalistycznym asystentem tylko dla platformy B2B Kaso. Nie mogę odpowiadać na pytania poza zakresem Kaso.",
    }

    LANGUAGE_INSTRUCTIONS = {
        'ar': "يجب أن ترد باللغة العربية.",
        'en': "You must respond in English.",
        'fr': "Vous devez répondre en français.",
        'de': "Sie müssen auf Deutsch antworten.",
        'es': "Debes responder en español.",
        'it': "Devi rispondere in italiano.",
        'pt': "Você deve responder em português.",
        'ru': "Вы должны отвечать на русском языке.",
        'zh': "您必须用中文回答。",
        'ja': "日本語で返答してください。",
        'ko': "한국어로 응답해야 합니다.",
        'hi': "आपको हिंदी में उत्तर देना होगा।",
        'tr': "Türkçe cevap vermelisiniz.",
        'nl': "Je moet in het Nederlands antwoorden.",
        'pl': "Musisz odpowiedzieć po polsku.",
    }

    # RTL (Right-to-Left) languages
    RTL_LANGUAGES = {'ar', 'he', 'fa', 'ur'}

    # ════════════════════════════════════════
    # CORE METHODS
    # ════════════════════════════════════════

    def detect_language(self, text: str) -> str:
        """
        Detect language of the given text.

        Uses langdetect library for automatic detection.
        Falls back to 'en' if detection fails.

        Args:
            text: Text to detect language from

        Returns:
            ISO 639-1 language code (e.g., 'ar', 'en', 'fr')
        """
        try:
            # Import langdetect here to handle cases where it's not installed
            from langdetect import detect, LangDetectException

            # Clean text
            text_clean = text.strip()

            if not text_clean:
                return 'en'  # Default fallback

            # Detect language
            detected = detect(text_clean)

            logger.debug(f"Detected language: {detected} for text: {text_clean[:50]}...")
            return detected

        except (ImportError, Exception) as e:
            logger.warning(f"Language detection failed: {e}. Falling back to 'en'")
            return 'en'

    def generate_refusal_message(
        self,
        language: str,
        use_llm: bool = True,
        context: str = "restaurant"
    ) -> str:
        """
        Generate refusal message in the specified language.

        Strategy (3-tier caching):
        1. Check hardcoded fallbacks (15+ languages) - 0ms
        2. Check LRU cache - 0.5ms
        3. Generate with LLM - 200-500ms, then cache

        Args:
            language: ISO 639-1 language code (e.g., 'ar', 'en', 'fr')
            use_llm: Whether to use LLM for uncommon languages
            context: Context type ('restaurant' or 'general')

        Returns:
            Refusal message in the specified language
        """
        # Tier 1: Hardcoded fallbacks
        if language in self.REFUSAL_MESSAGES:
            logger.debug(f"Using hardcoded refusal message for language: {language}")
            return self.REFUSAL_MESSAGES[language]

        # Tier 2: LRU cache
        cache_key = f"{language}_{context}"
        if cache_key in self._message_cache:
            logger.debug(f"Using cached refusal message for language: {language}")
            return self._message_cache[cache_key]

        # Tier 3: LLM generation (if enabled)
        if use_llm:
            generated_message = self._generate_refusal_with_llm(language, context)

            # Cache the generated message
            self._cache_message(cache_key, generated_message)

            return generated_message
        else:
            # Fallback to English if LLM generation is disabled
            logger.warning(
                f"LLM generation disabled and no fallback for language: {language}. "
                f"Using English."
            )
            return self.REFUSAL_MESSAGES['en']

    def _generate_refusal_with_llm(self, language: str, context: str = "restaurant") -> str:
        """
        Generate refusal message using LLM.

        Args:
            language: ISO 639-1 language code
            context: Context type ('restaurant' or 'general')

        Returns:
            Generated refusal message
        """
        try:
            # Import LLM service here to avoid circular imports
            from app.services.llm_service import llm_service

            # Build prompt for LLM
            prompt = f"""
Generate a polite refusal message in the language code '{language}' for the following scenario:

Scenario: A user asks a question that is NOT about Kaso B2B platform (a supply chain platform for restaurants and suppliers).

The refusal message should:
1. Apologize politely
2. Explain that you are a specialized assistant ONLY for Kaso B2B supply chain platform
3. State that you cannot answer questions outside Kaso's scope
4. Be concise (1-2 sentences)
5. Be written ENTIRELY in the target language (code: {language})

Example templates:
- English: "Sorry, I'm a specialized assistant for Kaso B2B supply chain platform only. I cannot answer questions outside Kaso's scope."
- Arabic: "عذراً، أنا مساعد خاص بمنصة كاسو B2B فقط. لا يمكنني الإجابة على أسئلة خارج نطاق كاسو."

Now generate the message in language code '{language}':
"""

            # Generate using sync LLM client
            messages = [{"role": "user", "content": prompt}]
            system_prompt = "You are a helpful assistant that generates localized messages."

            response = llm_service.generate(messages, system_prompt)

            # Clean up the response
            generated_message = response.strip()

            logger.info(
                f"Generated refusal message for language '{language}' using LLM: "
                f"{generated_message[:100]}..."
            )

            return generated_message

        except Exception as e:
            logger.error(f"Failed to generate refusal message with LLM: {e}")
            # Fallback to English
            return self.REFUSAL_MESSAGES['en']

    def generate_system_prompt_instruction(self, language: str) -> str:
        """
        Generate language instruction for system prompt.

        Args:
            language: ISO 639-1 language code (e.g., 'ar', 'en', 'fr')

        Returns:
            Language instruction string for system prompt
        """
        # Check hardcoded instructions
        if language in self.LANGUAGE_INSTRUCTIONS:
            return self.LANGUAGE_INSTRUCTIONS[language]

        # Generate generic instruction for uncommon languages
        # Use English template since LLM understands all languages
        return f"You must respond in the language with code '{language}'."

    def is_rtl_language(self, language: str) -> bool:
        """
        Check if the given language is Right-to-Left (RTL).

        Args:
            language: ISO 639-1 language code

        Returns:
            True if language is RTL, False otherwise
        """
        return language in self.RTL_LANGUAGES

    def _cache_message(self, key: str, message: str):
        """
        Cache a generated message with LRU eviction.

        Args:
            key: Cache key
            message: Message to cache
        """
        # Simple LRU cache implementation
        if len(self._message_cache) >= self._cache_max_size:
            # Remove oldest entry (first inserted)
            oldest_key = next(iter(self._message_cache))
            del self._message_cache[oldest_key]
            logger.debug(f"Evicted cache entry: {oldest_key}")

        self._message_cache[key] = message
        logger.debug(f"Cached message with key: {key}")

    def generate_company_disambiguation_refusal(
        self,
        language: str,
        detected_company: Optional[str] = None
    ) -> str:
        """
        Generate specialized refusal message for non-B2B-platform Kaso companies.

        This provides context-aware refusals that explicitly clarify we're about
        Kaso B2B supply chain platform, not other companies with the same name.

        Args:
            language: ISO 639-1 language code (e.g., 'ar', 'en', 'fr')
            detected_company: Detected company type (e.g., 'kaso_plastics', 'kaso_security')

        Returns:
            Specialized refusal message in the requested language
        """
        # Company-specific refusal templates (hardcoded for performance)
        company_refusals = {
            'ar': {
                'kaso_plastics': (
                    "عذراً، أنا مساعد خاص بمنصة Kaso B2B فقط. "
                    "يبدو أنك تسأل عن Kaso Plastics (شركة البلاستيك الأمريكية). "
                    "أنا لا أملك معلومات عن تلك الشركة."
                ),
                'kaso_security': (
                    "عذراً، أنا مساعد خاص بمنصة Kaso B2B فقط. "
                    "يبدو أنك تسأل عن Kaso Security (شركة الخزائن الآمنة الفنلندية). "
                    "أنا لا أملك معلومات عن تلك الشركة."
                ),
                'kaso_medical': (
                    "عذراً، أنا مساعد خاص بمنصة Kaso B2B فقط. "
                    "يبدو أنك تسأل عن Kaso Medical (شركة الأجهزة الطبية الصينية). "
                    "أنا لا أملك معلومات عن تلك الشركة."
                ),
                'kaso_group': (
                    "عذراً، أنا مساعد خاص بمنصة Kaso B2B فقط. "
                    "يبدو أنك تسأل عن Kaso Group (المجموعة العراقية). "
                    "أنا لا أملك معلومات عن تلك المجموعة."
                ),
                'unknown': (
                    "عذراً، أنا مساعد خاص بمنصة Kaso B2B (منصة سلسلة التوريد في الإمارات والسعودية) فقط. "
                    "يبدو أنك تسأل عن شركة أخرى تحمل اسم Kaso. "
                    "أنا لا أملك معلومات عن الشركات الأخرى."
                )
            },
            'en': {
                'kaso_plastics': (
                    "Sorry, I'm a specialized assistant for Kaso B2B supply chain platform only. "
                    "It seems you're asking about Kaso Plastics (the American plastics manufacturing company). "
                    "I don't have information about that company."
                ),
                'kaso_security': (
                    "Sorry, I'm a specialized assistant for Kaso B2B supply chain platform only. "
                    "It seems you're asking about Kaso Security (the Finnish security and safes company). "
                    "I don't have information about that company."
                ),
                'kaso_medical': (
                    "Sorry, I'm a specialized assistant for Kaso B2B supply chain platform only. "
                    "It seems you're asking about Kaso Medical (the Chinese medical devices company). "
                    "I don't have information about that company."
                ),
                'kaso_group': (
                    "Sorry, I'm a specialized assistant for Kaso B2B supply chain platform only. "
                    "It seems you're asking about Kaso Group (the Iraqi business conglomerate). "
                    "I don't have information about that group."
                ),
                'unknown': (
                    "Sorry, I'm a specialized assistant for Kaso B2B platform (supply chain platform in UAE/Saudi Arabia) only. "
                    "It seems you're asking about a different company named Kaso. "
                    "I don't have information about other Kaso companies."
                )
            },
            'fr': {
                'kaso_plastics': (
                    "Désolé, je suis un assistant spécialisé uniquement pour la plateforme B2B Kaso. "
                    "Il semble que vous posiez des questions sur Kaso Plastics (l'entreprise américaine de plastiques). "
                    "Je n'ai pas d'informations sur cette entreprise."
                ),
                'unknown': (
                    "Désolé, je suis un assistant spécialisé uniquement pour la plateforme B2B Kaso (plateforme de chaîne d'approvisionnement aux Émirats/Arabie Saoudite). "
                    "Il semble que vous posiez des questions sur une autre société nommée Kaso. "
                    "Je n'ai pas d'informations sur d'autres sociétés Kaso."
                )
            },
            'de': {
                'kaso_security': (
                    "Entschuldigung, ich bin ein spezialisierter Assistent nur für die Kaso B2B-Plattform. "
                    "Es scheint, Sie fragen nach Kaso Security (dem finnischen Sicherheitsunternehmen). "
                    "Ich habe keine Informationen über dieses Unternehmen."
                ),
                'unknown': (
                    "Entschuldigung, ich bin ein spezialisierter Assistent nur für die Kaso B2B-Plattform (Lieferkettenplattform in den VAE/Saudi-Arabien). "
                    "Es scheint, Sie fragen nach einem anderen Unternehmen namens Kaso. "
                    "Ich habe keine Informationen über andere Kaso-Unternehmen."
                )
            },
            'es': {
                'unknown': (
                    "Lo siento, soy un asistente especializado solo para la plataforma B2B Kaso (plataforma de cadena de suministro en EAU/Arabia Saudita). "
                    "Parece que preguntas sobre otra empresa llamada Kaso. "
                    "No tengo información sobre otras empresas Kaso."
                )
            }
        }

        # Try to get company-specific refusal in requested language
        if language in company_refusals:
            if detected_company and detected_company in company_refusals[language]:
                logger.info(f"Generated {language} refusal for {detected_company}")
                return company_refusals[language][detected_company]
            elif 'unknown' in company_refusals[language]:
                logger.info(f"Generated {language} generic company disambiguation refusal")
                return company_refusals[language]['unknown']

        # Fallback to English
        if detected_company and detected_company in company_refusals['en']:
            logger.info(f"Fallback to English refusal for {detected_company}")
            return company_refusals['en'][detected_company]

        logger.info("Fallback to English generic company disambiguation refusal")
        return company_refusals['en']['unknown']

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            'cache_size': len(self._message_cache),
            'cache_max_size': self._cache_max_size,
            'hardcoded_languages': len(self.REFUSAL_MESSAGES),
        }


# Singleton instance
multilingual_service = MultilingualService()
