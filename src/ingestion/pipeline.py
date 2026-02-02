import hashlib
import pandas as pd
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import config
from src.utils.embeddings import EmbeddingService

"""

Text chunker for splitting long product descriptions.

Pipeline Stage: CSV → Processing → **Chunking** → Embeddings → Vector DB

For product descriptions that exceed the embedding model's optimal context,
splits text into overlapping chunks to maintain semantic coherence.

"""

class TextChunker:
    """
    Text chunker for splitting long product descriptions into overlapping chunks.
    
    This class splits text that exceeds the embedding model's optimal context length
    into smaller, overlapping chunks to maintain semantic coherence and improve
    embedding quality.
    
    Attributes:
        chunk_size: Maximum character count per chunk (default: 512)
        overlap: Number of characters to overlap between consecutive chunks (default: 50)
    """
    
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks of specified size.
        
        Creates overlapping text chunks to preserve context at chunk boundaries.
        If the text is shorter than chunk_size, returns it as a single chunk.
        
        Args:
            text: The input text to be chunked
            
        Returns:
            List of text chunks with configured overlap
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.overlap
        
        return chunks
    
    def chunk_product(self, product_text: str, product_id: str) -> List[Dict[str, Any]]:
        """
        Chunk a product's text and return with metadata.
        
        Args:
            product_text: Combined product text for embedding.
            product_id: The product's unique identifier.
            
        Returns:
            List of dicts with chunk text and chunk metadata.
        """
        chunks = self.chunk(product_text)
        return [
            {
                "text": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "product_id": product_id
            }
            for i, chunk in enumerate(chunks)
        ]


