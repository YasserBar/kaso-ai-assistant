"""
Pipeline Reset Script
=====================
Deletes all pipeline data and resets the system to start fresh.

DANGER: This will delete ALL scraped data, processed content, chunks, and ChromaDB index!
Chat history will be preserved.
"""

import shutil
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def reset_pipeline(base_dir: Path = None, confirm: bool = False):
    """
    Reset the entire data pipeline

    Args:
        base_dir: Base data directory (default: backend/data)
        confirm: Set to True to actually delete (safety check)
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent / "data"

    base_dir = Path(base_dir)

    # Items to delete
    items_to_delete = [
        base_dir / "raw",
        base_dir / "processed",
        base_dir / "chunks",
        base_dir / "chroma_db",
        base_dir / "scrape_status.json",
        # Also clean up data_pipeline/data if it exists (artifacts from running in wrong dir)
        Path(__file__).parent / "data"
    ]

    # Items to preserve
    items_to_preserve = [
        base_dir / "chat_history.db",
        base_dir / "kaso_data_sources.csv"
    ]

    if not confirm:
        logger.warning("=" * 60)
        logger.warning("RESET PIPELINE - DRY RUN MODE")
        logger.warning("=" * 60)
        logger.warning("The following items will be DELETED:")
        for item in items_to_delete:
            if item.exists():
                if item.is_dir():
                    logger.warning(f"  - {item}/ (directory)")
                else:
                    logger.warning(f"  - {item} (file)")
            else:
                logger.warning(f"  - {item} (does not exist)")

        logger.warning("\nThe following items will be PRESERVED:")
        for item in items_to_preserve:
            logger.warning(f"  + {item}")

        logger.warning("\nTo actually delete, run with --confirm flag:")
        logger.warning("  python -m data_pipeline.reset_pipeline --confirm")
        return False

    # Actual deletion
    logger.info("=" * 60)
    logger.info("RESET PIPELINE - STARTING")
    logger.info("=" * 60)

    deleted_count = 0

    for item in items_to_delete:
        try:
            if item.exists():
                if item.is_dir():
                    logger.info(f"Deleting directory: {item}")
                    shutil.rmtree(item)
                else:
                    logger.info(f"Deleting file: {item}")
                    item.unlink()
                deleted_count += 1
            else:
                logger.info(f"Skipping (not found): {item}")
        except Exception as e:
            logger.error(f"Error deleting {item}: {e}")

    # Recreate empty directories
    logger.info("\nRecreating empty directories...")
    (base_dir / "raw").mkdir(parents=True, exist_ok=True)
    (base_dir / "processed").mkdir(parents=True, exist_ok=True)
    (base_dir / "chunks").mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info(f"RESET COMPLETE - Deleted {deleted_count} items")
    logger.info("=" * 60)
    logger.info("Run the pipeline to rebuild the knowledge base:")
    logger.info("  python -m data_pipeline.run_pipeline")

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Reset the data pipeline (DELETE ALL DATA)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
DANGER: This will delete ALL pipeline data!
  - Scraped content (raw/)
  - Processed content (processed/)
  - Document chunks (chunks/)
  - ChromaDB index (chroma_db/)
  - Scraping status (scrape_status.json)

PRESERVED:
  - Chat history (chat_history.db)
  - Source URLs (kaso_data_sources.csv)

Examples:
  # Dry run (see what will be deleted):
  python -m data_pipeline.reset_pipeline

  # Actually delete:
  python -m data_pipeline.reset_pipeline --confirm
        """
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help="Actually delete data (required for safety)"
    )

    args = parser.parse_args()
    reset_pipeline(confirm=args.confirm)


if __name__ == "__main__":
    main()
