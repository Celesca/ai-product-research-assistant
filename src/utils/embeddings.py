"""
Embedding service using Sentence Transformers.
Generates vector embeddings for text using local models (no API key required).
"""
from typing import List, Union
from sentence_transformers import SentenceTransformer

from .config import config


class EmbeddingService:
    """
    Service for generating text embeddings using Sentence Transformers.
    
    Uses all-MiniLM-L6-v2 by default, which provides a good balance of
    speed and quality with 384-dimensional embeddings.
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the Sentence Transformer model to use.
                       Defaults to config.EMBEDDING_MODEL.
        """
        self.model_name = model_name or config.EMBEDDING_MODEL
        self._model = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model."""
        if self._model is None:
            print(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def encode(self, text: Union[str, List[str]]) -> List[float]:
        """
        Generate embedding(s) for the given text.
        
        Args:
            text: Single text string or list of strings to encode.
            
        Returns:
            If single text: List of floats representing the embedding.
            If list of texts: List of embeddings.
        """
        embeddings = self.model.encode(text, convert_to_numpy=True)
        
        if isinstance(text, str):
            return embeddings.tolist()
        return [emb.tolist() for emb in embeddings]
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts efficiently.
        
        Args:
            texts: List of texts to encode.
            batch_size: Number of texts to encode at once.
            
        Returns:
            List of embeddings, one for each input text.
        """
        embeddings = self.model.encode(
            texts, 
            batch_size=batch_size, 
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return [emb.tolist() for emb in embeddings]
    
    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return config.EMBEDDING_DIMENSION


# Singleton instance for convenience
embedding_service = EmbeddingService()
