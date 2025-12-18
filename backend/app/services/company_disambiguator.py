"""
Company Disambiguator Service
==============================
Disambiguate between Kaso B2B platform and other companies named "Kaso".

CRITICAL: There are multiple companies worldwide named "Kaso":
- Kaso (B2B supply chain platform in UAE/Saudi Arabia) - WHAT WE SUPPORT
- Kaso Plastics (American plastics manufacturing)
- Kaso Security (Finnish security/safes company)
- Kaso Medical (Chinese medical devices)
- Kaso Group (Iraqi conglomerate)

This service prevents confusion by detecting queries about non-B2B-platform Kaso companies
BEFORE they reach the LLM, saving cost and preventing incorrect responses.
"""

import re
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DisambiguationResult:
    """
    Result of company disambiguation analysis.

    Attributes:
        is_kaso_b2b_platform: True if query is about Kaso B2B platform, False if about other Kaso company, None if uncertain
        confidence: Confidence score 0.0-1.0
        detected_company: Detected company key (e.g., 'kaso_plastics') or None
        reason: Explanation of the decision
    """
    is_kaso_b2b_platform: Optional[bool]
    confidence: float
    detected_company: Optional[str]
    reason: str


class CompanyDisambiguator:
    """
    Service to disambiguate between Kaso restaurant and other Kaso companies.

    Strategy:
    1. Check for non-restaurant company keywords (2+ matches = reject)
    2. Check for restaurant indicators (2+ matches = accept)
    3. If unclear, return uncertain result for further processing
    """

    def __init__(self):
        """Initialize company disambiguator with company database and patterns"""

        # Database of known non-restaurant Kaso companies
        # Each company has keywords in multiple languages and a confidence boost
        self.known_kaso_companies = {
            'kaso_plastics': {
                'keywords': [
                    # English
                    'plastic', 'plastics', 'injection', 'molding', 'mold', 'mould',
                    'manufacturing', 'manufacture', 'factory', 'vancouver', 'burlington',
                    'canada', 'contract manufacturing', 'custom molding',
                    # Arabic
                    'بلاستيك', 'حقن', 'قولبة', 'تصنيع', 'مصنع', 'كندا'
                ],
                'domain': 'manufacturing',
                'confidence_boost': 0.9,
                'description': 'American plastics manufacturing company'
            },
            'kaso_security': {
                'keywords': [
                    # English
                    'safe', 'safes', 'vault', 'vaults', 'security', 'fireproof',
                    'lock', 'locks', 'helsinki', 'finland', 'finnish',
                    'burglar', 'protection', 'secure storage',
                    # Arabic
                    'خزنة', 'خزائن', 'أمن', 'أمان', 'حماية', 'قفل', 'فنلندا',
                    # French
                    'coffre-fort', 'sécurité'
                ],
                'domain': 'security',
                'confidence_boost': 0.9,
                'description': 'Finnish security and safes company'
            },
            'kaso_medical': {
                'keywords': [
                    # English
                    'medical', 'dental', 'dentist', 'device', 'devices', 'equipment',
                    'hongkong', 'hong kong', 'china', 'chinese', 'healthcare',
                    'hospital', 'clinic', 'oem', 'surgical',
                    # Arabic
                    'طبي', 'طبية', 'أسنان', 'جهاز', 'أجهزة', 'معدات', 'صيني',
                    'مستشفى', 'عيادة', 'هونغ كونغ'
                ],
                'domain': 'medical',
                'confidence_boost': 0.9,
                'description': 'Chinese medical devices company'
            },
            'kaso_group': {
                'keywords': [
                    # English
                    'group', 'conglomerate', 'construction', 'building', 'oil',
                    'oil services', 'trading', 'baghdad', 'iraq', 'iraqi',
                    'general trading', 'contracting',
                    # Arabic
                    'مجموعة', 'بناء', 'إنشاءات', 'عقارات', 'نفط', 'بغداد',
                    'عراق', 'عراقي', 'تجارة', 'مقاولات'
                ],
                'domain': 'conglomerate',
                'confidence_boost': 0.85,
                'description': 'Iraqi business conglomerate'
            }
        }

        # Strong B2B platform indicators (multiple languages)
        # If 2+ of these are present, it's likely about the B2B platform
        self.b2b_platform_indicators = {
            'ar': [
                'مورد', 'موردين', 'منتجات', 'طلبات', 'مشتريات', 'مخزون',
                'توريد', 'سلسلة التوريد', 'جملة', 'كميات', 'كتالوج',
                'منصة', 'مطاعم', 'موردي المطاعم', 'توصيل', 'أسعار',
                'شراء', 'بائع', 'تجهيز', 'لوجستيات', 'فهرس'
            ],
            'en': [
                'supplier', 'suppliers', 'vendor', 'vendors', 'products',
                'order', 'orders', 'procurement', 'supply chain', 'inventory',
                'stock', 'platform', 'b2b', 'marketplace', 'wholesale', 'bulk',
                'catalog', 'catalogue', 'sourcing', 'purchase', 'restaurants',
                'delivery', 'logistics', 'pricing', 'price', 'prices'
            ],
            'fr': [
                'fournisseur', 'fournisseurs', 'produits', 'commande',
                'approvisionnement', 'chaîne d\'approvisionnement', 'inventaire',
                'plateforme', 'b2b', 'marché', 'gros', 'catalogue',
                'restaurants', 'livraison', 'prix'
            ],
            'de': [
                'lieferant', 'lieferanten', 'produkte', 'bestellung',
                'beschaffung', 'lieferkette', 'bestand', 'plattform',
                'b2b', 'marktplatz', 'großhandel', 'katalog',
                'restaurants', 'lieferung', 'preise'
            ],
            'es': [
                'proveedor', 'proveedores', 'productos', 'pedido',
                'adquisición', 'cadena de suministro', 'inventario',
                'plataforma', 'b2b', 'mercado', 'mayorista', 'catálogo',
                'restaurantes', 'entrega', 'precios'
            ]
        }

        logger.info("Company disambiguator initialized with 4 known non-restaurant Kaso companies")

    def analyze_query(self, query: str) -> DisambiguationResult:
        """
        Analyze query to determine if it's about Kaso restaurant or another Kaso company.

        Algorithm:
        1. Check for non-restaurant company keywords (2+ matches = high confidence rejection)
        2. Check for restaurant indicators (2+ matches = high confidence acceptance)
        3. If unclear, return uncertain result for next layer to handle

        Args:
            query: User query string

        Returns:
            DisambiguationResult with analysis result
        """
        query_lower = query.lower()

        # ============================================
        # STEP 1: Check for non-restaurant Kaso companies
        # ============================================
        for company_key, company_data in self.known_kaso_companies.items():
            keyword_matches = []

            for keyword in company_data['keywords']:
                # Use word boundaries for better matching
                pattern = rf'\b{re.escape(keyword)}\b'
                if re.search(pattern, query_lower, re.IGNORECASE):
                    keyword_matches.append(keyword)

            # If 2+ keywords match, high confidence it's about this non-restaurant company
            if len(keyword_matches) >= 2:
                logger.info(
                    f"Detected {company_key}: matched {len(keyword_matches)} keywords - {keyword_matches[:3]}"
                )
                return DisambiguationResult(
                    is_kaso_b2b_platform=False,
                    confidence=company_data['confidence_boost'],
                    detected_company=company_key,
                    reason=f"Detected {company_key} - matched keywords: {', '.join(keyword_matches[:5])}"
                )

            # If 1 keyword matches (weak signal), continue checking but note it
            elif len(keyword_matches) == 1:
                logger.debug(f"Weak signal for {company_key}: {keyword_matches[0]}")

        # ============================================
        # STEP 2: Check for B2B platform indicators
        # ============================================
        b2b_platform_score = self._calculate_b2b_platform_score(query_lower)

        if b2b_platform_score >= 2.0:  # Strong B2B platform signal
            logger.info(f"Strong B2B platform indicators (score: {b2b_platform_score:.1f})")
            return DisambiguationResult(
                is_kaso_b2b_platform=True,
                confidence=0.90,
                detected_company=None,
                reason=f"Strong B2B platform indicators detected (score: {b2b_platform_score:.1f})"
            )

        elif b2b_platform_score < 0.5:  # Very weak B2B platform signal
            logger.info(f"Weak B2B platform indicators (score: {b2b_platform_score:.1f})")
            return DisambiguationResult(
                is_kaso_b2b_platform=False,
                confidence=0.70,
                detected_company='unknown',
                reason=f"Weak B2B platform indicators (score: {b2b_platform_score:.1f}) - likely non-B2B-platform query"
            )

        # ============================================
        # STEP 3: Uncertain - needs further analysis
        # ============================================
        logger.debug(f"Ambiguous query - B2B platform score: {b2b_platform_score:.1f}")
        return DisambiguationResult(
            is_kaso_b2b_platform=None,  # Uncertain
            confidence=0.5,
            detected_company=None,
            reason=f"Ambiguous - B2B platform score: {b2b_platform_score:.1f}, needs further classification"
        )

    def _calculate_b2b_platform_score(self, query_lower: str) -> float:
        """
        Calculate how strongly the query indicates it's about the B2B platform.

        Score calculation:
        - Each exact match = 1.0 point
        - Partial match = 0.5 point

        Args:
            query_lower: Lowercased query string

        Returns:
            Score (typically 0-5, but can be higher)
        """
        score = 0.0

        for lang, indicators in self.b2b_platform_indicators.items():
            for indicator in indicators:
                # Exact word boundary match
                pattern = rf'\b{re.escape(indicator)}\b'
                if re.search(pattern, query_lower, re.IGNORECASE):
                    score += 1.0
                # Partial match (substring)
                elif indicator in query_lower:
                    score += 0.5

        return score

    def get_company_description(self, company_key: str) -> str:
        """
        Get human-readable description of a company.

        Args:
            company_key: Company key (e.g., 'kaso_plastics')

        Returns:
            Description string or 'Unknown company'
        """
        if company_key in self.known_kaso_companies:
            return self.known_kaso_companies[company_key]['description']
        return 'Unknown company'


# Singleton instance
company_disambiguator = CompanyDisambiguator()
