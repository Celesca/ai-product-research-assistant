"""
Load Testing for AI Product Research Assistant using Locust.

Run with:
    locust -f locustfile.py --host=http://localhost:8000

Then open http://localhost:8089 to configure and start the test.
"""
from locust import HttpUser, task, between
import random
import json


class ProductResearchUser(HttpUser):
    """
    Simulates a user interacting with the Product Research Assistant API.
    """
    
    # Wait between 1-3 seconds between tasks
    wait_time = between(1, 3)
    
    # Sample queries for testing
    product_catalog_queries = [
        "What wireless headphones do we have in stock?",
        "Show me high-rated electronics under $100",
        "Which products from AudioMax brand are bestsellers?",
        "Find yoga mats with good ratings",
        "What kitchen appliances do we sell?",
        "Show me products in the Sports & Fitness category",
        "Find protein powder products",
        "What water bottles do we have?",
        "Show me products with rating above 4.5",
        "Find products under $50"
    ]
    
    web_search_queries = [
        "Current market price for noise-cancelling headphones",
        "Latest reviews for Sony WH-1000XM5",
        "Trending products in home fitness equipment",
        "Best protein powders 2024",
        "Kitchen appliance market trends"
    ]
    
    price_analysis_queries = [
        "Which products have the lowest profit margins?",
        "Calculate average margin for Electronics category",
        "Show me products with margins below 40%",
        "What are the highest margin products?",
        "Analyze pricing for Sports & Fitness category"
    ]
    
    multi_tool_queries = [
        "Should we lower AudioMax headphones price based on competitors?",
        "Compare our yoga mat prices with market rates",
        "Recommend pricing strategy for our electronics",
        "How do our protein powder prices compare to competitors?"
    ]
    
    @task(5)
    def query_product_catalog(self):
        """Test product catalog RAG queries (most common)."""
        query = random.choice(self.product_catalog_queries)
        self._make_query(query, "product_catalog")
    
    @task(2)
    def query_web_search(self):
        """Test web search queries."""
        query = random.choice(self.web_search_queries)
        self._make_query(query, "web_search")
    
    @task(2)
    def query_price_analysis(self):
        """Test price analysis queries."""
        query = random.choice(self.price_analysis_queries)
        self._make_query(query, "price_analysis")
    
    @task(1)
    def query_multi_tool(self):
        """Test queries requiring multiple tools."""
        query = random.choice(self.multi_tool_queries)
        self._make_query(query, "multi_tool")
    
    @task(3)
    def check_health(self):
        """Test health check endpoint."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(2)
    def get_query_history(self):
        """Test query history endpoint."""
        with self.client.get("/queries?limit=10", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get queries failed: {response.status_code}")
    
    def _make_query(self, query: str, query_type: str):
        """Helper method to make a query request."""
        with self.client.post(
            "/query",
            json={"query": query},
            catch_response=True,
            name=f"/query [{query_type}]"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "success":
                        response.success()
                    else:
                        response.failure(f"Query returned error status: {data.get('status')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Query failed: {response.status_code}")


class HighLoadUser(HttpUser):
    """
    Simulates high-load scenarios for stress testing.
    """
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    simple_queries = [
        "headphones",
        "yoga mat",
        "protein",
        "electronics",
        "kitchen"
    ]
    
    @task
    def rapid_query(self):
        """Rapid fire simple queries."""
        query = random.choice(self.simple_queries)
        self.client.post(
            "/query",
            json={"query": query},
            name="/query [rapid]"
        )
    
    @task
    def health_ping(self):
        """Rapid health checks."""
        self.client.get("/health", name="/health [rapid]")
