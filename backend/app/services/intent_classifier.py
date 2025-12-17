"""
Intent Classifier Service
==========================
Multi-layer intent classification to filter off-topic queries.

This module implements a cascading approach:
1. Fast keyword-based filtering (100-500μs)
2. Embedding similarity check (1-5ms)
3. LLM-based classification for edge cases (500-2000ms)

This ensures both speed and accuracy while preventing off-topic queries
from consuming expensive LLM resources.
"""

import re
import logging
from typing import Tuple, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)


class IntentCategory(Enum):
    """Intent categories for query classification"""
    KASO_RELATED = "kaso_related"
    OFF_TOPIC = "off_topic"
    GREETING = "greeting"
    UNCLEAR = "unclear"


class IntentClassifier:
    """
    Multi-stage intent classification to filter off-topic queries.

    Stage 1: Fast keyword-based filtering (100-500μs)
    Stage 2: Embedding similarity check (1-5ms)
    Stage 3: LLM-based classification for edge cases (500-2000ms)

    This cascading approach balances accuracy with latency.
    """

    def __init__(self):
        """Initialize the intent classifier with keyword lists and patterns"""

        # Kaso-specific keywords (Arabic + English)
        self.kaso_keywords = {
            'ar': [
                'كاسو', 'كازو', 'kaso',
                'مطعم', 'طعام', 'وجبة', 'منيو', 'قائمة',
                'فرع', 'موقع', 'عنوان', 'فروع',
                'توصيل', 'طلب', 'أوردر',
                'ساندوتش', 'برجر', 'بطاطس', 'مشروب',
                'سعر', 'أسعار', 'كم سعر',
                'ساعات العمل', 'مواعيد', 'متى يفتح',
                'حجز', 'reservation', 'طلبات', 'أكل',
                'مأكولات', 'وجبات', 'عروض', 'خصم'
            ],
            'en': [
                'kaso', 'restaurant', 'food', 'meal', 'menu',
                'branch', 'location', 'address', 'branches',
                'delivery', 'order', 'ordering',
                'sandwich', 'burger', 'fries', 'drink',
                'price', 'prices', 'cost', 'how much',
                'hours', 'opening', 'timing', 'schedule',
                'reservation', 'book', 'booking',
                'foodtech', 'cuisine', 'dish', 'dishes'
            ]
        }

        # Off-topic indicators (strong signals)
        self.off_topic_keywords = {
            'ar': [
                'سياسة', 'انتخابات', 'حرب', 'رئيس', 'حكومة',
                'برمجة', 'كود', 'بايثون', 'جافا', 'برنامج',
                'رياضة', 'كرة القدم', 'مباراة', 'فريق',
                'فيلم', 'مسلسل', 'ممثل', 'سينما',
                'طقس', 'حالة الطقس', 'درجة الحرارة', 'أمطار',
                'تاريخ', 'جغرافيا', 'علوم', 'فيزياء',
                'موسيقى', 'أغنية', 'مغني'
            ],
            'en': [
                'politics', 'election', 'war', 'president', 'government',
                'programming', 'code', 'python', 'java', 'software',
                'sports', 'football', 'soccer', 'match', 'game', 'team',
                'movie', 'film', 'series', 'actor', 'cinema',
                'weather', 'temperature', 'forecast', 'rain',
                'history', 'geography', 'science', 'physics',
                'music', 'song', 'singer', 'band'
            ]
        }

        # Generic greetings (allow these)
        self.greeting_patterns = [
            r'^(hi|hello|hey|greetings)\b',
            r'^(مرحبا|السلام عليكم|أهلا|هلا|هاي)\b',
            r'^(how are you|كيف حالك|ازيك|ازيكم)\b',
            r'^(good (morning|afternoon|evening)|صباح الخير|مساء الخير)\b'
        ]

        # Pre-compute Kaso embedding centroid (lazy initialization)
        self._kaso_embedding_centroid = None

    def _initialize_embeddings(self):
        """Pre-compute representative Kaso embeddings for similarity check"""
        try:
            from app.services.embedding_service import embedding_service
            import numpy as np

            # Create representative Kaso sentences (multilingual)
            kaso_sentences = [
                "أين يقع مطعم كاسو؟",
                "ما هي قائمة طعام كاسو؟",
                "كم سعر الساندوتش في كاسو؟",
                "هل يوجد توصيل من كاسو؟",
                "Where is Kaso restaurant located?",
                "What is on the Kaso menu?",
                "How much does a burger cost at Kaso?",
                "Does Kaso deliver food?",
                "What are Kaso's opening hours?",
                "ما ساعات عمل كاسو؟"
            ]

            # Embed all sentences
            embeddings = embedding_service.embed_texts(kaso_sentences)

            # Compute centroid (average)
            self._kaso_embedding_centroid = np.mean(embeddings, axis=0)

            logger.info("Intent classifier: Kaso embedding centroid initialized")

        except Exception as e:
            logger.warning(f"Failed to initialize embeddings: {e}. Embedding similarity will be skipped.")
            self._kaso_embedding_centroid = None

    def classify(
        self,
        query: str,
        use_llm_guard: bool = True
    ) -> Tuple[IntentCategory, float, str]:
        """
        Classify query intent using multi-stage approach.

        Args:
            query: User query to classify
            use_llm_guard: Whether to use LLM for edge cases (slower but more accurate)

        Returns:
            Tuple of (category, confidence, explanation)
            - category: IntentCategory enum value
            - confidence: Float between 0-1 indicating confidence level
            - explanation: String explaining the classification decision
        """
        query_lower = query.lower().strip()

        # ============================================
        # STAGE 0: Empty/Very short queries
        # ============================================
        if len(query_lower) < 3:
            return IntentCategory.UNCLEAR, 0.5, "Query too short to classify"

        # ============================================
        # STAGE 1: Greeting detection (fast path)
        # ============================================
        for pattern in self.greeting_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return IntentCategory.GREETING, 0.95, "Greeting detected via pattern matching"

        # ============================================
        # STAGE 2: Keyword-based filtering (very fast)
        # ============================================
        kaso_score = self._keyword_score(query_lower, self.kaso_keywords)
        off_topic_score = self._keyword_score(query_lower, self.off_topic_keywords)

        # Strong signals from keywords
        if kaso_score >= 2.0:  # Multiple Kaso keywords found
            return (
                IntentCategory.KASO_RELATED,
                0.85,
                f"Strong Kaso keyword signals (score: {kaso_score:.1f})"
            )

        if off_topic_score >= 2.0:  # Multiple off-topic keywords
            return (
                IntentCategory.OFF_TOPIC,
                0.85,
                f"Strong off-topic keyword signals (score: {off_topic_score:.1f})"
            )

        # ============================================
        # STAGE 3: Embedding similarity check (medium speed)
        # ============================================
        embedding_similarity = self._embedding_similarity(query)

        if embedding_similarity is not None:
            if embedding_similarity > 0.7:  # High similarity to Kaso domain
                return (
                    IntentCategory.KASO_RELATED,
                    embedding_similarity,
                    f"High semantic similarity to Kaso domain ({embedding_similarity:.2f})"
                )

            if embedding_similarity < 0.3:  # Very low similarity
                return (
                    IntentCategory.OFF_TOPIC,
                    0.80,
                    f"Low semantic similarity to Kaso domain ({embedding_similarity:.2f})"
                )

        # ============================================
        # STAGE 4: LLM Guard for edge cases (slowest, most accurate)
        # ============================================
        if use_llm_guard and embedding_similarity is not None and 0.3 <= embedding_similarity <= 0.7:
            llm_category, llm_confidence, llm_reason = self._llm_classify(query)
            return llm_category, llm_confidence, f"LLM classification: {llm_reason}"

        # ============================================
        # DEFAULT: If unclear, allow it (better UX than false negatives)
        # ============================================
        # Bias towards allowing queries rather than blocking them
        # False negatives (allowing off-topic) are less harmful than false positives (blocking valid queries)
        return (
            IntentCategory.KASO_RELATED,
            0.6,
            "Borderline query - allowing to avoid false rejection"
        )

    def _keyword_score(self, query: str, keyword_dict: Dict[str, List[str]]) -> float:
        """
        Calculate weighted keyword match score.

        Args:
            query: Lowercased query string
            keyword_dict: Dict of language -> keywords list

        Returns:
            Float score (higher = more matches)
        """
        score = 0.0

        for lang, keywords in keyword_dict.items():
            for keyword in keywords:
                if keyword in query:
                    # Exact word boundary match gets higher score
                    if re.search(rf'\b{re.escape(keyword)}\b', query, re.IGNORECASE):
                        score += 1.5
                    else:
                        # Substring match gets lower score
                        score += 0.5

        return score

    def _embedding_similarity(self, query: str) -> float:
        """
        Calculate cosine similarity with Kaso domain centroid.

        Args:
            query: User query

        Returns:
            Cosine similarity score (0-1), or None if embeddings unavailable
        """
        try:
            # Lazy initialization of embeddings
            if self._kaso_embedding_centroid is None:
                self._initialize_embeddings()

            if self._kaso_embedding_centroid is None:
                return None  # Embeddings not available

            from app.services.embedding_service import embedding_service
            import numpy as np

            # Embed the query
            query_embedding = embedding_service.embed_text(query)

            # Cosine similarity
            dot_product = np.dot(query_embedding, self._kaso_embedding_centroid)
            norm_a = np.linalg.norm(query_embedding)
            norm_b = np.linalg.norm(self._kaso_embedding_centroid)

            similarity = dot_product / (norm_a * norm_b)

            return float(similarity)

        except Exception as e:
            logger.warning(f"Embedding similarity calculation failed: {e}")
            return None

    def _llm_classify(self, query: str) -> Tuple[IntentCategory, float, str]:
        """
        Use LLM as a final guard for edge cases.
        This is expensive but accurate for ambiguous queries.

        Args:
            query: User query

        Returns:
            Tuple of (category, confidence, explanation)
        """
        try:
            from app.services.llm_service import llm_service

            classification_prompt = f"""You are an intent classifier for Kaso restaurant chatbot.

Your ONLY task: Determine if this query is related to Kaso restaurant or not.

Kaso is a restaurant/foodtech company. Queries about Kaso include:
- Menu items, prices, ingredients, food quality
- Branch locations, addresses, how to get there
- Hours, opening times, closing times
- Ordering, delivery, reservations, bookings
- General restaurant info, history, services, contact info
- Restaurant recommendations, reviews (if about Kaso)

OFF-TOPIC queries (NOT related to Kaso):
- Other companies named "Kaso" (Kaso Plastics, Kaso Security, Kaso Medical, etc.)
- General knowledge questions (weather, sports, politics, tech, science)
- Programming, coding, technical help
- News, current events
- Entertainment (movies, music, games)
- Anything else NOT about Kaso restaurant

Query to classify: "{query}"

Respond with EXACTLY ONE WORD:
- KASO if the query is about Kaso restaurant
- OFFTOPIC if the query is NOT about Kaso restaurant
- UNCLEAR if you're uncertain

Your one-word answer:"""

            messages = [{"role": "user", "content": classification_prompt}]
            response = llm_service.generate(
                messages=messages,
                system_prompt="You are a precise intent classifier. Answer with one word only: KASO, OFFTOPIC, or UNCLEAR."
            )

            response_clean = response.strip().upper()

            if "KASO" in response_clean:
                return (
                    IntentCategory.KASO_RELATED,
                    0.90,
                    "LLM classified as Kaso-related"
                )
            elif "OFFTOPIC" in response_clean or "OFF" in response_clean:
                return (
                    IntentCategory.OFF_TOPIC,
                    0.90,
                    "LLM classified as off-topic"
                )
            else:
                return (
                    IntentCategory.UNCLEAR,
                    0.5,
                    "LLM uncertain about classification"
                )

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            # Fail safe: allow query if LLM fails (better than blocking legitimate queries)
            return (
                IntentCategory.KASO_RELATED,
                0.5,
                f"LLM classification error: {str(e)}"
            )

    def should_process(self, query: str) -> Tuple[bool, str]:
        """
        Main entry point: determine if query should be processed.

        This is the method that should be called by the chat endpoint to decide
        whether to process a query or return a polite refusal.

        Args:
            query: User query

        Returns:
            Tuple of (should_process, explanation)
            - should_process: Boolean - True if query should be processed, False if off-topic
            - explanation: String explaining the decision
        """
        category, confidence, explanation = self.classify(query)

        # Log the classification for monitoring
        logger.info(
            f"Intent classification: query='{query[:50]}...', "
            f"category={category.value}, confidence={confidence:.2f}, "
            f"reason='{explanation}'"
        )

        # Allow greetings and Kaso-related queries
        if category in [IntentCategory.KASO_RELATED, IntentCategory.GREETING]:
            return True, explanation

        # Block off-topic with high confidence
        if category == IntentCategory.OFF_TOPIC and confidence > 0.75:
            return False, explanation

        # Default: allow (better to have false negatives than false positives)
        # False positive (blocking legitimate query) creates bad UX
        # False negative (allowing off-topic) is handled by system prompt
        return True, explanation


# Singleton instance
intent_classifier = IntentClassifier()
