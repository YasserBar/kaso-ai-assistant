"""
Data Chunker
============
Splits documents into chunks for embedding.

This module reads cleaned JSON documents from `backend/data/processed/` and
splits long text into overlapping chunks to balance retrieval recall and
answer coherence. Chunks are saved to `backend/data/chunks/` as JSON.

CLI:
    python -m data_pipeline.chunker --chunk-size 500 --overlap 50
    python -m data_pipeline.chunker --markdown ../kaso_research_report.md

Rationale:
    - Overlap helps preserve context across chunk boundaries
    - RecursiveCharacterTextSplitter breaks at semantic separators first
"""

import json
from pathlib import Path
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter

from data_pipeline.logger import setup_pipeline_logger


class DataChunker:
    """
    Splits documents into chunks suitable for embedding.

    Design:
    - Uses `RecursiveCharacterTextSplitter` with configurable `chunk_size`
      and `chunk_overlap` to produce consistent token-friendly segments.
    - Emits chunk metadata (source URL/title, indices) required for traceability
      and attribution downstream in the RAG pipeline.

    Inputs:
    - processed_dir: Cleaned documents (JSON)

    Outputs:
    - chunks_dir/all_chunks.json: Aggregated chunks across all documents
    - chunks_dir/<name>_chunks.json: Chunks for a specific markdown file
    """
    
    def __init__(
        self,
        base_dir: str = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / "data"
        self.base_dir = Path(base_dir)
        self.processed_dir = self.base_dir / "processed"
        self.chunks_dir = self.base_dir / "chunks"

        # Setup logger
        self.logger = setup_pipeline_logger("chunker")

        # Create directories
        self.chunks_dir.mkdir(parents=True, exist_ok=True)

        # Initialize splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
    
    def chunk_document(self, doc: Dict) -> List[Dict]:
        """
        Split a document into chunks.
        
        Behavior:
        - Skips documents without `content`
        - Splits content according to splitter configuration
        - Preserves source/title, and records `chunk_index` and `total_chunks`
        
        Returns:
            List of chunk dictionaries suitable for embedding/indexing.
        """
        content = doc.get('content', '')
        
        if not content:
            return []
        
        # Split text
        texts = self.splitter.split_text(content)
        
        # Create chunk objects
        chunks = []
        for i, text in enumerate(texts):
            chunks.append({
                'content': text,
                'source': doc.get('url', ''),
                'title': doc.get('title', ''),
                'chunk_index': i,
                'total_chunks': len(texts)
            })
        
        return chunks
    
    def chunk_markdown_file(self, file_path: Path) -> List[Dict]:
        """
        Chunk a markdown file directly.
        Useful for the research report or any ad-hoc knowledge files.
        
        Args:
            file_path: Absolute or relative path to a markdown file
        
        Returns:
            List of chunk dictionaries with `source` set to the file name.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split
        texts = self.splitter.split_text(content)
        
        # Create chunks
        chunks = []
        for i, text in enumerate(texts):
            chunks.append({
                'content': text,
                'source': file_path.name,
                'title': file_path.stem,
                'chunk_index': i,
                'total_chunks': len(texts)
            })
        
        return chunks
    
    def process_all(self) -> int:
        """
        Process all cleaned documents found in `processed_dir`.

        Logging:
        - Reports chunker configuration (size/overlap) for reproducibility
        - Emits per-file chunk counts and final totals

        Returns:
            Total number of chunks created across all processed documents.
        """
        processed_files = list(self.processed_dir.glob("*.json"))

        all_chunks = []

        self.logger.info(f"Chunking {len(processed_files)} documents...")
        self.logger.info(f"Chunk size: {self.splitter._chunk_size}")
        self.logger.info(f"Chunk overlap: {self.splitter._chunk_overlap}")

        for doc_file in processed_files:
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    doc = json.load(f)

                chunks = self.chunk_document(doc)
                all_chunks.extend(chunks)
                self.logger.debug(f"Chunked: {doc_file.name} -> {len(chunks)} chunks")

            except Exception as e:
                self.logger.error(f"Error chunking {doc_file.name}: {e}")

        # Save all chunks
        output_file = self.chunks_dir / "all_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        self.logger.info("=" * 70)
        self.logger.info(f"CHUNKING COMPLETE")
        self.logger.info(f"  Created: {len(all_chunks)} chunks")
        self.logger.info(f"  Output: {output_file}")
        self.logger.info("=" * 70)

        return len(all_chunks)
    
    def process_markdown(self, file_path: str) -> int:
        """
        Process a markdown file (like the research report).

        Args:
            file_path: Path to markdown file

        Returns:
            Number of chunks created for the given file.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return 0

        self.logger.info(f"Chunking markdown file: {file_path.name}")

        chunks = self.chunk_markdown_file(file_path)

        # Save chunks
        output_file = self.chunks_dir / f"{file_path.stem}_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Created {len(chunks)} chunks from {file_path.name}")
        self.logger.info(f"Output: {output_file}")

        return len(chunks)


def main():
    """CLI entry point that supports both JSON and markdown chunking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Chunk documents for embedding")
    parser.add_argument('--markdown', type=str, help="Path to markdown file to chunk")
    parser.add_argument('--chunk-size', type=int, default=500)
    parser.add_argument('--overlap', type=int, default=50)
    args = parser.parse_args()
    
    chunker = DataChunker(
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap
    )
    
    if args.markdown:
        chunker.process_markdown(args.markdown)
    else:
        chunker.process_all()


if __name__ == "__main__":
    main()
