"""
Content Quality Validator
==========================
Validates scraped content quality using hybrid approach:
1. Fast heuristics for obvious errors (404, 403, auth barriers)
2. AI (Groq LLM) for ambiguous cases (using project's existing API)

Design:
- Stage 1 (Fast): Filters ~70-80% of files instantly
- Stage 2 (AI): Uses Groq LLM for remaining ~20-30%
- Total cost: minimal tokens per pipeline run

CLI:
    python -m data_pipeline.content_validator backend/data/raw/*.json --verbose
"""

import re
import json
from typing import Tuple, Dict, Optional
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.llm_service import LLMService
from data_pipeline.logger import setup_pipeline_logger


class ContentValidator:
    """
    Validates content quality using heuristics + AI.

    Two-stage validation:
    1. Fast heuristics for clear errors
    2. AI validation for ambiguous content
    """

    def __init__(self, use_ai: bool = True):
        """
        Args:
            use_ai: Enable AI validation for ambiguous cases (default: True)
        """
        self.use_ai = use_ai
        self.logger = setup_pipeline_logger("validator")

        # Initialize LLM service for AI validation
        if self.use_ai:
            try:
                self.llm = LLMService()
                self.logger.info("AI validation enabled (Groq LLM)")
            except Exception as e:
                self.logger.warning(f"Could not initialize LLM service: {e}")
                self.use_ai = False

        # Error patterns to detect (Stage 1 - Fast)
        self.error_patterns = [
            r'404.*not\s+found',
            r'error.*occurred',
            r'access\s+denied',
            r'forbidden',
            r'403\s+error',
            r'cloudfront.*request',
            r'just\s+a\s+moment',
            r'enable\s+javascript',
            r'verification.*required',
            r'sign\s+in',
            r'sign\s+up',
            r'log\s+in',
            r'نعتذر\s+عن',
            r'قيد\s+الصيانة',
            r'تحديث\s+الموقع',
            r'page\s+not\s+found',
            r'reference\s+#[\d.]+',
            r'checking\s+your\s+browser',
        ]

        # Authentication barriers
        self.auth_keywords = [
            'sign in to continue',
            'log in to view',
            'create an account',
            'verify you are human',
            'checking your browser',
            'enable cookies',
            'javascript is required',
        ]

        # Kaso-related keywords for relevance check
        self.kaso_keywords = [
            'kaso',
            'elkaso',
            'food supply',
            'restaurant',
            'supplier',
            'dubai',
            'uae',
            'saudi',
            'foodtech',
            'y combinator',
        ]

        # Generic/low-quality indicators
        self.generic_indicators = [
            'cookie policy',
            'privacy policy',
            'terms of service',
            'accept cookies',
        ]

    def _validate_with_ai(self, content: str, title: str, url: str) -> Tuple[bool, str]:
        """
        Use AI (Groq LLM) to validate ambiguous content.

        Args:
            content: Text content (first 800 chars)
            title: Page title
            url: Source URL

        Returns:
            Tuple of (is_valid, reason)
        """
        if not self.use_ai:
            return True, "AI validation disabled - assuming valid"

        try:
            # Truncate content to 800 chars to save tokens
            content_preview = content[:800]

            prompt = f"""You are a content quality validator for a knowledge base about "Kaso", a food supply company in the Middle East.

**Task**: Determine if this scraped content is relevant and high-quality.

**Content to validate**:
Title: {title}
URL: {url}
Content preview (first 800 chars):
---
{content_preview}
---

**Answer in JSON format ONLY**:
{{
  "valid": true/false,
  "reason": "brief explanation (max 15 words)",
  "confidence": 0.0-1.0
}}

**Valid content includes**:
- Information about Kaso company, products, services
- News articles mentioning Kaso
- Industry reports about food supply in Middle East
- Y Combinator portfolio pages mentioning Kaso

**Invalid content includes**:
- Error pages (404, 403, CloudFront errors)
- Login/authentication barriers
- Cookie consent pages without real content
- Completely unrelated topics

Respond with JSON only, no other text."""

            # Call LLM service
            response = self.llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a helpful content validator. Always respond in valid JSON format."
            )

            # Parse JSON response
            result = json.loads(response)
            is_valid = result.get("valid", False)
            reason = result.get("reason", "AI validation result")
            confidence = result.get("confidence", 0.5)

            self.logger.debug(f"AI validation: valid={is_valid}, confidence={confidence}, reason={reason}")

            return is_valid, f"AI: {reason}"

        except Exception as e:
            self.logger.warning(f"AI validation failed: {e}, assuming valid")
            return True, f"AI validation error: {e}"

    def validate(self, content: str, title: str = "", url: str = "") -> Tuple[bool, str, Dict]:
        """
        Validate content quality using two-stage approach.

        Args:
            content: Text content to validate
            title: Page title
            url: Source URL

        Returns:
            Tuple of (is_valid, reason, metrics)
        """
        content_lower = content.lower()
        title_lower = title.lower()

        metrics = {
            'content_length': len(content),
            'has_kaso_keywords': False,
            'kaso_keyword_count': 0,
            'has_error_patterns': False,
            'has_auth_barriers': False,
            'is_generic': False,
            'used_ai': False,
        }

        # STAGE 1: Fast Heuristics (no AI needed)

        # 1. Length checks
        if len(content) < 100:
            return False, f"Content too short ({len(content)} chars)", metrics

        # 2. Error pattern detection
        for pattern in self.error_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                metrics['has_error_patterns'] = True
                return False, f"Error pattern detected: {pattern}", metrics

        # 3. Authentication barrier detection
        for keyword in self.auth_keywords:
            if keyword.lower() in content_lower:
                metrics['has_auth_barriers'] = True
                return False, f"Authentication barrier: {keyword}", metrics

        # 4. CloudFront error reference check
        if re.search(r'Reference #[\d.]+', content):
            return False, "CloudFront error reference detected", metrics

        # 5. Kaso relevance check
        kaso_count = sum(1 for kw in self.kaso_keywords if kw.lower() in content_lower)
        metrics['kaso_keyword_count'] = kaso_count
        metrics['has_kaso_keywords'] = kaso_count > 0

        # 6. Generic content check
        generic_count = sum(1 for ind in self.generic_indicators if ind in content_lower)
        if generic_count >= 2 and len(content) < 1000 and kaso_count == 0:
            metrics['is_generic'] = True
            return False, "Generic/boilerplate content only", metrics

        # STAGE 2: AI Validation for Ambiguous Cases

        # Case 1: Short content without Kaso keywords
        if len(content) < 1000 and kaso_count == 0:
            self.logger.debug(f"Ambiguous content detected, using AI validation...")
            metrics['used_ai'] = True
            is_valid, reason = self._validate_with_ai(content, title, url)
            return is_valid, reason, metrics

        # Case 2: Title mentions Kaso but content doesn't (unclear)
        if 'kaso' in title_lower and kaso_count == 0 and len(content) < 1500:
            self.logger.debug(f"Title/content mismatch, using AI validation...")
            metrics['used_ai'] = True
            is_valid, reason = self._validate_with_ai(content, title, url)
            return is_valid, reason, metrics

        # Passed all checks (clearly valid)
        return True, "Content passed quality checks", metrics


