"""
Data Cleaner
============
Cleans and normalizes scraped content.

This module reads raw scraped JSON files from `backend/data/raw/`, applies
light text normalization (whitespace, boilerplate removal), and writes
cleaned documents to `backend/data/processed/` for downstream chunking
and indexing.

CLI:
    python -m data_pipeline.cleaner

Outputs:
    - processed/*.json files with `cleaned: true`
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional

from data_pipeline.logger import setup_pipeline_logger


class DataCleaner:
    """
    Cleans raw scraped content and prepares it for chunking.

    Responsibilities:
    - Remove extra whitespace and excessive newlines from text
    - Normalize common boilerplate/footer content patterns
    - Preserve essential metadata (url, title, scraped_at)
    - Skip ultra-short content after cleaning to reduce noise

    Directories:
    - raw_dir:     Input directory containing raw scraped JSON files
    - processed_dir: Output directory for cleaned JSON files

    This class is intentionally simple and fast as it may run frequently
    in incremental pipeline updates.
    """
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / "data"
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"

        # Setup logger
        self.logger = setup_pipeline_logger("cleaner")

        # Create directories
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def clean_text(self, text: str) -> str:
        """
        Clean a text string.

        Steps:
        - Collapse multiple whitespace characters into single spaces
        - Reduce 3+ consecutive newlines to exactly two (paragraph break)
        - Remove common site boilerplate (cookies, legal, newsletter prompts)
        - Trim leading/trailing whitespace

        Args:
            text: Raw input text to normalize. If None or empty, returns empty string.

        Returns:
            A normalized string safe for downstream chunking/embedding.
        """
        if not text:
            return ""
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove common boilerplate
        boilerplate_patterns = [
            r'Cookie\s*Policy.*?Accept',
            r'Subscribe\s*to\s*our\s*newsletter',
            r'Follow\s*us\s*on\s*social\s*media',
            r'All\s*rights\s*reserved',
            r'Privacy\s*Policy.*?Terms',
            r'©\s*\d{4}',
        ]
        
        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Trim
        text = text.strip()
        
        return text
    
    def clean_document(self, doc: Dict) -> Dict:
        """
        Clean a single document while preserving metadata.

        Args:
            doc: A dictionary representing a scraped page with keys like
                 `url`, `title`, `content`, `scraped_at`.

        Returns:
            A dictionary with normalized `title` and `content`, original
            metadata fields, and a `cleaned: True` flag.
        """
        return {
            'url': doc.get('url', ''),
            'title': self.clean_text(doc.get('title', '')),
            'content': self.clean_text(doc.get('content', '')),
            'scraped_at': doc.get('scraped_at', ''),
            'cleaned': True
        }
    
    def process_all(self) -> int:
        """
        Process all raw documents in the input directory.

        Behavior:
        - Iterates over `raw/*.json` files
        - Applies `clean_document` to each
        - Skips documents whose cleaned content is < 50 characters
        - Writes cleaned output to `processed/*.json`
        - Logs summary metrics (processed/skipped)

        Returns:
            Number of processed documents successfully written.
        """
        raw_files = list(self.raw_dir.glob("*.json"))

        if not raw_files:
            self.logger.warning("No raw files to process")
            return 0

        self.logger.info(f"Cleaning {len(raw_files)} documents...")

        processed_count = 0
        skipped_count = 0

        for raw_file in raw_files:
            try:
                with open(raw_file, 'r', encoding='utf-8') as f:
                    doc = json.load(f)

                cleaned = self.clean_document(doc)

                # Skip if content too short after cleaning
                if len(cleaned['content']) < 50:
                    self.logger.debug(f"Skipping {raw_file.name}: content too short after cleaning")
                    skipped_count += 1
                    continue

                # Save
                output_file = self.processed_dir / raw_file.name
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned, f, indent=2, ensure_ascii=False)

                processed_count += 1
                self.logger.debug(f"Cleaned: {raw_file.name}")

            except Exception as e:
                self.logger.error(f"Error processing {raw_file.name}: {e}")

        self.logger.info("=" * 70)
        self.logger.info(f"CLEANING COMPLETE")
        self.logger.info(f"  Processed: {processed_count} documents")
        self.logger.info(f"  Skipped: {skipped_count} documents")
        self.logger.info("=" * 70)

        return processed_count


def main():
    """CLI entry point to run the cleaner over all raw files."""
    cleaner = DataCleaner()
    cleaner.process_all()


if __name__ == "__main__":
    main()
