"""
ChromaDB Service
================
Vector database for storing and retrieving document chunks
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.embedding_service import embedding_service


class ChromaService:
    """
    Service for interacting with ChromaDB vector database
    """
    
    _instance: Optional['ChromaService'] = None
    _client: Optional[chromadb.PersistentClient] = None
    _collection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self):
        """Initialize ChromaDB client and collection"""
        if self._client is None:
            # Create persistent client
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
    
    @property
    def collection(self):
        """Get the ChromaDB collection"""
        if self._collection is None:
            self.initialize()
        return self._collection
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """
        Add documents to the collection.
        
        Args:
            documents: List of text documents.
            metadatas: List of metadata dicts for each document (e.g., source URL, title).
            ids: List of unique IDs for each document.
        """
        # Generate embeddings for each document chunk
        embeddings = embedding_service.embed_texts(documents)
        
        # Add to collection (Chroma will persist to disk under settings.chroma_persist_directory)
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
    
    def query(
        self,
        query_text: str,
        n_results: int = 10,
        where: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Query the collection for similar documents
        
        Args:
            query_text: Query text
            n_results: Number of results to return
            where: Optional filter conditions
            
        Returns:
            Dict with 'documents', 'metadatas', 'distances', 'ids'
        """
        # Generate query embedding
        query_embedding = embedding_service.embed_text(query_text)
        
        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "ids": results["ids"][0] if results["ids"] else []
        }
    
    def get_count(self) -> int:
        """Get total number of documents in collection"""
        return self.collection.count()
    
    def delete_by_source(self, source: str):
        """Delete all documents from a specific source"""
        self.collection.delete(where={"source": source})
    
    def reset(self):
        """Clear all documents from collection"""
        self._client.delete_collection(settings.chroma_collection_name)
        self._collection = self._client.create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"}
        )


# Singleton instance
chroma_service = ChromaService()
