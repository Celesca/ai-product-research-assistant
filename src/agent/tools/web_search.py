from typing import Dict, Any, List, Optional
import httpx
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import settings


class WebSearchTool:
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
        query_lower = query.lower()
        
        # Import mock database
        from data.mock_websearch import MOCK_WEBSEARCH_DATABASE

        mock_database = MOCK_WEBSEARCH_DATABASE
        
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
        # For sync mode, always use mock to avoid async issues
        return self.search_mock(query, limit)
    
    def __call__(self, query: str, limit: int = 5) -> Dict[str, Any]:
        return self.search_sync(query, limit)

# Singleton instance
web_search_tool = WebSearchTool()