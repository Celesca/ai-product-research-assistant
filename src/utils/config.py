"""
Configuration settings for the AI Product Research Assistant.
"""
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application configuration settings using Pydantic."""
    
    # Qdrant Configuration
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    COLLECTION_NAME: str = "products"
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:4b"
    
    # Embedding Model Configuration
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384  # Dimension for all-MiniLM-L6-v2
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./data/app.db"
    
    # Web Search Configuration (optional - for real API)
    SERPER_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    
    # Data Paths
    @property
    def DATA_DIR(self) -> str:
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "data"
        )
    
    @property
    def PRODUCTS_CSV(self) -> str:
        return os.path.join(self.DATA_DIR, "products_catalog.csv")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Legacy Config class for backward compatibility
class Config:
    """Legacy configuration settings (for backward compatibility)."""
    
    # Qdrant Configuration
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "products")
    
    # Embedding Model Configuration
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", 
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    EMBEDDING_DIMENSION: int = 384  # Dimension for all-MiniLM-L6-v2
    
    # Data Paths
    DATA_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
        "data"
    )
    PRODUCTS_CSV: str = os.path.join(DATA_DIR, "products_catalog.csv")


# Singleton instances
settings = Settings()
config = Config()
