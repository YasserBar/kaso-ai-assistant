"""
Test RAG Pipeline
==================
Tests the RAG system with various queries in multiple languages
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)


async def test_query(query: str, description: str, output_file):
    """Test a single query"""
    output_file.write(f"\n{'='*70}\n")
    output_file.write(f"TEST: {description}\n")
    output_file.write(f"{'='*70}\n")
    output_file.write(f"Query: {query}\n\n")

    try:
        # Process query through RAG
        context, language, sources = rag_service.process_query(query)

        output_file.write(f"Detected Language: {language}\n")
        output_file.write(f"\nRetrieved Context ({len(context)} chars):\n")
        output_file.write("-" * 70 + "\n")
        output_file.write((context[:1000] + "..." if len(context) > 1000 else context) + "\n")
        output_file.write("-" * 70 + "\n")
        output_file.write(f"\nSources ({len(sources)} sources):\n")
        for i, source in enumerate(sources, 1):
            output_file.write(f"  {i}. {source}\n")

    except Exception as e:
        output_file.write(f"ERROR: {e}\n")
        import traceback
        traceback.print_exc(file=output_file)


async def main():
    """Run all tests"""
    # Write to file to avoid Windows console encoding issues
    with open('test_results.txt', 'w', encoding='utf-8') as f:
        f.write("\n" + "="*70 + "\n")
        f.write("KASO AI ASSISTANT - RAG PIPELINE TEST\n")
        f.write("="*70 + "\n")

        test_cases = [
            # Arabic queries
            ("ما هي نشاطات كاسو فودتك؟", "Arabic: What are Kaso Foodtech activities?"),
            ("ماذا تفعل شركة كاسو؟", "Arabic: What does Kaso company do?"),
            ("من هو المؤسس؟", "Arabic: Who is the founder?"),
            ("ما هي منتجات كاسو؟", "Arabic: What are Kaso products?"),

            # English queries
            ("What does Kaso Foodtech do?", "English: What does Kaso Foodtech do?"),
            ("Who founded Kaso?", "English: Who founded Kaso?"),
            ("Tell me about Kaso's business model", "English: Tell me about business model"),

            # French queries
            ("Que fait Kaso Foodtech?", "French: What does Kaso Foodtech do?"),
            ("Qui a fondé Kaso?", "French: Who founded Kaso?"),
        ]

        for query, description in test_cases:
            await test_query(query, description, f)
            f.flush()  # Ensure data is written
            await asyncio.sleep(0.5)  # Small delay between tests

        f.write("\n" + "="*70 + "\n")
        f.write("ALL TESTS COMPLETED!\n")
        f.write("="*70 + "\n")

    logger.info("Test completed! Results saved to test_results.txt")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
