"""
Full Pipeline Runner
====================
Runs the complete data pipeline:
1. Scrape URLs
2. Clean content  
3. Chunk documents
4. Index in ChromaDB
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_pipeline.scraper import DataScraper
from data_pipeline.cleaner import DataCleaner
from data_pipeline.chunker import DataChunker
from data_pipeline.indexer import DataIndexer
from data_pipeline.logger import setup_pipeline_logger


def run_pipeline(
    scrape: bool = True,
    clean: bool = True,
    chunk: bool = True,
    index: bool = True,
    include_markdown: str = None,
    reset_index: bool = False
):
    """
    Run the full data pipeline

    Args:
        scrape: Whether to scrape URLs
        clean: Whether to clean scraped content
        chunk: Whether to chunk documents
        index: Whether to index in ChromaDB
        include_markdown: Optional path to markdown file to include
        reset_index: Whether to reset ChromaDB before indexing
    """
    # Setup main logger
    logger = setup_pipeline_logger("pipeline")

    logger.info("=" * 70)
    logger.info("KASO AI ASSISTANT - DATA PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Steps to run:")
    logger.info(f"  - Scrape: {scrape}")
    logger.info(f"  - Clean: {clean}")
    logger.info(f"  - Chunk: {chunk}")
    logger.info(f"  - Index: {index}")
    logger.info(f"  - Reset index: {reset_index}")
    if include_markdown:
        logger.info(f"  - Include markdown: {include_markdown}")
    logger.info("=" * 70)

    # Step 1: Scrape sources to raw JSON files (may use Selenium when necessary)
    if scrape:
        logger.info("\nSTEP 1/4: Scraping URLs...")
        scraper = DataScraper()
        count = scraper.scrape_all()
        logger.info(f"Scraping done - {count} URLs successful")

    # Step 2: Clean
    if clean:
        logger.info("\nSTEP 2/4: Cleaning content...")
        cleaner = DataCleaner()
        count = cleaner.process_all()
        logger.info(f"Cleaning done - {count} documents processed")

    # Step 3: Chunk documents for vector indexing; optionally include markdown file
    if chunk:
        logger.info("\nSTEP 3/4: Chunking documents...")
        chunker = DataChunker()
        count = chunker.process_all()
        logger.info(f"Chunking done - {count} chunks created")
        # Also chunk markdown if provided
        if include_markdown:
            logger.info(f"Processing markdown file: {include_markdown}")
            md_count = chunker.process_markdown(include_markdown)
            logger.info(f"Markdown processing done - {md_count} chunks created")

    # Step 4: Index chunks into ChromaDB; optionally reset collection before indexing
    if index:
        logger.info("\nSTEP 4/4: Indexing in ChromaDB...")
        indexer = DataIndexer()
        if reset_index:
            indexer.reset_index()
        count = indexer.index_all()
        logger.info(f"Indexing done - {count} chunks indexed")

    logger.info("\n" + "=" * 70)
    logger.info("PIPELINE COMPLETE!")
    logger.info("=" * 70)
    logger.info("Check logs in: backend/logs/")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the data pipeline")
    # Flags to skip steps and control markdown inclusion/reset behavior
    parser.add_argument('--no-scrape', action='store_true', help="Skip scraping")
    parser.add_argument('--no-clean', action='store_true', help="Skip cleaning")
    parser.add_argument('--no-chunk', action='store_true', help="Skip chunking")
    parser.add_argument('--no-index', action='store_true', help="Skip indexing")
    parser.add_argument('--markdown', type=str, help="Path to markdown file to include")
    parser.add_argument('--reset', action='store_true', help="Reset ChromaDB before indexing")
    args = parser.parse_args()
    
    run_pipeline(
        scrape=not args.no_scrape,
        clean=not args.no_clean,
        chunk=not args.no_chunk,
        index=not args.no_index,
        include_markdown=args.markdown,
        reset_index=args.reset
    )


if __name__ == "__main__":
    main()