class ProductIngestionPipeline:
    """
    Pipeline for ingesting product catalog data into Qdrant.
    
    Pipeline Architecture:
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │  CSV File    │───▶│  Processing  │───▶│   Chunking   │───▶│  Embeddings  │
    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                       │
                                                                       ▼
                                                              ┌──────────────┐
                                                              │   Qdrant     │
                                                              │  Vector DB   │
                                                              └──────────────┘
    
    Features:
    - Loads products from CSV
    - Chunks long product descriptions for better embedding quality
    - Generates text embeddings using Sentence Transformers
    - Stores vectors with full metadata for filtering
    - Supports incremental updates (upsert by product_id, skips unchanged)
    """
    
    def __init__(
        self, 
        qdrant_host: str = None,
        qdrant_port: int = None,
        collection_name: str = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        self.qdrant_host = qdrant_host or config.QDRANT_HOST
        self.qdrant_port = qdrant_port or config.QDRANT_PORT
        self.collection_name = collection_name or config.COLLECTION_NAME
        
        self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        self.embedding_service = EmbeddingService()
        self.chunker = TextChunker(chunk_size=chunk_size, overlap=chunk_overlap)
        
        # Store last update timestamps and chunk info for incremental updates
        self._stored_timestamps: Dict[str, str] = {}
        self._stored_chunk_counts: Dict[str, int] = {}
    
    def _product_id_to_point_id(self, product_id: str) -> int:
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
    
    def _cleanup_old_chunks(self, product_ids: set) -> None:
        """
        Delete all existing chunk points for products whose chunk count has changed.
        
        When a product's description length changes significantly, the number of chunks
        it's split into may change. This method removes all old chunk points for such
        products before new ones are upserted, preventing orphaned chunk points.
        
        Args:
            product_ids: Set of product IDs that need their old chunks cleaned up
        """
        print(f"Cleaning up old chunks for {len(product_ids)} products with changed chunk counts...")
        
        # Delete points by filtering on product_id
        for product_id in product_ids:
            try:
                # Use scroll to find all points for this product
                offset = None
                points_to_delete = []
                
                while True:
                    result = self.client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="product_id",
                                    match=models.MatchValue(value=product_id)
                                )
                            ]
                        ),
                        limit=100,
                        offset=offset
                    )
                    points, offset = result
                    
                    if not points:
                        break
                    
                    points_to_delete.extend([point.id for point in points])
                    
                    if offset is None:
                        break
                
                # Delete the points
                if points_to_delete:
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=models.PointIdsList(points=points_to_delete)
                    )
                    print(f"  Deleted {len(points_to_delete)} old chunk points for product {product_id}")
                    
            except Exception as e:
                print(f"Warning: Could not cleanup chunks for product {product_id}: {e}")
    
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
    
    def load_products(self, csv_path: str = None) -> pd.DataFrame: # Load products from CSV file.
        csv_path = csv_path or config.PRODUCTS_CSV
        print(f"Loading products from: {csv_path}")
        
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} products.")
        
        return df
    
    def ingest(
        self, 
        csv_path: str = None, 
        recreate_collection: bool = False,
        batch_size: int = 32,
        skip_unchanged: bool = True
    ) -> Dict[str, Any]:
        """
        
        Pipeline: CSV → Processing → Chunking → Embeddings → Vector DB

        """
        # Load products
        df = self.load_products(csv_path)
        
        # Create collection
        self.create_collection(recreate=recreate_collection)
        
        # Load existing timestamps for incremental update detection
        if skip_unchanged and not recreate_collection:
            self._load_stored_timestamps()
        
        # Track statistics
        stats = {
            "new_products": 0,
            "updated_products": 0,
            "skipped_products": 0,
            "total_chunks": 0
        }
        
        # Filter products that need processing
        products_to_process = []
        for _, row in df.iterrows():
            product_id = str(row["product_id"])
            last_updated = str(row["last_updated"])
            
            # Check if product was updated
            if skip_unchanged and product_id in self._stored_timestamps:
                if self._stored_timestamps[product_id] == last_updated:
                    stats["skipped_products"] += 1
                    continue
                else:
                    stats["updated_products"] += 1
            else:
                stats["new_products"] += 1
            
            products_to_process.append(row)
        
        if not products_to_process:
            print("No products to update.")
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "status": "success",
                "collection_name": self.collection_name,
                "products_loaded": len(df),
                "vectors_count": collection_info.points_count,
                **stats
            }
        
        # Prepare texts for embedding with chunking
        print(f"Processing {len(products_to_process)} products ({stats['skipped_products']} skipped as unchanged)...")
        all_chunks = []
        chunk_to_product = []  # Maps chunk index to product row
        products_needing_cleanup = set()  # Track products whose chunk count changed
        
        for row in products_to_process:
            product_id = str(row["product_id"])
            product_text = self._prepare_text_for_embedding(row)
            chunks = self.chunker.chunk_product(product_text, product_id)
            
            # Check if chunk count changed (need to cleanup old points)
            new_chunk_count = len(chunks)
            if product_id in self._stored_chunk_counts:
                old_chunk_count = self._stored_chunk_counts[product_id]
                if old_chunk_count != new_chunk_count:
                    products_needing_cleanup.add(product_id)
                    print(f"Product {product_id}: chunk count changed from {old_chunk_count} to {new_chunk_count}")
            
            for chunk_info in chunks:
                all_chunks.append(chunk_info["text"])
                chunk_to_product.append((row, chunk_info))
        
        stats["total_chunks"] = len(all_chunks)
        print(f"Created {len(all_chunks)} chunks from {len(products_to_process)} products.")
        
        # Clean up old chunk points for products with changed chunk counts
        if products_needing_cleanup:
            self._cleanup_old_chunks(products_needing_cleanup)
        
        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.embedding_service.encode_batch(all_chunks, batch_size=batch_size)
        
        # Prepare points for upsert
        print("Preparing points for Qdrant...")
        points = []
        for idx, (row, chunk_info) in enumerate(chunk_to_product):
            # For products with single chunk, use product_id as point_id
            # For multi-chunk products, include chunk index
            if chunk_info["total_chunks"] == 1:
                point_id = self._product_id_to_point_id(str(row["product_id"]))
            else:
                # Create unique ID for each chunk
                chunk_id = f"{row['product_id']}_chunk_{chunk_info['chunk_index']}"
                point_id = self._product_id_to_point_id(chunk_id)
            
            # Prepare payload with chunk metadata
            payload = self._prepare_payload(row)
            payload["chunk_index"] = chunk_info["chunk_index"]
            payload["total_chunks"] = chunk_info["total_chunks"]
            
            point = PointStruct(
                id=point_id,
                vector=embeddings[idx],
                payload=payload
            )
            points.append(point)
        
        # Upsert points to Qdrant
        print(f"Upserting {len(points)} points to Qdrant...")
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        # Update stored chunk counts for processed products
        for row, chunk_info in chunk_to_product:
            product_id = str(row["product_id"])
            self._stored_chunk_counts[product_id] = chunk_info["total_chunks"]
            self._stored_timestamps[product_id] = str(row["last_updated"])
        
        # Verify ingestion
        collection_info = self.client.get_collection(self.collection_name)
        vectors_count = collection_info.points_count
        
        print(f"\n✅ Ingestion complete!")
        print(f"   Collection: {self.collection_name}")
        print(f"   Vectors count: {vectors_count}")
        print(f"   New products: {stats['new_products']}")
        print(f"   Updated products: {stats['updated_products']}")
        print(f"   Skipped (unchanged): {stats['skipped_products']}")
        print(f"   Total chunks created: {stats['total_chunks']}")
        
        return {
            "status": "success",
            "collection_name": self.collection_name,
            "products_loaded": len(df),
            "vectors_count": vectors_count,
            **stats
        }
    
    def _load_stored_timestamps(self) -> None:
        """
        Load existing product timestamps and chunk metadata from Qdrant.
        
        This tracks both the last_updated timestamp and the number of chunks
        per product to properly detect when re-chunking is needed (e.g., when
        a product description changes significantly in length).
        """
        try:
            # Scroll through all points to get their last_updated timestamps and chunk info
            offset = None
            self._stored_timestamps = {}
            self._stored_chunk_counts = {}
            
            while True:
                result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=["product_id", "last_updated", "total_chunks"]
                )
                points, offset = result
                
                if not points:
                    break
                
                for point in points:
                    if point.payload:
                        product_id = point.payload.get("product_id")
                        last_updated = point.payload.get("last_updated")
                        total_chunks = point.payload.get("total_chunks", 1)
                        
                        if product_id and last_updated:
                            if product_id not in self._stored_timestamps:
                                # First occurrence: store the values
                                self._stored_timestamps[product_id] = last_updated
                                self._stored_chunk_counts[product_id] = total_chunks
                            else:
                                # Validate consistency for multi-chunk products
                                # Use the maximum chunk count if there's inconsistency
                                if total_chunks != self._stored_chunk_counts[product_id]:
                                    print(f"Warning: Inconsistent chunk count for product {product_id}. "
                                          f"Found {total_chunks} and {self._stored_chunk_counts[product_id]}. "
                                          f"Using maximum value.")
                                    self._stored_chunk_counts[product_id] = max(
                                        total_chunks, 
                                        self._stored_chunk_counts[product_id]
                                    )
                
                if offset is None:
                    break
            
            print(f"Loaded {len(self._stored_timestamps)} existing product timestamps.")
        except Exception as e:
            print(f"Warning: Could not load existing timestamps: {e}")
            self._stored_timestamps = {}
            self._stored_chunk_counts = {}
    
    def search( # Search similar products
        self, 
        query: str, 
        limit: int = 5, # Maximum number of results to return.
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
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
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=query_filter
        )
        
        # Format results
        return [
            {
                "score": hit.score,
                **hit.payload
            }
            for hit in results.points
        ]


def main():
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
