"""
Unit Tests for Data Pipeline
=============================
Tests for scraper, cleaner, chunker components
"""

import pytest
import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataCleaner:
    """Tests for DataCleaner"""
    
    def test_clean_text_whitespace(self):
        """Test whitespace normalization"""
        from data_pipeline.cleaner import DataCleaner
        
        cleaner = DataCleaner()
        
        text = "Hello   world\n\n\n\ntest"
        result = cleaner.clean_text(text)
        
        assert "   " not in result  # No multiple spaces
    
    def test_clean_text_empty(self):
        """Test cleaning empty text"""
        from data_pipeline.cleaner import DataCleaner
        
        cleaner = DataCleaner()
        
        result = cleaner.clean_text("")
        assert result == ""
    
    def test_clean_text_none(self):
        """Test cleaning None"""
        from data_pipeline.cleaner import DataCleaner
        
        cleaner = DataCleaner()
        
        result = cleaner.clean_text(None)
        assert result == ""
    
    def test_clean_document(self):
        """Test document cleaning"""
        from data_pipeline.cleaner import DataCleaner
        
        cleaner = DataCleaner()
        
        doc = {
            "url": "https://example.com",
            "title": "  Test Title  ",
            "content": "  Test content  with   spaces  ",
            "scraped_at": "2024-01-01"
        }
        
        result = cleaner.clean_document(doc)
        
        assert result["url"] == "https://example.com"
        assert result["title"] == "Test Title"
        assert result["cleaned"] is True


class TestDataChunker:
    """Tests for DataChunker"""
    
    def test_chunk_empty_content(self):
        """Test chunking empty document"""
        from data_pipeline.chunker import DataChunker
        
        chunker = DataChunker()
        
        doc = {"content": "", "url": "test.com", "title": "Test"}
        chunks = chunker.chunk_document(doc)
        
        assert len(chunks) == 0
    
    def test_chunk_short_content(self):
        """Test chunking short content"""
        from data_pipeline.chunker import DataChunker
        
        chunker = DataChunker(chunk_size=100, chunk_overlap=10)
        
        doc = {
            "content": "Short content",
            "url": "test.com",
            "title": "Test"
        }
        chunks = chunker.chunk_document(doc)
        
        assert len(chunks) == 1
        assert chunks[0]["content"] == "Short content"
        assert chunks[0]["source"] == "test.com"
    
    def test_chunk_long_content(self):
        """Test chunking long content splits properly"""
        from data_pipeline.chunker import DataChunker
        
        chunker = DataChunker(chunk_size=50, chunk_overlap=10)
        
        # Create content longer than chunk size
        long_content = "This is a test. " * 20
        
        doc = {
            "content": long_content,
            "url": "test.com",
            "title": "Test"
        }
        chunks = chunker.chunk_document(doc)
        
        assert len(chunks) > 1
        assert all(chunk["source"] == "test.com" for chunk in chunks)
    
    def test_chunk_preserves_metadata(self):
        """Test that chunking preserves metadata"""
        from data_pipeline.chunker import DataChunker
        
        chunker = DataChunker()
        
        doc = {
            "content": "Test content",
            "url": "https://example.com/article",
            "title": "Article Title"
        }
        chunks = chunker.chunk_document(doc)
        
        assert chunks[0]["source"] == "https://example.com/article"
        assert chunks[0]["title"] == "Article Title"
        assert "chunk_index" in chunks[0]
        assert "total_chunks" in chunks[0]


class TestDataScraper:
    """Tests for DataScraper"""
    
    def test_get_url_hash(self):
        """Test URL hashing"""
        from data_pipeline.scraper import DataScraper
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = DataScraper(base_dir=tmpdir)
            
            hash1 = scraper.get_url_hash("https://example.com/1")
            hash2 = scraper.get_url_hash("https://example.com/2")
            hash3 = scraper.get_url_hash("https://example.com/1")
            
            assert hash1 != hash2  # Different URLs have different hashes
            assert hash1 == hash3  # Same URL has same hash
    
    def test_load_sources_empty(self):
        """Test loading sources when file doesn't exist"""
        from data_pipeline.scraper import DataScraper
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = DataScraper(base_dir=tmpdir)
            sources = scraper.load_sources()
            
            assert sources == []
    
    def test_load_status_empty(self):
        """Test loading status when file doesn't exist"""
        from data_pipeline.scraper import DataScraper
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = DataScraper(base_dir=tmpdir)
            status = scraper.load_status()
            
            assert status == {}
    
    def test_save_and_load_status(self):
        """Test saving and loading status"""
        from data_pipeline.scraper import DataScraper
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = DataScraper(base_dir=tmpdir)
            
            status = {"url1": {"success": True}, "url2": {"success": False}}
            scraper.save_status(status)
            
            loaded = scraper.load_status()
            
            assert loaded == status


class TestPipelineIntegration:
    """Integration tests for the full pipeline"""
    
    def test_chunker_to_json(self):
        """Test that chunker output is valid JSON"""
        from data_pipeline.chunker import DataChunker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            chunker = DataChunker(base_dir=tmpdir)
            
            # Create processed directory
            processed_dir = Path(tmpdir) / "processed"
            processed_dir.mkdir()
            
            # Create test document
            test_doc = {
                "url": "https://test.com",
                "title": "Test",
                "content": "This is test content for chunking.",
                "cleaned": True
            }
            
            with open(processed_dir / "test.json", "w") as f:
                json.dump(test_doc, f)
            
            # Process
            count = chunker.process_all()
            
            # Verify output
            chunks_file = Path(tmpdir) / "chunks" / "all_chunks.json"
            assert chunks_file.exists()
            
            with open(chunks_file) as f:
                chunks = json.load(f)
            
            assert isinstance(chunks, list)
            assert len(chunks) > 0
