"""
Price Analysis Tool

This tool provides deterministic price analysis and margin calculations.
All calculations are done programmatically, not by the LLM.
"""
from typing import Dict, Any, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
import statistics

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import settings


def calculate_margin(price: float, cost: float) -> float:
    """
    Calculate profit margin percentage.
    
    Formula: ((price - cost) / price) * 100
    
    Args:
        price: Selling price
        cost: Cost price
        
    Returns:
        Margin percentage (0-100)
    """
    if price <= 0:
        return 0.0
    return ((price - cost) / price) * 100


def calculate_profit(price: float, cost: float) -> float:
    """
    Calculate absolute profit.
    
    Args:
        price: Selling price
        cost: Cost price
        
    Returns:
        Absolute profit amount
    """
    return price - cost


def calculate_markup(price: float, cost: float) -> float:
    """
    Calculate markup percentage.
    
    Formula: ((price - cost) / cost) * 100
    
    Args:
        price: Selling price
        cost: Cost price
        
    Returns:
        Markup percentage
    """
    if cost <= 0:
        return 0.0
    return ((price - cost) / cost) * 100


class PriceAnalysisTool:
    
    name: str = "price_analysis"
    description: str = """
    Analyze product pricing and calculate profit margins.
    Use this tool when you need to:
    - Calculate profit margins for products
    - Find products with low or high margins
    - Analyze pricing by category or brand
    - Get pricing recommendations based on margins
    - Compare costs and pricing across products
    
    This tool uses deterministic calculations:
    - Margin = ((price - cost) / price) × 100
    - Profit = price - cost
    - Markup = ((price - cost) / cost) × 100
    """
    
    def __init__(
        self,
        qdrant_host: str = None,
        qdrant_port: int = None,
        collection_name: str = None
    ):
        self.qdrant_host = qdrant_host or settings.QDRANT_HOST
        self.qdrant_port = qdrant_port or settings.QDRANT_PORT
        self.collection_name = collection_name or settings.COLLECTION_NAME
        
        self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
    
    def _get_all_products(self, limit: int = 200) -> List[Dict[str, Any]]:
        results = self.client.scroll(
            collection_name=self.collection_name,
            limit=limit
        )
        
        products = []
        for point in results[0]:
            product = point.payload
            # Calculate financial metrics
            price = product.get("current_price", 0)
            cost = product.get("cost", 0)
            product["margin_percentage"] = round(calculate_margin(price, cost), 2)
            product["profit"] = round(calculate_profit(price, cost), 2)
            product["markup_percentage"] = round(calculate_markup(price, cost), 2)
            products.append(product)
        
        return products
    
    def _get_products_by_category(self, category: str, limit: int = 100) -> List[Dict[str, Any]]:
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
            price = product.get("current_price", 0)
            cost = product.get("cost", 0)
            product["margin_percentage"] = round(calculate_margin(price, cost), 2)
            product["profit"] = round(calculate_profit(price, cost), 2)
            product["markup_percentage"] = round(calculate_markup(price, cost), 2)
            products.append(product)
        
        return products
    
    def _get_products_by_brand(self, brand: str, limit: int = 100) -> List[Dict[str, Any]]:
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
            price = product.get("current_price", 0)
            cost = product.get("cost", 0)
            product["margin_percentage"] = round(calculate_margin(price, cost), 2)
            product["profit"] = round(calculate_profit(price, cost), 2)
            product["markup_percentage"] = round(calculate_markup(price, cost), 2)
            products.append(product)
        
        return products
    
    def get_products_with_lowest_margins(
        self, 
        limit: int = 10, # Number of products to return
        category: Optional[str] = None, # Filter by category (optional)
        brand: Optional[str] = None # Filter by brand (optional)
    ) -> Dict[str, Any]:
        try:
            if category:
                products = self._get_products_by_category(category)
            elif brand:
                products = self._get_products_by_brand(brand)
            else:
                products = self._get_all_products()
            
            # Sort by margin ascending
            sorted_products = sorted(products, key=lambda x: x["margin_percentage"])
            low_margin_products = sorted_products[:limit]
            
            # Calculate statistics
            all_margins = [p["margin_percentage"] for p in products]
            
            return {
                "status": "success",
                "analysis_type": "lowest_margins",
                "filters": {"category": category, "brand": brand},
                "total_products_analyzed": len(products),
                "statistics": {
                    "min_margin": round(min(all_margins), 2),
                    "max_margin": round(max(all_margins), 2),
                    "average_margin": round(statistics.mean(all_margins), 2),
                    "median_margin": round(statistics.median(all_margins), 2)
                },
                "products": [
                    {
                        "product_id": p["product_id"],
                        "product_name": p["product_name"],
                        "brand": p["brand"],
                        "category": p["category"],
                        "current_price": p["current_price"],
                        "cost": p["cost"],
                        "margin_percentage": p["margin_percentage"],
                        "profit": p["profit"]
                    }
                    for p in low_margin_products
                ]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "products": []
            }
    
    def get_products_with_highest_margins(
        self, 
        limit: int = 10,
        category: Optional[str] = None,
        brand: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            if category:
                products = self._get_products_by_category(category)
            elif brand:
                products = self._get_products_by_brand(brand)
            else:
                products = self._get_all_products()
            
            # Sort by margin descending
            sorted_products = sorted(products, key=lambda x: x["margin_percentage"], reverse=True)
            high_margin_products = sorted_products[:limit]
            
            # Calculate statistics
            all_margins = [p["margin_percentage"] for p in products]
            
            return {
                "status": "success",
                "analysis_type": "highest_margins",
                "filters": {"category": category, "brand": brand},
                "total_products_analyzed": len(products),
                "statistics": {
                    "min_margin": round(min(all_margins), 2),
                    "max_margin": round(max(all_margins), 2),
                    "average_margin": round(statistics.mean(all_margins), 2),
                    "median_margin": round(statistics.median(all_margins), 2)
                },
                "products": [
                    {
                        "product_id": p["product_id"],
                        "product_name": p["product_name"],
                        "brand": p["brand"],
                        "category": p["category"],
                        "current_price": p["current_price"],
                        "cost": p["cost"],
                        "margin_percentage": p["margin_percentage"],
                        "profit": p["profit"]
                    }
                    for p in high_margin_products
                ]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "products": []
            }
    
    def get_products_below_margin_threshold(
        self, 
        threshold: float = 40.0,
        category: Optional[str] = None,
        brand: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            if category:
                products = self._get_products_by_category(category)
            elif brand:
                products = self._get_products_by_brand(brand)
            else:
                products = self._get_all_products()
            
            # Filter products below threshold
            below_threshold = [p for p in products if p["margin_percentage"] < threshold]
            below_threshold = sorted(below_threshold, key=lambda x: x["margin_percentage"])
            
            # Calculate category-wise breakdown
            category_breakdown = {}
            for p in below_threshold:
                cat = p["category"]
                if cat not in category_breakdown:
                    category_breakdown[cat] = {"count": 0, "avg_margin": []}
                category_breakdown[cat]["count"] += 1
                category_breakdown[cat]["avg_margin"].append(p["margin_percentage"])
            
            for cat in category_breakdown:
                margins = category_breakdown[cat]["avg_margin"]
                category_breakdown[cat]["avg_margin"] = round(statistics.mean(margins), 2)
            
            return {
                "status": "success",
                "analysis_type": "below_threshold",
                "threshold": threshold,
                "filters": {"category": category, "brand": brand},
                "total_products_analyzed": len(products),
                "products_below_threshold": len(below_threshold),
                "percentage_below_threshold": round(len(below_threshold) / len(products) * 100, 2) if products else 0,
                "category_breakdown": category_breakdown,
                "products": [
                    {
                        "product_id": p["product_id"],
                        "product_name": p["product_name"],
                        "brand": p["brand"],
                        "category": p["category"],
                        "current_price": p["current_price"],
                        "cost": p["cost"],
                        "margin_percentage": p["margin_percentage"],
                        "profit": p["profit"],
                        "suggested_price_for_40_margin": round(p["cost"] / (1 - 0.40), 2)
                    }
                    for p in below_threshold
                ]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "products": []
            }
    
    def get_category_margin_analysis(self, category: str) -> Dict[str, Any]:
        try:
            products = self._get_products_by_category(category)
            
            if not products:
                return {
                    "status": "not_found",
                    "error": f"No products found in category: {category}"
                }
            
            margins = [p["margin_percentage"] for p in products]
            profits = [p["profit"] for p in products]
            prices = [p["current_price"] for p in products]
            
            return {
                "status": "success",
                "analysis_type": "category_analysis",
                "category": category,
                "total_products": len(products),
                "margin_statistics": {
                    "min": round(min(margins), 2),
                    "max": round(max(margins), 2),
                    "average": round(statistics.mean(margins), 2),
                    "median": round(statistics.median(margins), 2),
                    "std_dev": round(statistics.stdev(margins), 2) if len(margins) > 1 else 0
                },
                "profit_statistics": {
                    "min": round(min(profits), 2),
                    "max": round(max(profits), 2),
                    "average": round(statistics.mean(profits), 2),
                    "total": round(sum(profits), 2)
                },
                "price_statistics": {
                    "min": round(min(prices), 2),
                    "max": round(max(prices), 2),
                    "average": round(statistics.mean(prices), 2)
                },
                "products": sorted(
                    [
                        {
                            "product_id": p["product_id"],
                            "product_name": p["product_name"],
                            "brand": p["brand"],
                            "current_price": p["current_price"],
                            "cost": p["cost"],
                            "margin_percentage": p["margin_percentage"],
                            "profit": p["profit"]
                        }
                        for p in products
                    ],
                    key=lambda x: x["margin_percentage"],
                    reverse=True
                )
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_brand_margin_analysis(self, brand: str) -> Dict[str, Any]:
        try:
            products = self._get_products_by_brand(brand)
            
            if not products:
                return {
                    "status": "not_found",
                    "error": f"No products found for brand: {brand}"
                }
            
            margins = [p["margin_percentage"] for p in products]
            profits = [p["profit"] for p in products]
            
            return {
                "status": "success",
                "analysis_type": "brand_analysis",
                "brand": brand,
                "total_products": len(products),
                "margin_statistics": {
                    "min": round(min(margins), 2),
                    "max": round(max(margins), 2),
                    "average": round(statistics.mean(margins), 2),
                    "median": round(statistics.median(margins), 2)
                },
                "profit_statistics": {
                    "min": round(min(profits), 2),
                    "max": round(max(profits), 2),
                    "average": round(statistics.mean(profits), 2),
                    "total": round(sum(profits), 2)
                },
                "products": sorted(
                    [
                        {
                            "product_id": p["product_id"],
                            "product_name": p["product_name"],
                            "category": p["category"],
                            "current_price": p["current_price"],
                            "cost": p["cost"],
                            "margin_percentage": p["margin_percentage"],
                            "profit": p["profit"]
                        }
                        for p in products
                    ],
                    key=lambda x: x["margin_percentage"],
                    reverse=True
                )
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def analyze(
        self,
        analysis_type: str = "lowest_margins",
        category: Optional[str] = None,
        brand: Optional[str] = None,
        threshold: float = 40.0,
        limit: int = 10
    ) -> Dict[str, Any]:
        if analysis_type == "lowest_margins":
            return self.get_products_with_lowest_margins(limit, category, brand)
        elif analysis_type == "highest_margins":
            return self.get_products_with_highest_margins(limit, category, brand)
        elif analysis_type == "below_threshold":
            return self.get_products_below_margin_threshold(threshold, category, brand)
        elif analysis_type == "category_analysis" and category:
            return self.get_category_margin_analysis(category)
        elif analysis_type == "brand_analysis" and brand:
            return self.get_brand_margin_analysis(brand)
        else:
            return self.get_products_with_lowest_margins(limit, category, brand)
    
    def __call__(
        self,
        analysis_type: str = "lowest_margins",
        category: Optional[str] = None,
        brand: Optional[str] = None,
        threshold: float = 40.0,
        limit: int = 10
    ) -> Dict[str, Any]:
        return self.analyze(
            analysis_type=analysis_type,
            category=category,
            brand=brand,
            threshold=threshold,
            limit=limit
        )


# Singleton instance
price_analysis_tool = PriceAnalysisTool()
