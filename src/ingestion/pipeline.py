import hashlib
import logging
import os
import sys

import pandas as pd
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import config
from src.utils.embeddings import EmbeddingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TextChunker:

    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start = end - self.overlap

        return chunks

    def chunk_product(self, product_text: str, product_id: str) -> List[Dict[str, Any]]:
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

    def _product_id_to_point_id(self, product_id: str) -> int:
        if product_id.startswith("PROD-"):
            try:
                return int(product_id.replace("PROD-", ""))
            except ValueError:
                pass

        hash_bytes = hashlib.md5(product_id.encode()).digest()
        return int.from_bytes(hash_bytes[:8], byteorder='big') % (2**63)

    def _prepare_text_for_embedding(self, row: pd.Series) -> str:
        return (
            f"{row['product_name']} - {row['brand']} - {row['category']}: "
            f"{row['description']}"
        )

    def _prepare_payload(self, row: pd.Series) -> Dict[str, Any]:
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
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name in collection_names:
            if recreate:
                logger.info(f"Deleting existing collection: {self.collection_name}")
                self.client.delete_collection(self.collection_name)
            else:
                logger.info(f"Collection '{self.collection_name}' already exists.")
                return

        logger.info(f"Creating collection: {self.collection_name}")
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_service.dimension,
                distance=Distance.COSINE
            )
        )

        logger.info("Creating payload indexes for filtering...")

        for field in ["category", "brand", "supplier", "product_id"]:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD
            )

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

        logger.info("Collection created with indexes.")

    def load_products(self, csv_path: str = None) -> pd.DataFrame:
        csv_path = csv_path or config.PRODUCTS_CSV
        logger.info(f"Loading products from: {csv_path}")

        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} products.")

        return df

    def ingest(
        self,
        csv_path: str = None,
        recreate_collection: bool = False,
        batch_size: int = 32
    ) -> Dict[str, Any]:
        df = self.load_products(csv_path)
        self.create_collection(recreate=recreate_collection)

        logger.info(f"Processing {len(df)} products...")
        all_chunks = []
        chunk_to_product = []

        for _, row in df.iterrows():
            product_text = self._prepare_text_for_embedding(row)
            product_id = str(row["product_id"])
            chunks = self.chunker.chunk_product(product_text, product_id)

            for chunk_info in chunks:
                all_chunks.append(chunk_info["text"])
                chunk_to_product.append((row, chunk_info))

        logger.info(f"Created {len(all_chunks)} chunks from {len(df)} products.")

        logger.info("Generating embeddings...")
        embeddings = self.embedding_service.encode_batch(all_chunks, batch_size=batch_size)

        logger.info("Preparing points for Qdrant...")
        points = []
        for idx, (row, chunk_info) in enumerate(chunk_to_product):
            if chunk_info["total_chunks"] == 1:
                point_id = self._product_id_to_point_id(str(row["product_id"]))
            else:
                chunk_id = f"{row['product_id']}_chunk_{chunk_info['chunk_index']}"
                point_id = self._product_id_to_point_id(chunk_id)

            payload = self._prepare_payload(row)
            payload["chunk_index"] = chunk_info["chunk_index"]
            payload["total_chunks"] = chunk_info["total_chunks"]

            points.append(PointStruct(
                id=point_id,
                vector=embeddings[idx],
                payload=payload
            ))

        logger.info(f"Upserting {len(points)} points to Qdrant...")
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        collection_info = self.client.get_collection(self.collection_name)
        vectors_count = collection_info.points_count

        logger.info(f"✅ Ingestion complete!")
        logger.info(f"  - Collection: {self.collection_name}")
        logger.info(f"  - Vectors count: {vectors_count}")
        logger.info(f"  - Total chunks: {len(all_chunks)}")

        return {
            "status": "success",
            "collection_name": self.collection_name,
            "products_loaded": len(df),
            "vectors_count": vectors_count,
            "total_chunks": len(all_chunks)
        }

    def search(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        query_vector = self.embedding_service.encode(query)

        query_filter = None
        if filters:
            must_conditions = []
            for field, value in filters.items():
                if isinstance(value, dict):
                    if "gte" in value or "lte" in value:
                        must_conditions.append(
                            models.FieldCondition(
                                key=field,
                                range=models.Range(**value)
                            )
                        )
                else:
                    must_conditions.append(
                        models.FieldCondition(
                            key=field,
                            match=models.MatchValue(value=value)
                        )
                    )

            if must_conditions:
                query_filter = models.Filter(must=must_conditions)

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=query_filter
        )

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
    parser.add_argument("--csv", type=str, default=None, help="Path to products CSV file")
    parser.add_argument("--recreate", action="store_true", help="Recreate collection from scratch")

    args = parser.parse_args()

    pipeline = ProductIngestionPipeline()
    result = pipeline.ingest(
        csv_path=args.csv,
        recreate_collection=args.recreate
    )

    logger.info(f"Ingestion result: {result}")


if __name__ == "__main__":
    main()