def validate_file(file_path: Path, validator: ContentValidator = None) -> Tuple[bool, str, Dict]:
    """
    Validate a scraped JSON file.

    Args:
        file_path: Path to JSON file
        validator: ContentValidator instance (creates new if None)

    Returns:
        Tuple of (is_valid, reason, metrics)
    """
    if validator is None:
        validator = ContentValidator()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        content = data.get('content', '')
        title = data.get('title', '')
        url = data.get('url', '')

        return validator.validate(content, title, url)

    except Exception as e:
        return False, f"Error reading file: {e}", {}


def main():
    """CLI tool to validate files manually."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate scraped content quality")
    parser.add_argument('files', nargs='+', help="Files to validate")
    parser.add_argument('--verbose', '-v', action='store_true', help="Show detailed metrics")
    args = parser.parse_args()

    validator = ContentValidator()

    valid_count = 0
    invalid_count = 0

    for file_path in args.files:
        file_path = Path(file_path)

        if not file_path.exists():
            print(f"\nERROR: File not found: {file_path}")
            continue

        print(f"\n{'='*70}")
        print(f"File: {file_path.name}")
        print(f"{'='*70}")

        is_valid, reason, metrics = validate_file(file_path, validator)

        status = "✓ VALID" if is_valid else "✗ INVALID"
        print(f"Status: {status}")
        print(f"Reason: {reason}")

        if args.verbose:
            print(f"\nMetrics:")
            for key, value in metrics.items():
                print(f"  {key}: {value}")

        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Valid:   {valid_count}/{len(args.files)}")
    print(f"Invalid: {invalid_count}/{len(args.files)}")


if __name__ == "__main__":
    main()
