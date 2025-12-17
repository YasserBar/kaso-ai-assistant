"""
Data Indexer
============
Indexes chunks into ChromaDB for semantic search.

This module loads chunk JSON files from `backend/data/chunks/`, computes
embeddings via `EmbeddingService`, and stores them in a persistent ChromaDB
collection using `ChromaService`.

CLI:
    python -m data_pipeline.indexer [--reset]

Notes:
    - Indexing is batched for efficiency
    - By default, new chunks are appended to the existing collection
      (supports incremental updates). Use `--reset` for a full rebuild.
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.chroma_service import ChromaService
from data_pipeline.logger import setup_pipeline_logger


class DataIndexer:
    """
    Indexes document chunks into ChromaDB.

    Services:
    - EmbeddingService: Provides multilingual sentence embeddings
    - ChromaService: Manages a disk-persisted Chroma collection

    Directories:
    - chunks_dir: Input directory containing chunk JSON files

    Typical Flow:
    - Load chunks → initialize services → add documents in batches → log summary.
    """
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / "data"
        self.base_dir = Path(base_dir)
        self.chunks_dir = self.base_dir / "chunks"

        # Setup logger
        self.logger = setup_pipeline_logger("indexer")

        # Initialize services
        self.embedding_service = EmbeddingService()
        self.chroma_service = ChromaService()
    
    def load_chunks(self) -> List[Dict]:
        """Load all chunk files from `chunks_dir` and aggregate into a list."""
        all_chunks = []

        for chunk_file in self.chunks_dir.glob("*.json"):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                    if isinstance(chunks, list):
                        all_chunks.extend(chunks)
                        self.logger.debug(f"Loaded {len(chunks)} chunks from {chunk_file.name}")
            except Exception as e:
                self.logger.error(f"Error loading {chunk_file.name}: {e}")

        return all_chunks
    
    def index_chunks(self, chunks: List[Dict], batch_size: int = 100) -> int:
        """
        Index chunks into ChromaDB.

        Args:
            chunks: List of chunk dictionaries
            batch_size: Number of chunks to process at once

        Returns:
            Number of indexed chunks
        
        Behavior:
            - Initializes embedding and Chroma services once per run
            - Creates UUIDs for each chunk document
            - Persists source/title + positional metadata for future attribution
            - Uses service-layer `add_documents` to handle embedding and storage
        """
        if not chunks:
            self.logger.warning("No chunks to index")
            return 0

        self.logger.info(f"Indexing {len(chunks)} chunks...")
        self.logger.info(f"Batch size: {batch_size}")

        # Initialize services
        self.logger.info("Loading embedding model...")
        self.embedding_service.initialize()

        self.logger.info("Initializing ChromaDB...")
        self.chroma_service.initialize()

        # Process in batches
        indexed = 0

        for i in tqdm(range(0, len(chunks), batch_size), desc="Indexing"):
            batch = chunks[i:i+batch_size]

            documents = []
            metadatas = []
            ids = []

            for chunk in batch:
                doc_id = str(uuid.uuid4())

                documents.append(chunk['content'])
                metadatas.append({
                    'source': chunk.get('source', ''),
                    'title': chunk.get('title', ''),
                    'chunk_index': chunk.get('chunk_index', 0),
                    'total_chunks': chunk.get('total_chunks', 1)
                })
                ids.append(doc_id)

            # Add to ChromaDB
            self.chroma_service.add_documents(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            indexed += len(batch)
            self.logger.debug(f"Indexed batch {i//batch_size + 1}: {len(batch)} chunks")

        total_count = self.chroma_service.get_count()

        self.logger.info("=" * 70)
        self.logger.info(f"INDEXING COMPLETE")
        self.logger.info(f"  Indexed: {indexed} chunks")
        self.logger.info(f"  Total in DB: {total_count} documents")
        self.logger.info("=" * 70)

        return indexed
    
    def index_all(self) -> int:
        """
        Index all chunks from the chunks directory.

        Returns:
            Number of chunks indexed across all chunk files.
        """
        chunks = self.load_chunks()
        return self.index_chunks(chunks)
    
    def reset_index(self):
        """
        Clear and reset the ChromaDB collection.

        Use with caution: this wipes the collection and is only needed for
        full rebuilds. Incremental updates normally do not require reset.
        """
        self.logger.warning("Resetting ChromaDB collection...")
        self.chroma_service.initialize()
        self.chroma_service.reset()
        self.logger.info("Collection reset - now empty")


def main():
    """CLI entry point to index chunks into ChromaDB with optional reset."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Index chunks into ChromaDB")
    parser.add_argument('--reset', action='store_true', help="Reset collection before indexing")
    args = parser.parse_args()
    
    indexer = DataIndexer()
    
    if args.reset:
        indexer.reset_index()
    
    indexer.index_all()


if __name__ == "__main__":
    main()
