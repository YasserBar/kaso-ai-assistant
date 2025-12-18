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
from typing import Tuple, Dict, List, Optional
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
        # UPDATED: Added company info keywords (funding, founders, etc.)
        self.kaso_keywords = {
            'ar': [
                # Brand name
                'كاسو', 'كازو', 'kaso',
                # Suppliers & products
                'مورد', 'موردين', 'بائع',
                'منتجات', 'منتج', 'كتالوج', 'فهرس',
                # Orders & purchasing
                'طلب', 'طلبات', 'طلبية', 'شراء', 'مشتريات',
                # Inventory & logistics
                'مخزون', 'مخزن', 'سلسلة التوريد',
                'توصيل', 'توريد', 'شحن', 'لوجستيات',
                # Pricing
                'سعر', 'أسعار', 'تسعير', 'جملة',
                # Platform
                'منصة', 'سوق', 'ماركت بليس',
                # Restaurants
                'مطاعم', 'مطعم',
                # General
                'فودتك', 'كميات', 'توريدات',
                'فرع', 'موقع', 'عنوان', 'فروع',
                'عروض', 'خصم', 'أوردر',
                # Company info (NEW)
                'تمويل', 'استثمار', 'مستثمر', 'مستثمرين',
                'مؤسس', 'مؤسسين', 'فريق', 'تاريخ',
                'شركة', 'شراكة', 'عملاء'
            ],
            'en': [
                # Brand name
                'kaso',
                # Suppliers & products
                'supplier', 'suppliers', 'vendor', 'vendors',
                'products', 'product', 'catalog', 'catalogue',
                # Orders & purchasing
                'order', 'ordering', 'orders', 'purchase', 'procurement',
                # Inventory & logistics
                'inventory', 'stock', 'supply chain',
                'delivery', 'logistics', 'shipping',
                # Pricing
                'price', 'prices', 'pricing', 'cost', 'wholesale',
                # Platform
                'platform', 'b2b', 'marketplace',
                # Restaurants
                'restaurant', 'restaurants',
                # General
                'foodtech', 'bulk', 'sourcing',
                'branch', 'location', 'address', 'branches',
                'how much', 'available',
                # Company info (NEW)
                'funding', 'funded', 'raised', 'investment', 'investor', 'investors',
                'founder', 'founders', 'founded', 'team', 'history',
                'company', 'partnership', 'customers'
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
        """
        Pre-compute representative Kaso embeddings for similarity check.

        UPDATED: Now includes examples from 11 languages for full multilingual support (100+ languages).
        """
        try:
            from app.services.embedding_service import embedding_service
            import numpy as np

            # ===================================================================
            # POSITIVE EXAMPLES: Kaso B2B Platform (11 languages, 33 examples)
            # ===================================================================
            kaso_b2b_platform_sentences = [
                # Arabic (3 examples)
                "من هم الموردون المتاحون على منصة كاسو؟",
                "كيف أطلب منتجات من كاسو؟",
                "ما هي أسعار المنتجات على كاسو؟",

                # English (3 examples)
                "Who are the suppliers on Kaso platform?",
                "How do I place an order with Kaso?",
                "What products are available on Kaso?",

                # French (3 examples)
                "Qui sont les fournisseurs sur la plateforme Kaso?",
                "Comment passer une commande avec Kaso?",
                "Quels produits sont disponibles sur Kaso?",

                # German (3 examples)
                "Wer sind die Lieferanten auf der Kaso-Plattform?",
                "Wie kann ich eine Bestellung bei Kaso aufgeben?",
                "Welche Produkte sind bei Kaso verfügbar?",

                # Spanish (3 examples)
                "¿Quiénes son los proveedores en la plataforma Kaso?",
                "¿Cómo hago un pedido con Kaso?",
                "¿Qué productos están disponibles en Kaso?",

                # Chinese (3 examples)
                "Kaso平台上有哪些供应商？",
                "如何在Kaso下订单？",
                "Kaso上有哪些产品？",

                # Japanese (3 examples)
                "Kasoプラットフォームのサプライヤーは誰ですか？",
                "Kasoで注文するにはどうすればいいですか？",
                "Kasoではどんな製品が利用できますか？",

                # Korean (3 examples)
                "Kaso 플랫폼에는 어떤 공급업체가 있나요?",
                "Kaso에서 주문하려면 어떻게 해야 하나요?",
                "Kaso에서 어떤 제품을 이용할 수 있나요?",

                # Hindi (3 examples)
                "Kaso प्लेटफॉर्म पर कौन से आपूर्तिकर्ता हैं?",
                "मैं Kaso से उत्पाद कैसे ऑर्डर करूं?",
                "Kaso पर कौन से उत्पाद उपलब्ध हैं?",

                # Turkish (3 examples)
                "Kaso platformunda hangi tedarikçiler var?",
                "Kaso'dan nasıl sipariş veririm?",
                "Kaso'da hangi ürünler mevcut?",

                # Russian (3 examples)
                "Какие поставщики есть на платформе Kaso?",
                "Как разместить заказ через Kaso?",
                "Какие продукты доступны на Kaso?",
            ]

            # ===================================================================
            # NEGATIVE EXAMPLES: Other Kaso Companies (40 examples)
            # Critical for company disambiguation!
            # ===================================================================
            non_restaurant_kaso_sentences = [
                # Kaso Plastics (10 examples - multilingual)
                "Does Kaso Plastics do injection molding?",
                "Where is Kaso Plastics manufacturing facility in Vancouver?",
                "ما هي خدمات Kaso Plastics في البلاستيك؟",
                "Kaso Plastics contract manufacturing services",
                "Kaso plastic injection company Canada",
                "How much does Kaso Plastics charge for tooling?",
                "Kaso Plastics Burlington factory address",
                "Custom plastic molding by Kaso Plastics",
                "Kaso Plastics OEM manufacturing capabilities",
                "كم تكلفة قوالب البلاستيك من Kaso Plastics؟",

                # Kaso Security (10 examples - multilingual)
                "How much does a Kaso safe cost?",
                "Where to buy Kaso security vault in Helsinki?",
                "ما هو سعر خزنة Kaso الآمنة؟",
                "Kaso fireproof safe specifications Finland",
                "Kaso Security Solutions products catalog",
                "Are Kaso safes burglar resistant?",
                "Kaso vault installation services",
                "خزائن Kaso الفنلندية للحماية",
                "Kaso safe dealer near me",
                "Kaso Security fireproof rating",

                # Kaso Medical (10 examples - multilingual)
                "Kaso Medical dental devices catalog",
                "Kaso Medical Technology China contact information",
                "أجهزة Kaso الطبية للأسنان في الصين",
                "Kaso medical equipment OEM services",
                "Kaso Medical Hong Kong address",
                "Dental instruments by Kaso Medical",
                "Kaso Medical Technology product line",
                "معدات Kaso الطبية في هونغ كونغ",
                "Kaso Medical distributor in Middle East",
                "Kaso dental device specifications",

                # Kaso Group (10 examples - multilingual)
                "Kaso Group construction projects in Iraq",
                "Kaso General Trading Baghdad office",
                "مشاريع مجموعة Kaso في بغداد",
                "Kaso Group oil services division",
                "What companies are part of Kaso Group?",
                "Kaso Group Iraq contracting services",
                "مجموعة Kaso للتجارة العامة",
                "Kaso Group real estate development",
                "شركات مجموعة Kaso في العراق",
                "Kaso Group business conglomerate Iraq",
            ]

            # Check if negative embeddings are enabled
            from app.config import settings
            use_negative_embeddings = getattr(settings, 'company_use_negative_embeddings', True)

            # Embed positive examples (B2B platform)
            positive_embeddings = embedding_service.embed_texts(kaso_b2b_platform_sentences)
            self._kaso_b2b_platform_centroid = np.mean(positive_embeddings, axis=0)

            if use_negative_embeddings:
                # Embed negative examples (other Kaso companies)
                negative_embeddings = embedding_service.embed_texts(non_restaurant_kaso_sentences)
                self._non_restaurant_kaso_centroid = np.mean(negative_embeddings, axis=0)

                logger.info(
                    f"Intent classifier: Initialized with DUAL centroids - "
                    f"{len(kaso_b2b_platform_sentences)} B2B platform examples + "
                    f"{len(non_restaurant_kaso_sentences)} non-restaurant examples"
                )
            else:
                # Fallback to single centroid (backward compatibility)
                self._non_restaurant_kaso_centroid = None
                self._kaso_embedding_centroid = self._kaso_b2b_platform_centroid  # For backward compatibility

                logger.info(
                    f"Intent classifier: Kaso B2B platform centroid initialized "
                    f"from {len(kaso_b2b_platform_sentences)} examples in 11 languages"
                )

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
        # STAGE 0.5: "KASO" MENTIONED → ALLOW (MULTILINGUAL FIX)
        # ============================================
        # "Kaso" is a brand name that can be written in different scripts.
        # If user mentions "Kaso" in ANY script, they're asking about Kaso.
        # The system prompt will handle disambiguation between different Kaso companies.
        kaso_variants = [
            # Latin script (most common - used by most languages)
            'kaso',
            # Arabic script
            'كاسو', 'كازو',
            # Cyrillic (Russian, Ukrainian, etc.)
            'касо',
            # Japanese (Katakana - most common for foreign brands)
            'カソ',
            # Chinese (phonetic transliteration)
            '卡索', '卡苏',
            # Korean (Hangul)
            '카소',
            # Hindi/Devanagari
            'कासो',
            # Greek
            'κάσο', 'κασο',
            # Thai
            'คาโซ',
            # Hebrew
            'קאסו',
        ]

        if any(variant in query_lower or variant in query for variant in kaso_variants):
            return (
                IntentCategory.KASO_RELATED,
                0.90,
                "Query mentions 'Kaso' brand name - allowing for all languages"
            )

        # ============================================
        # STAGE 1: Greeting detection (fast path)
        # ============================================
        for pattern in self.greeting_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return IntentCategory.GREETING, 0.95, "Greeting detected via pattern matching"

        # ============================================
        # STAGE 2: Keyword-based filtering (very fast)
        # OPTIONAL: Disabled by default for full multilingual support
        # ============================================
        try:
            from app.config import settings
            use_keywords = getattr(settings, 'intent_use_keywords', False)
        except:
            use_keywords = False  # Default: disabled for multilingual

        if use_keywords:
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
        # STAGE 3: Embedding similarity check with company disambiguation (medium speed)
        # UPDATED: Now uses dual centroids for better company separation
        # ============================================
        embedding_similarity, interpretation = self._embedding_similarity(query)

        if interpretation is not None and interpretation != "legacy_mode":
            # Using new dual centroid system
            if interpretation == "strongly_restaurant":
                return (
                    IntentCategory.KASO_RELATED,
                    0.85,
                    "High similarity to Kaso restaurant (dual centroid analysis)"
                )

            elif interpretation == "strongly_non_restaurant":
                return (
                    IntentCategory.OFF_TOPIC,
                    0.85,
                    "High similarity to non-restaurant Kaso companies (dual centroid)"
                )

            # interpretation == "ambiguous" - proceed to LLM guard

        elif interpretation == "legacy_mode" and embedding_similarity is not None:
            # Fallback to single centroid logic (backward compatibility)
            if embedding_similarity > 0.7:
                return (
                    IntentCategory.KASO_RELATED,
                    embedding_similarity,
                    f"High semantic similarity to Kaso ({embedding_similarity:.2f})"
                )

            if embedding_similarity < 0.3:
                return (
                    IntentCategory.OFF_TOPIC,
                    0.80,
                    f"Low semantic similarity to Kaso ({embedding_similarity:.2f})"
                )

        # ============================================
        # STAGE 4: LLM Guard for ambiguous cases (slowest, most accurate)
        # UPDATED: Now called for ambiguous dual-centroid results
        # ============================================
        if use_llm_guard and (interpretation == "ambiguous" or
                             (embedding_similarity is not None and 0.3 <= embedding_similarity <= 0.7)):
            llm_category, llm_confidence, llm_reason = self._llm_classify(query)
            return llm_category, llm_confidence, f"LLM classification: {llm_reason}"

        # ============================================
        # DEFAULT: CHANGED - Reject unclear queries for safety
        # CRITICAL CHANGE: Prevent confusion with other Kaso companies
        # ============================================
        # NEW POLICY: If we're uncertain whether it's about the restaurant or another
        # Kaso company, it's safer to reject and clarify than to accept and give wrong info
        return (
            IntentCategory.OFF_TOPIC,
            0.6,
            "Ambiguous query - rejecting to avoid company confusion (may be about non-restaurant Kaso company)"
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

    def _embedding_similarity(self, query: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Calculate semantic similarity with dual centroids for company disambiguation.

        UPDATED: Now uses TWO centroids:
        - Restaurant centroid (positive examples)
        - Non-restaurant Kaso companies centroid (negative examples)

        Returns relative similarity score and interpretation.

        Args:
            query: User query

        Returns:
            Tuple of (similarity_score, interpretation)
            - similarity_score: 0-1 (higher = more restaurant-like)
            - interpretation: 'strongly_restaurant', 'strongly_non_restaurant', 'ambiguous', or None
        """
        try:
            # Lazy initialization of embeddings
            if not hasattr(self, '_kaso_b2b_platform_centroid') or self._kaso_b2b_platform_centroid is None:
                self._initialize_embeddings()

            if not hasattr(self, '_kaso_b2b_platform_centroid') or self._kaso_b2b_platform_centroid is None:
                return (None, None)  # Embeddings not available

            from app.services.embedding_service import embedding_service
            import numpy as np

            # Embed the query
            query_embedding = embedding_service.embed_text(query)

            # Cosine similarity to B2B platform centroid
            dot_b2b_platform = np.dot(query_embedding, self._kaso_b2b_platform_centroid)
            norm_query = np.linalg.norm(query_embedding)
            norm_b2b_platform = np.linalg.norm(self._kaso_b2b_platform_centroid)
            similarity_b2b_platform = dot_b2b_platform / (norm_query * norm_b2b_platform)

            # If negative embeddings are enabled, use dual centroid approach
            if hasattr(self, '_non_restaurant_kaso_centroid') and self._non_restaurant_kaso_centroid is not None:
                # Cosine similarity to non-restaurant centroid
                dot_non_restaurant = np.dot(query_embedding, self._non_restaurant_kaso_centroid)
                norm_non_restaurant = np.linalg.norm(self._non_restaurant_kaso_centroid)
                similarity_non_restaurant = dot_non_restaurant / (norm_query * norm_non_restaurant)

                # Relative score: positive = B2B platform, negative = non-B2B-platform
                # This creates better separation than absolute similarity
                relative_score = similarity_b2b_platform - similarity_non_restaurant

                logger.debug(
                    f"Embedding similarity: B2B_platform={similarity_b2b_platform:.3f}, "
                    f"non-restaurant={similarity_non_restaurant:.3f}, "
                    f"relative={relative_score:.3f}"
                )

                # Interpret the relative score
                if relative_score > 0.2:  # Clearly more B2B platform-like
                    return (0.85, "strongly_b2b_platform")
                elif relative_score < -0.2:  # Clearly more non-B2B-platform
                    return (0.15, "strongly_non_b2b_platform")
                else:  # Ambiguous - needs LLM guard
                    return (0.5, "ambiguous")

            else:
                # Fallback to single centroid (backward compatibility)
                logger.debug(f"Single centroid similarity: {similarity_b2b_platform:.3f}")
                return (float(similarity_b2b_platform), "legacy_mode")

        except Exception as e:
            logger.warning(f"Embedding similarity calculation failed: {e}")
            return (None, None)

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

            # UPDATED: Enhanced prompt with explicit company disambiguation
            classification_prompt = f"""You are an intent classifier for Kaso B2B PLATFORM chatbot.

CRITICAL: There are MULTIPLE companies worldwide named "Kaso". You MUST distinguish between them.

✅ KASO B2B PLATFORM (what we support):
- Kaso - B2B supply chain platform connecting suppliers with restaurants
- Locations: UAE and Saudi Arabia
- Founded: 2021
- Topics ALLOWED (classify as KASO_B2B_PLATFORM):
  * Platform features: suppliers, products, orders, inventory, pricing, procurement, supply chain
  * Company info: funding, investors, founders, team, history, locations, branches, offices
  * Business questions: how to use, pricing, partnerships, customers, restaurants
  * Any question that mentions "Kaso" in context of food/restaurant/B2B platform

❌ OTHER KASO COMPANIES (NOT supported - MUST classify as OFFTOPIC):
1. Kaso Plastics - American plastics manufacturing (Vancouver, Canada, injection molding)
2. Kaso Security Solutions - Finnish security company (Helsinki, Finland, safes/vaults)
3. Kaso Medical Technology - Chinese medical devices (Hong Kong, dental equipment)
4. Kaso Group - Iraqi business conglomerate (Baghdad, Iraq, construction/oil)

❌ GENERAL OFF-TOPIC (also OFFTOPIC):
- Weather, politics, sports, entertainment, tech, programming, science, news

Query to classify: "{query}"

Respond with EXACTLY ONE WORD:
- KASO_B2B_PLATFORM - if asking about the B2B supply chain platform
- KASO_PLASTICS - if asking about the plastics company
- KASO_SECURITY - if asking about security/safes
- KASO_MEDICAL - if asking about medical devices
- KASO_GROUP - if asking about the Iraqi conglomerate
- OTHER_KASO - if asking about a different Kaso company
- OFFTOPIC - if not about any Kaso company at all
- UNCLEAR - if genuinely uncertain

Your one-word answer:"""

            messages = [{"role": "user", "content": classification_prompt}]
            response = llm_service.generate(
                messages=messages,
                system_prompt="You are a precise intent classifier. Answer with ONE word only."
            )

            response_clean = response.strip().upper()

            # Check for KASO B2B PLATFORM first (what we support)
            if "KASO_B2B_PLATFORM" in response_clean or "KASO_RESTAURANT" in response_clean:
                return (
                    IntentCategory.KASO_RELATED,
                    0.95,
                    "LLM: Kaso restaurant"
                )
            # Check for OTHER Kaso companies (NOT supported - must reject)
            elif any(x in response_clean for x in [
                "KASO_PLASTICS", "KASO_SECURITY", "KASO_MEDICAL",
                "KASO_GROUP", "OTHER_KASO"
            ]):
                detected = response_clean.strip()
                return (
                    IntentCategory.OFF_TOPIC,
                    0.95,
                    f"LLM: Other Kaso company - {detected}"
                )
            # Check for general off-topic
            elif "OFFTOPIC" in response_clean or "OFF" in response_clean:
                return (
                    IntentCategory.OFF_TOPIC,
                    0.90,
                    "LLM: Completely off-topic"
                )
            # Uncertain
            else:
                return (
                    IntentCategory.UNCLEAR,
                    0.5,
                    "LLM: Uncertain"
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
