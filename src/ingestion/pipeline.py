"""
Data Ingestion Pipeline for Products Catalog.

This module handles loading products from CSV, generating embeddings,
and storing them in Qdrant vector database with full metadata for filtering.
"""
import hashlib
import pandas as pd
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import config
from src.embeddings import EmbeddingService


class ProductIngestionPipeline:
    """
    Pipeline for ingesting product catalog data into Qdrant.
    
    Features:
    - Loads products from CSV
    - Generates text embeddings from product descriptions
    - Stores vectors with full metadata for filtering
    - Supports incremental updates (upsert by product_id)
    """
    
    def __init__(
        self, 
        qdrant_host: str = None,
        qdrant_port: int = None,
        collection_name: str = None
    ):
        """
        Initialize the ingestion pipeline.
        
        Args:
            qdrant_host: Qdrant server host (default: from config)
            qdrant_port: Qdrant server port (default: from config)
            collection_name: Name of the collection to use (default: from config)
        """
        self.qdrant_host = qdrant_host or config.QDRANT_HOST
        self.qdrant_port = qdrant_port or config.QDRANT_PORT
        self.collection_name = collection_name or config.COLLECTION_NAME
        
        self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        self.embedding_service = EmbeddingService()
    
    def _product_id_to_point_id(self, product_id: str) -> int:
        """
        Convert product_id string to a numeric point ID.
        
        Uses hash to ensure consistent IDs across runs, enabling upserts.
        """
        # Extract numeric part from PROD-XXX format
        if product_id.startswith("PROD-"):
            try:
                return int(product_id.replace("PROD-", ""))
            except ValueError:
                pass
        
        # Fallback: use hash
        hash_bytes = hashlib.md5(product_id.encode()).digest()
        return int.from_bytes(hash_bytes[:8], byteorder='big') % (2**63)
    
    def _prepare_text_for_embedding(self, row: pd.Series) -> str:
        """
        Prepare product text for embedding generation.
        
        Combines relevant fields into a searchable text representation.
        """
        return (
            f"{row['product_name']} - {row['brand']} - {row['category']}: "
            f"{row['description']}"
        )
    
    def _prepare_payload(self, row: pd.Series) -> Dict[str, Any]:
        """
        Prepare metadata payload for a product.
        
        Includes all fields for filtering and display.
        """
        return {
            "product_id": str(row["product_id"]),
            "product_name": str(row["product_name"]),
            "category": str(row["category"]),
            "brand": str(row["brand"]),
            "description": str(row["description"]),
            "current_price": float(row["current_price"]),
            "cost": float(row["cost"]),
            "stock_quantity": int(row["stock_quantity"]),
            "monthly_sales": int(row["monthly_sales"]),
            "average_rating": float(row["average_rating"]),
            "review_count": int(row["review_count"]),
            "supplier": str(row["supplier"]),
            "last_updated": str(row["last_updated"]),
        }
    
    def create_collection(self, recreate: bool = False) -> None:
        """
        Create the Qdrant collection if it doesn't exist.
        
        Args:
            recreate: If True, delete and recreate the collection.
        """
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name in collection_names:
            if recreate:
                print(f"Deleting existing collection: {self.collection_name}")
                self.client.delete_collection(self.collection_name)
            else:
                print(f"Collection '{self.collection_name}' already exists.")
                return
        
        print(f"Creating collection: {self.collection_name}")
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_service.dimension,
                distance=Distance.COSINE
            )
        )
        
        # Create payload indexes for filtering
        print("Creating payload indexes for filtering...")
        
        # Keyword indexes for exact matching
        for field in ["category", "brand", "supplier", "product_id"]:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        
        # Numeric indexes for range filtering
        for field in ["current_price", "cost", "average_rating"]:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.FLOAT
            )
        
        for field in ["stock_quantity", "monthly_sales", "review_count"]:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.INTEGER
            )
        
        print("Collection created with indexes.")
    
    def load_products(self, csv_path: str = None) -> pd.DataFrame:
        """
        Load products from CSV file.
        
        Args:
            csv_path: Path to the CSV file (default: from config)
            
        Returns:
            DataFrame with product data.
        """
        csv_path = csv_path or config.PRODUCTS_CSV
        print(f"Loading products from: {csv_path}")
        
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} products.")
        
        return df
    
    def ingest(
        self, 
        csv_path: str = None, 
        recreate_collection: bool = False,
        batch_size: int = 32
    ) -> Dict[str, Any]:
        """
        Run the full ingestion pipeline.
        
        Args:
            csv_path: Path to the products CSV file.
            recreate_collection: If True, recreate the collection from scratch.
            batch_size: Number of products to process at once.
            
        Returns:
            Dictionary with ingestion statistics.
        """
        # Load products
        df = self.load_products(csv_path)
        
        # Create collection
        self.create_collection(recreate=recreate_collection)
        
        # Prepare texts for embedding
        print("Preparing texts for embedding...")
        texts = [self._prepare_text_for_embedding(row) for _, row in df.iterrows()]
        
        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.embedding_service.encode_batch(texts, batch_size=batch_size)
        
        # Prepare points for upsert
        print("Preparing points for Qdrant...")
        points = []
        for idx, (_, row) in enumerate(df.iterrows()):
            point = PointStruct(
                id=self._product_id_to_point_id(row["product_id"]),
                vector=embeddings[idx],
                payload=self._prepare_payload(row)
            )
            points.append(point)
        
        # Upsert points to Qdrant
        print(f"Upserting {len(points)} points to Qdrant...")
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        # Verify ingestion
        collection_info = self.client.get_collection(self.collection_name)
        vectors_count = collection_info.vectors_count
        
        print(f"\n✅ Ingestion complete!")
        print(f"   Collection: {self.collection_name}")
        print(f"   Vectors count: {vectors_count}")
        
        return {
            "status": "success",
            "collection_name": self.collection_name,
            "products_loaded": len(df),
            "vectors_count": vectors_count
        }
    
    def search(
        self, 
        query: str, 
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for products similar to the query.
        
        Args:
            query: Search query text.
            limit: Maximum number of results to return.
            filters: Optional Qdrant filter conditions.
            
        Returns:
            List of matching products with scores.
        """
        # Generate query embedding
        query_vector = self.embedding_service.encode(query)
        
        # Build filter if provided
        query_filter = None
        if filters:
            must_conditions = []
            for field, value in filters.items():
                if isinstance(value, dict):
                    # Range filter
                    if "gte" in value or "lte" in value:
                        must_conditions.append(
                            models.FieldCondition(
                                key=field,
                                range=models.Range(**value)
                            )
                        )
                else:
                    # Exact match
                    must_conditions.append(
                        models.FieldCondition(
                            key=field,
                            match=models.MatchValue(value=value)
                        )
                    )
            
            if must_conditions:
                query_filter = models.Filter(must=must_conditions)
        
        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter
        )
        
        # Format results
        return [
            {
                "score": hit.score,
                **hit.payload
            }
            for hit in results
        ]


def main():
    """Run the ingestion pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest products into Qdrant")
    parser.add_argument(
        "--csv", 
        type=str, 
        default=None,
        help="Path to products CSV file"
    )
    parser.add_argument(
        "--recreate", 
        action="store_true",
        help="Recreate collection from scratch"
    )
    parser.add_argument(
        "--test-search",
        action="store_true",
        help="Run a test search after ingestion"
    )
    
    args = parser.parse_args()
    
    # Run ingestion
    pipeline = ProductIngestionPipeline()
    result = pipeline.ingest(
        csv_path=args.csv,
        recreate_collection=args.recreate
    )
    
    print(f"\nIngestion result: {result}")
    
    # Optional: Test search
    if args.test_search:
        print("\n--- Test Search ---")
        test_queries = [
            "wireless headphones",
            "fitness equipment",
            "kitchen appliances"
        ]
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            results = pipeline.search(query, limit=3)
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r['product_name']} ({r['brand']}) - Score: {r['score']:.4f}")


if __name__ == "__main__":
    main()
