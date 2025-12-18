from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ════════════════════════════════════════
    # LLM and Models
    # ════════════════════════════════════════
    llm_model: str = Field(
        default="llama-3.1-8b-instant",
        description="Groq model to use"
    )
    embedding_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        description="SentenceTransformer embedding model (supports 100+ languages)"
    )
    reranker_model: str = Field(
        default="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        description="CrossEncoder reranking model (multilingual)"
    )

    # ════════════════════════════════════════
    # API Configuration
    # ════════════════════════════════════════
    groq_api_key: str = Field(
        default="",
        description="Groq API key for LLM access"
    )
    api_secret_key: str = Field(
        default="",
        description="Shared secret between frontend proxy and backend"
    )
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="CORS origins"
    )

    # ════════════════════════════════════════
    # Multilingual Settings (Solution 4)
    # ════════════════════════════════════════
    multilingual_enabled: bool = Field(
        default=True,
        description="Enable full multilingual support (100+ languages)"
    )
    multilingual_use_llm_for_messages: bool = Field(
        default=True,
        description="Use LLM to generate messages for uncommon languages"
    )
    multilingual_cache_size: int = Field(
        default=100,
        description="Cache size for generated multilingual messages"
    )

    # ════════════════════════════════════════
    # Intent Classification Settings (Solution 1)
    # ════════════════════════════════════════
    intent_use_keywords: bool = Field(
        default=False,
        description="Use keyword matching for intent classification (NOT recommended for multilingual)"
    )
    intent_llm_guard_enabled: bool = Field(
        default=True,
        description="Enable LLM guard for ambiguous intent classification"
    )
    intent_embedding_kaso_threshold: float = Field(
        default=0.5,
        description="Embedding similarity threshold for Kaso-related queries (0.0-1.0)"
    )
    intent_embedding_off_topic_threshold: float = Field(
        default=0.3,
        description="Embedding similarity threshold for off-topic queries (0.0-1.0)"
    )

    # ════════════════════════════════════════
    # Database and Storage
    # ════════════════════════════════════════
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/chat_history.db",
        description="Database connection URL"
    )
    chroma_persist_dir: str = Field(
        default="./data/chroma_db",
        description="ChromaDB persistence directory"
    )
    chroma_collection_name: str = Field(
        default="kaso_knowledge",
        description="ChromaDB collection name"
    )

    # ════════════════════════════════════════
    # RAG Settings
    # ════════════════════════════════════════
    rag_top_k: int = Field(
        default=5,
        description="Number of documents to retrieve from vector DB"
    )
    rag_rerank_top_k: int = Field(
        default=5,
        description="Number of documents to keep after reranking"
    )
    rag_rerank_enabled: bool = Field(
        default=True,
        description="Enable reranking of retrieved documents"
    )
    chunk_size: int = Field(
        default=500,
        description="Chunk size for document splitting"
    )
    chunk_overlap: int = Field(
        default=50,
        description="Chunk overlap for document splitting"
    )

    # ════════════════════════════════════════
    # Token Management Settings (Solution 3)
    # ════════════════════════════════════════
    token_max_context: int = Field(
        default=5500,
        description="Maximum tokens for conversation history"
    )
    token_summarization_enabled: bool = Field(
        default=True,
        description="Enable conversation summarization for long histories"
    )

    # ════════════════════════════════════════
    # Conversation Settings (Solution 2)
    # ════════════════════════════════════════
    conv_reformulate_queries: bool = Field(
        default=True,
        description="Enable query reformulation for follow-up questions"
    )
    conv_max_history_for_reformulation: int = Field(
        default=3,
        description="Maximum number of previous turns to consider when reformulating queries"
    )
    conv_context_messages: int = Field(
        default=6,
        description="Maximum number of messages to include in conversation context for system prompt"
    )
    conv_max_history_for_context: int = Field(
        default=6,
        description="[DEPRECATED] Use conv_context_messages instead"
    )

    # ════════════════════════════════════════
    # Company Disambiguation Settings (Solution 5)
    # ════════════════════════════════════════
    company_disambiguation_enabled: bool = Field(
        default=True,
        description="Enable company disambiguation layer to prevent confusion with other Kaso companies"
    )
    company_disambiguation_confidence_threshold: float = Field(
        default=0.75,
        description="Confidence threshold for company disambiguation rejection (0.0-1.0)"
    )
    company_use_negative_embeddings: bool = Field(
        default=True,
        description="Use negative embedding examples for better disambiguation in intent classification"
    )
    company_llm_guard_enabled: bool = Field(
        default=True,
        description="Enable LLM-based disambiguation for ambiguous cases"
    )

    # ════════════════════════════════════════
    # Debug and Logging
    # ════════════════════════════════════════
    debug_mode: bool = Field(
        default=False,
        description="Enable debug logging"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> list:
        """Convert comma-separated CORS origins to list"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
