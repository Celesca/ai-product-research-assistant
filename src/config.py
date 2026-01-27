"""
Configuration settings for the AI Product Research Assistant.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration settings."""
    
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
        os.path.dirname(os.path.dirname(__file__)), 
        "data"
    )
    PRODUCTS_CSV: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "products_catalog.csv"
    )


config = Config()
