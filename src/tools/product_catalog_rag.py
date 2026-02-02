"""
Product Catalog RAG Tool

This tool retrieves information from the product catalog using
vector similarity search (RAG - Retrieval Augmented Generation).
"""
from typing import Dict, Any, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import settings
from src.utils.embeddings import EmbeddingService


class ProductCatalogRAGTool:
    """
    RAG-based tool for searching the product catalog.
    
    Uses Qdrant vector database for semantic search over product descriptions,
    with metadata filtering support for category, brand, price range, etc.
    """
    
    name: str = "product_catalog_search"
    description: str = """
    Search the internal product catalog to find products based on natural language queries.
    Use this tool when you need to:
    - Find products by description, features, or specifications
    - Search for products in specific categories or from specific brands
    - Look up products in stock
    - Find products within a price range
    - Get product details like price, rating, stock quantity
    
    The tool returns matching products with their full details including:
    product_id, name, category, brand, description, price, cost, stock, sales, rating.
    """
    
    def __init__(
        self,
        qdrant_host: str = None,
        qdrant_port: int = None,
        collection_name: str = None
    ):
        """
        Initialize the Product Catalog RAG tool.
        
        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            collection_name: Name of the Qdrant collection
        """
        self.qdrant_host = qdrant_host or settings.QDRANT_HOST
        self.qdrant_port = qdrant_port or settings.QDRANT_PORT
        self.collection_name = collection_name or settings.COLLECTION_NAME
        
        self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        self.embedding_service = EmbeddingService()
    
    def _build_filters(
        self,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        in_stock: Optional[bool] = None
    ) -> Optional[models.Filter]:
        """
        Build Qdrant filter conditions from parameters.
        
        Args:
            category: Filter by product category
            brand: Filter by brand name
            min_price: Minimum price
            max_price: Maximum price
            min_rating: Minimum average rating
            in_stock: If True, only return products with stock > 0
            
        Returns:
            Qdrant Filter object or None if no filters specified
        """
        must_conditions = []
        
        if category:
            must_conditions.append(
                models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value=category)
                )
            )
        
        if brand:
            must_conditions.append(
                models.FieldCondition(
                    key="brand",
                    match=models.MatchValue(value=brand)
                )
            )
        
        # Price range filter
        if min_price is not None or max_price is not None:
            range_params = {}
            if min_price is not None:
                range_params["gte"] = min_price
            if max_price is not None:
                range_params["lte"] = max_price
            must_conditions.append(
                models.FieldCondition(
                    key="current_price",
                    range=models.Range(**range_params)
                )
            )
        
        # Rating filter
        if min_rating is not None:
            must_conditions.append(
                models.FieldCondition(
                    key="average_rating",
                    range=models.Range(gte=min_rating)
                )
            )
        
        # Stock filter
        if in_stock:
            must_conditions.append(
                models.FieldCondition(
                    key="stock_quantity",
                    range=models.Range(gt=0)
                )
            )
        
        if must_conditions:
            return models.Filter(must=must_conditions)
        return None
    
    def search(
        self,
        query: str,
        limit: int = 5,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        in_stock: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Search for products in the catalog.
        
        Args:
            query: Natural language search query
            limit: Maximum number of results to return (default: 5)
            category: Filter by category
            brand: Filter by brand
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_rating: Minimum rating filter
            in_stock: If True, only return products in stock
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            # Generate query embedding
            query_vector = self.embedding_service.encode(query)
            
            # Build filters
            query_filter = self._build_filters(
                category=category,
                brand=brand,
                min_price=min_price,
                max_price=max_price,
                min_rating=min_rating,
                in_stock=in_stock
            )
            
            # Execute search
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                query_filter=query_filter
            )
            
            # Format results
            products = []
            for hit in results.points:
                product = {
                    "score": round(hit.score, 4),
                    **hit.payload
                }
                # Calculate margin for each product
                if "current_price" in product and "cost" in product:
                    product["margin_percentage"] = round(
                        ((product["current_price"] - product["cost"]) / product["current_price"]) * 100, 
                        2
                    )
                products.append(product)
            
            return {
                "status": "success",
                "query": query,
                "filters_applied": {
                    "category": category,
                    "brand": brand,
                    "min_price": min_price,
                    "max_price": max_price,
                    "min_rating": min_rating,
                    "in_stock": in_stock
                },
                "total_results": len(products),
                "products": products,
                "confidence": max([p["score"] for p in products]) if products else 0.0
            }
            
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "products": [],
                "confidence": 0.0
            }
    
    def get_product_by_id(self, product_id: str) -> Dict[str, Any]:
        """
        Get a specific product by its ID.
        
        Args:
            product_id: The product ID (e.g., "PROD-001")
            
        Returns:
            Dictionary with product details or error
        """
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="product_id",
                            match=models.MatchValue(value=product_id)
                        )
                    ]
                ),
                limit=1
            )
            
            if results[0]:
                product = results[0][0].payload
                # Calculate margin
                if "current_price" in product and "cost" in product:
                    product["margin_percentage"] = round(
                        ((product["current_price"] - product["cost"]) / product["current_price"]) * 100, 
                        2
                    )
                return {
                    "status": "success",
                    "product": product
                }
            else:
                return {
                    "status": "not_found",
                    "error": f"Product with ID '{product_id}' not found"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_products_by_category(self, category: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get all products in a specific category.
        
        Args:
            category: The category name
            limit: Maximum number of products to return
            
        Returns:
            Dictionary with products in the category
        """
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="category",
                            match=models.MatchValue(value=category)
                        )
                    ]
                ),
                limit=limit
            )
            
            products = []
            for point in results[0]:
                product = point.payload
                if "current_price" in product and "cost" in product:
                    product["margin_percentage"] = round(
                        ((product["current_price"] - product["cost"]) / product["current_price"]) * 100, 
                        2
                    )
                products.append(product)
            
            return {
                "status": "success",
                "category": category,
                "total_products": len(products),
                "products": products
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "products": []
            }
    
    def get_products_by_brand(self, brand: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get all products from a specific brand.
        
        Args:
            brand: The brand name
            limit: Maximum number of products to return
            
        Returns:
            Dictionary with products from the brand
        """
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="brand",
                            match=models.MatchValue(value=brand)
                        )
                    ]
                ),
                limit=limit
            )
            
            products = []
            for point in results[0]:
                product = point.payload
                if "current_price" in product and "cost" in product:
                    product["margin_percentage"] = round(
                        ((product["current_price"] - product["cost"]) / product["current_price"]) * 100, 
                        2
                    )
                products.append(product)
            
            return {
                "status": "success",
                "brand": brand,
                "total_products": len(products),
                "products": products
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "products": []
            }
    
    def __call__(
        self,
        query: str,
        limit: int = 5,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        in_stock: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Make the tool callable directly."""
        return self.search(
            query=query,
            limit=limit,
            category=category,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            min_rating=min_rating,
            in_stock=in_stock
        )


# Singleton instance
product_catalog_tool = ProductCatalogRAGTool()
