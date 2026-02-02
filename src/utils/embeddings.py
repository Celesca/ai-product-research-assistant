from typing import List, Union
from sentence_transformers import SentenceTransformer

from .config import config


class EmbeddingService:
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.EMBEDDING_MODEL
        self._model = None
    
    @property
    def model(self) -> SentenceTransformer:
        # Lazy load the model.
        if self._model is None:
            print(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def encode(self, text: Union[str, List[str]]) -> List[float]:

        embeddings = self.model.encode(text, convert_to_numpy=True)
        
        if isinstance(text, str):
            return embeddings.tolist()
        return [emb.tolist() for emb in embeddings]
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:

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
