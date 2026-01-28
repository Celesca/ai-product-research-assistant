"""
Web Search Tool

This tool provides web search capabilities for finding market trends,
competitor information, and current market prices.
"""
from typing import Dict, Any, List, Optional
import httpx
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import settings


class WebSearchTool:
    """
    Web search tool for market research.
    
    Supports multiple search backends:
    1. Tavily API (recommended for AI applications)
    2. Serper API (Google Search)
    3. Mock data (fallback when no API is available)
    
    The tool automatically falls back to mock data if no API keys are configured.
    """
    
    name: str = "web_search"
    description: str = """
    Search the web for current market information, competitor data, and trends.
    Use this tool when you need to:
    - Find current market prices for products
    - Research competitor offerings and pricing
    - Get latest product reviews and ratings
    - Research market trends and consumer preferences
    - Find information that is not in the internal product catalog
    
    This tool searches external sources and returns relevant web results.
    """
    
    def __init__(
        self,
        tavily_api_key: str = None,
        serper_api_key: str = None
    ):
        """
        Initialize the Web Search tool.
        
        Args:
            tavily_api_key: Tavily API key for web search
            serper_api_key: Serper API key for Google search
        """
        self.tavily_api_key = tavily_api_key or settings.TAVILY_API_KEY
        self.serper_api_key = serper_api_key or settings.SERPER_API_KEY
        
        # Determine which backend to use
        if self.tavily_api_key:
            self.backend = "tavily"
        elif self.serper_api_key:
            self.backend = "serper"
        else:
            self.backend = "mock"
            print("Warning: No web search API key configured. Using mock data.")
    
    async def search_tavily(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search using Tavily API.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Search results dictionary
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "max_results": limit,
                    "include_answer": True
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "query": query,
                    "source": "tavily",
                    "answer": data.get("answer"),
                    "results": [
                        {
                            "title": r.get("title"),
                            "url": r.get("url"),
                            "content": r.get("content"),
                            "score": r.get("score")
                        }
                        for r in data.get("results", [])
                    ],
                    "total_results": len(data.get("results", []))
                }
            else:
                return {
                    "status": "error",
                    "error": f"Tavily API error: {response.status_code}",
                    "query": query
                }
    
    async def search_serper(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search using Serper API (Google Search).
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Search results dictionary
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": self.serper_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "q": query,
                    "num": limit
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for r in data.get("organic", [])[:limit]:
                    results.append({
                        "title": r.get("title"),
                        "url": r.get("link"),
                        "content": r.get("snippet"),
                        "score": None
                    })
                
                return {
                    "status": "success",
                    "query": query,
                    "source": "serper",
                    "answer": data.get("answerBox", {}).get("snippet"),
                    "results": results,
                    "total_results": len(results)
                }
            else:
                return {
                    "status": "error",
                    "error": f"Serper API error: {response.status_code}",
                    "query": query
                }
    
    def search_mock(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Provide mock search results for demonstration purposes.
        
        This is used when no real API keys are configured.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Mock search results
        """
        query_lower = query.lower()
        
        # Mock data for common product research queries
        mock_database = {
            "headphones": {
                "answer": "The noise-cancelling headphones market in 2024 shows strong growth, with premium models ranging from $249-$399. Sony WH-1000XM5 ($349) and Bose QuietComfort Ultra ($429) lead the market. Budget options from brands like Anker and JBL are available for $50-$100.",
                "results": [
                    {
                        "title": "Best Noise-Cancelling Headphones 2024 - CNET",
                        "url": "https://www.cnet.com/tech/mobile/best-noise-canceling-headphones/",
                        "content": "Sony WH-1000XM5 remains the top pick at $349. Bose QuietComfort Ultra at $429 offers superior comfort. Apple AirPods Max at $549 for Apple users.",
                        "score": 0.95
                    },
                    {
                        "title": "Headphone Market Trends 2024 - TechRadar",
                        "url": "https://www.techradar.com/audio/headphones/market-trends",
                        "content": "The wireless headphones market is projected to reach $45.7 billion by 2026. Key trends: active noise cancellation, spatial audio, longer battery life.",
                        "score": 0.89
                    },
                    {
                        "title": "Amazon Best Sellers: Headphones",
                        "url": "https://www.amazon.com/Best-Sellers-Headphones/zgbs",
                        "content": "Top selling wireless headphones: Sony WH-1000XM4 ($248), Apple AirPods Pro ($189), Beats Studio3 ($169).",
                        "score": 0.85
                    }
                ]
            },
            "fitness": {
                "answer": "The home fitness equipment market has stabilized post-pandemic. Smart fitness trackers range from $50-$300, with adjustable dumbbells ($200-$500) being popular. Yoga mats average $20-$40 for quality options.",
                "results": [
                    {
                        "title": "Home Fitness Equipment Market Analysis 2024",
                        "url": "https://www.marketwatch.com/fitness-equipment-2024",
                        "content": "The global fitness equipment market is valued at $14.8 billion. Resistance bands and yoga accessories show 15% YoY growth.",
                        "score": 0.92
                    },
                    {
                        "title": "Best Home Gym Equipment - Wirecutter",
                        "url": "https://www.nytimes.com/wirecutter/reviews/best-home-gym-equipment/",
                        "content": "Top picks: Bowflex SelectTech 552 Dumbbells ($429), Manduka PRO Yoga Mat ($120), TRX Pro4 System ($249).",
                        "score": 0.88
                    }
                ]
            },
            "electronics": {
                "answer": "Consumer electronics pricing varies widely. Smart home devices have seen price drops of 15-20% due to competition. Premium electronics maintain stable pricing. Key players: Apple, Samsung, Sony, LG.",
                "results": [
                    {
                        "title": "Consumer Electronics Trends 2024 - Statista",
                        "url": "https://www.statista.com/consumer-electronics-trends",
                        "content": "Global CE market expected to reach $1.1 trillion in 2024. Smart home devices growing at 12% CAGR. Average selling prices declining for mature categories.",
                        "score": 0.91
                    },
                    {
                        "title": "Best Tech Products 2024 - The Verge",
                        "url": "https://www.theverge.com/best-tech-2024",
                        "content": "Top rated: Apple iPhone 15 Pro, Samsung Galaxy S24, Sony a7C II camera, M3 MacBook Pro.",
                        "score": 0.87
                    }
                ]
            },
            "kitchen": {
                "answer": "Kitchen appliance pricing: coffee makers $60-$200, cast iron skillets $25-$80, air fryers $80-$200. Premium brands command 30-50% premium over budget options.",
                "results": [
                    {
                        "title": "Best Kitchen Appliances 2024 - Good Housekeeping",
                        "url": "https://www.goodhousekeeping.com/kitchen-appliances",
                        "content": "Top picks: Cuisinart Coffee Maker ($99), Lodge Cast Iron Skillet ($45), Ninja Air Fryer ($149).",
                        "score": 0.90
                    },
                    {
                        "title": "Kitchen Trends & Market Analysis",
                        "url": "https://www.kitchentrends.com/market-2024",
                        "content": "Small kitchen appliances market growing at 6% annually. Eco-friendly materials gaining popularity.",
                        "score": 0.84
                    }
                ]
            },
            "protein": {
                "answer": "Protein powder market: Whey protein $25-$50/lb, plant-based $30-$60/lb. Top brands: Optimum Nutrition, Dymatize, Garden of Life. Market growing at 8% CAGR.",
                "results": [
                    {
                        "title": "Best Protein Powders 2024 - Healthline",
                        "url": "https://www.healthline.com/nutrition/best-protein-powder",
                        "content": "Top rated: Optimum Nutrition Gold Standard ($32/2lb), Dymatize ISO100 ($35/2lb), Garden of Life Organic ($45/2lb).",
                        "score": 0.93
                    }
                ]
            }
        }
        
        # Default mock data
        default_mock = {
            "answer": f"Based on current market data for '{query}': Market prices vary depending on brand, quality, and features. Premium products command 20-40% higher prices than budget alternatives. The market shows steady growth with increasing consumer demand for quality products.",
            "results": [
                {
                    "title": f"Market Analysis: {query.title()}",
                    "url": f"https://www.marketresearch.com/{query.replace(' ', '-')}",
                    "content": f"Current market trends for {query} show moderate growth. Consumer preferences are shifting towards quality and sustainability.",
                    "score": 0.80
                },
                {
                    "title": f"Price Comparison: {query.title()}",
                    "url": f"https://www.pricewatch.com/{query.replace(' ', '-')}",
                    "content": f"Prices for {query} range from budget to premium tiers. Key factors affecting pricing include brand reputation, features, and materials.",
                    "score": 0.75
                }
            ]
        }
        
        # Find best matching mock data
        best_match = None
        for key, data in mock_database.items():
            if key in query_lower:
                best_match = data
                break
        
        if not best_match:
            best_match = default_mock
        
        return {
            "status": "success",
            "query": query,
            "source": "mock",
            "note": "Using mock data. Configure TAVILY_API_KEY or SERPER_API_KEY for real web search.",
            "answer": best_match["answer"],
            "results": best_match["results"][:limit],
            "total_results": len(best_match["results"][:limit])
        }
    
    async def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search the web for information.
        
        Automatically selects the appropriate backend based on available API keys.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with search results
        """
        try:
            if self.backend == "tavily":
                return await self.search_tavily(query, limit)
            elif self.backend == "serper":
                return await self.search_serper(query, limit)
            else:
                return self.search_mock(query, limit)
        except Exception as e:
            # Fallback to mock on any error
            result = self.search_mock(query, limit)
            result["fallback_reason"] = str(e)
            return result
    
    def search_sync(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Synchronous version of search for non-async contexts.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with search results (uses mock data in sync mode)
        """
        # For sync mode, always use mock to avoid async issues
        return self.search_mock(query, limit)
    
    def __call__(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Make the tool callable directly (sync version)."""
        return self.search_sync(query, limit)


# Singleton instance
web_search_tool = WebSearchTool()
