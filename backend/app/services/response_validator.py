"""
Response Validator Service
===========================
Validate LLM responses to catch hallucinations or off-topic answers.

This is a safety net that runs after response generation to detect:
1. Off-topic content (model went off-topic despite system prompt)
2. Hallucinations (information not present in the provided context)
3. Quality issues (too short, malformed, etc.)

This provides an additional layer of defense against the model not
following instructions properly.
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class ResponseValidator:
    """
    Validate LLM responses to catch hallucinations or off-topic answers.
    This is a safety net after generation.
    """

    def __init__(self):
        """Initialize validator with detection patterns"""

        # Patterns indicating the model went off-topic (strong signals)
        # UPDATED: Multilingual support for 10+ languages
        self.off_topic_patterns = {
            'ar': [
                r'(الرئيس|الحكومة|الانتخابات|السياسة)',  # Politics
                r'(البرمجة|الكود|بايثون|جافا|برمجة)',  # Programming
                r'(الطقس|درجة الحرارة|الأمطار|حالة الجو)',  # Weather
                r'(المباراة|الفريق|الدوري|كرة القدم)',  # Sports
                r'(الفيلم|المسلسل|الممثل|السينما)',  # Entertainment
            ],
            'en': [
                r'\b(president|government|election|politics|political)\b',
                r'\b(programming|code|python|java|software|algorithm)\b',
                r'\b(weather|temperature|forecast|rain|climate)\b',
                r'\b(match|team|league|game|tournament|player)\b',
                r'\b(movie|film|series|actor|cinema|tv show)\b',
            ],
            'fr': [  # French
                r'\b(président|gouvernement|élection|politique)\b',
                r'\b(programmation|code|python|java|logiciel)\b',
                r'\b(météo|température|prévision|pluie|climat)\b',
                r'\b(match|équipe|ligue|jeu|tournoi|joueur)\b',
                r'\b(film|série|acteur|cinéma)\b',
            ],
            'de': [  # German
                r'\b(präsident|regierung|wahl|politik)\b',
                r'\b(programmierung|code|python|java|software)\b',
                r'\b(wetter|temperatur|vorhersage|regen|klima)\b',
                r'\b(spiel|mannschaft|liga|turnier|spieler)\b',
                r'\b(film|serie|schauspieler|kino)\b',
            ],
            'es': [  # Spanish
                r'\b(presidente|gobierno|elección|política)\b',
                r'\b(programación|código|python|java|software)\b',
                r'\b(clima|temperatura|pronóstico|lluvia)\b',
                r'\b(partido|equipo|liga|juego|torneo|jugador)\b',
                r'\b(película|serie|actor|cine)\b',
            ],
            'it': [  # Italian
                r'\b(presidente|governo|elezione|politica)\b',
                r'\b(programmazione|codice|python|java|software)\b',
                r'\b(tempo|temperatura|previsione|pioggia|clima)\b',
                r'\b(partita|squadra|lega|gioco|torneo|giocatore)\b',
                r'\b(film|serie|attore|cinema)\b',
            ],
            'pt': [  # Portuguese
                r'\b(presidente|governo|eleição|política)\b',
                r'\b(programação|código|python|java|software)\b',
                r'\b(clima|temperatura|previsão|chuva)\b',
                r'\b(jogo|equipe|liga|torneio|jogador)\b',
                r'\b(filme|série|ator|cinema)\b',
            ],
            'ru': [  # Russian
                r'\b(президент|правительство|выборы|политика)\b',
                r'\b(программирование|код|python|java|программа)\b',
                r'\b(погода|температура|прогноз|дождь|климат)\b',
                r'\b(матч|команда|лига|игра|турнир|игрок)\b',
                r'\b(фильм|сериал|актёр|кино)\b',
            ],
            'zh': [  # Chinese
                r'(总统|政府|选举|政治)',
                r'(编程|代码|程序|软件)',
                r'(天气|温度|预报|雨|气候)',
                r'(比赛|球队|联赛|游戏|锦标赛|球员)',
                r'(电影|电视剧|演员|电影院)',
            ],
            'ja': [  # Japanese
                r'(大統領|政府|選挙|政治)',
                r'(プログラミング|コード|ソフトウェア)',
                r'(天気|温度|予報|雨|気候)',
                r'(試合|チーム|リーグ|ゲーム|トーナメント|選手)',
                r'(映画|シリーズ|俳優|映画館)',
            ],
            'ko': [  # Korean
                r'(대통령|정부|선거|정치)',
                r'(프로그래밍|코드|소프트웨어)',
                r'(날씨|온도|예보|비|기후)',
                r'(경기|팀|리그|게임|토너먼트|선수)',
                r'(영화|시리즈|배우|영화관)',
            ],
        }

        # Patterns indicating a proper refusal (good response)
        # UPDATED: Multilingual support for 10+ languages
        self.refusal_patterns = [
            # Apology (sorry, etc.)
            r'(sorry|عذراً|آسف|أعتذر|désolé|entschuldigung|lo siento|mi dispiace|desculpe|извините|抱歉|申し訳|죄송)',
            # Cannot/Can't
            r'(cannot|can\'t|لا يمكنني|لا أستطيع|ne peux pas|kann nicht|no puedo|non posso|não posso|не могу|无法|できません|수 없)',
            # Only/Specialized for Kaso
            r'(only.*kaso|فقط.*كاسو|مخصص.*كاسو|uniquement.*kaso|nur.*kaso|solo.*kaso|只.*kaso)',
            # Outside scope
            r'(outside.*scope|خارج.*نطاق|خارج.*مجال|hors.*cadre|außerhalb.*bereich|fuera.*alcance|범위.*밖)',
            # Specialized assistant
            r'(specialized.*assistant|مساعد.*متخصص|مساعد.*خاص|assistant.*spécialisé|spezialisiert.*assistent|asistente.*especializado|전용.*어시스턴트)',
        ]

        logger.info("Response validator initialized")

    def validate(
        self,
        query: str,
        response: str,
        context: str
    ) -> Tuple[bool, str]:
        """
        Validate response quality and topicality.

        Args:
            query: Original user query
            response: Generated response from LLM
            context: RAG context that was provided to LLM

        Returns:
            Tuple of (is_valid, explanation)
            - is_valid: Boolean - True if response passes validation
            - explanation: String explaining the validation result
        """
        # ============================================
        # CHECK 1: Empty or too short response
        # ============================================
        if not response or len(response.strip()) < 10:
            logger.warning(f"Validation failed: response too short ({len(response)} chars)")
            return False, "Response too short or empty"

        # ============================================
        # CHECK 2: Is response a proper refusal?
        # ============================================
        # If it's a refusal, that's valid (model refused off-topic query)
        if self._is_refusal(response):
            logger.debug("Validation passed: response is a proper refusal")
            return True, "Valid refusal response"

        # ============================================
        # CHECK 3: Does response contain off-topic content?
        # ============================================
        if self._contains_off_topic(response):
            logger.warning(f"Validation failed: response contains off-topic content")
            return False, "Response contains off-topic content (politics, weather, sports, etc.)"

        # ============================================
        # CHECK 4: Hallucination detection (heuristic)
        # ============================================
        hallucination_risk = self._check_hallucination(response, context)

        if hallucination_risk > 0.8:
            logger.warning(
                f"Validation warning: high hallucination risk detected ({hallucination_risk:.2f})"
            )
            return False, f"High hallucination risk detected (score: {hallucination_risk:.2f})"

        # ============================================
        # CHECK 5: Response coherence
        # ============================================
        if not self._is_coherent(response):
            logger.warning("Validation failed: response appears incoherent")
            return False, "Response appears incoherent or malformed"

        # ============================================
        # ALL CHECKS PASSED
        # ============================================
        logger.debug("Validation passed: response appears valid")
        return True, "Response passed all validation checks"

    def _is_refusal(self, response: str) -> bool:
        """
        Check if response is a valid refusal (model refused to answer).

        A refusal is valid if the model politely declined to answer an
        off-topic question.

        Args:
            response: Response text

        Returns:
            True if response is a refusal, False otherwise
        """
        response_lower = response.lower()

        # Count refusal indicators
        matches = sum(
            1 for pattern in self.refusal_patterns
            if re.search(pattern, response_lower, re.IGNORECASE)
        )

        # Consider it a refusal if has at least 2 refusal indicators
        is_refusal = matches >= 2

        return is_refusal

    def _contains_off_topic(self, response: str) -> bool:
        """
        Check if response discusses off-topic subjects.

        Args:
            response: Response text

        Returns:
            True if off-topic content detected, False otherwise
        """
        for lang, patterns in self.off_topic_patterns.items():
            for pattern in patterns:
                if re.search(pattern, response, re.IGNORECASE):
                    logger.debug(f"Off-topic pattern matched: {pattern}")
                    return True

        return False

    def _check_hallucination(self, response: str, context: str) -> float:
        """
        Estimate hallucination risk by checking if response content exists in context.

        This is a heuristic-based check, not perfect but catches obvious hallucinations.

        Args:
            response: Response text
            context: RAG context that was provided

        Returns:
            Hallucination risk score 0.0-1.0 (higher = more risky)
        """
        # Strategy: Check if specific numbers/facts in response are in context
        # Numbers are strong hallucination indicators

        # Extract numbers from response
        response_numbers = set(re.findall(r'\b\d+(?:[.,]\d+)?\b', response))

        # Extract numbers from context
        context_numbers = set(re.findall(r'\b\d+(?:[.,]\d+)?\b', context))

        if response_numbers:
            # How many numbers in response are NOT in context?
            novel_numbers = response_numbers - context_numbers

            if novel_numbers:
                hallucination_score = len(novel_numbers) / len(response_numbers)

                logger.debug(
                    f"Hallucination check: "
                    f"response_numbers={response_numbers}, "
                    f"context_numbers={context_numbers}, "
                    f"novel={novel_numbers}, "
                    f"score={hallucination_score:.2f}"
                )

                return hallucination_score

        # No numbers found, can't assess via this method
        return 0.0

    def _is_coherent(self, response: str) -> bool:
        """
        Check if response appears coherent (not gibberish or malformed).

        This is a basic sanity check.

        Args:
            response: Response text

        Returns:
            True if response appears coherent, False otherwise
        """
        # Check 1: Not too many repeated words (sign of model looping)
        words = response.lower().split()
        if len(words) > 10:
            unique_words = len(set(words))
            repetition_ratio = unique_words / len(words)

            if repetition_ratio < 0.3:
                # Less than 30% unique words = too repetitive
                logger.debug(f"Coherence check failed: too repetitive (ratio={repetition_ratio:.2f})")
                return False

        # Check 2: Has some sentence structure (contains periods or question marks)
        # (unless it's a very short response)
        if len(response) > 50:
            sentence_markers = response.count('.') + response.count('?') + response.count('!') + response.count('。')
            if sentence_markers == 0:
                logger.debug("Coherence check failed: no sentence markers in long response")
                return False

        # Check 3: Not just special characters
        alphanumeric = sum(c.isalnum() for c in response)
        if alphanumeric < len(response) * 0.5:
            # Less than 50% alphanumeric = suspicious
            logger.debug("Coherence check failed: too many special characters")
            return False

        return True


# Singleton instance
response_validator = ResponseValidator()
