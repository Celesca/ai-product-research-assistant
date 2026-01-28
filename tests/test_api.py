"""
Tests for the FastAPI server endpoints.
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import will fail without proper dependencies, so we use try/except
try:
    from src.server import app
    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


@pytest.fixture
def client():
    """Create a test client."""
    if not IMPORT_SUCCESS:
        pytest.skip(f"Could not import server: {IMPORT_ERROR}")
    return TestClient(app)


class TestRootEndpoint:
    """Tests for the root endpoint."""
    
    def test_root_returns_api_info(self, client):
        """Test that root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["name"] == "AI Product Research Assistant"


class TestHealthEndpoint:
    """Tests for the health check endpoint."""
    
    def test_health_check_returns_status(self, client):
        """Test that health check returns status information."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data
        assert "version" in data


class TestToolsEndpoint:
    """Tests for the tools listing endpoint."""
    
    def test_tools_list_returns_tools(self, client):
        """Test that tools endpoint returns list of available tools."""
        response = client.get("/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) == 3
        
        tool_names = [t["name"] for t in data["tools"]]
        assert "product_catalog_search" in tool_names
        assert "web_search" in tool_names
        assert "price_analysis" in tool_names


class TestQueryEndpoint:
    """Tests for the query endpoint."""
    
    def test_query_requires_body(self, client):
        """Test that query endpoint requires a request body."""
        response = client.post("/query")
        assert response.status_code == 422  # Validation error
    
    def test_query_requires_query_field(self, client):
        """Test that query endpoint requires query field."""
        response = client.post("/query", json={})
        assert response.status_code == 422
    
    def test_query_rejects_empty_query(self, client):
        """Test that empty queries are rejected."""
        response = client.post("/query", json={"query": ""})
        assert response.status_code == 422


class TestFeedbackEndpoint:
    """Tests for the feedback endpoint."""
    
    def test_feedback_requires_query_id(self, client):
        """Test that feedback endpoint requires query_id."""
        response = client.post("/feedback", json={})
        assert response.status_code == 422
    
    def test_feedback_validates_rating_range(self, client):
        """Test that rating must be between 1-5."""
        response = client.post("/feedback", json={
            "query_id": 1,
            "rating": 6  # Invalid: > 5
        })
        assert response.status_code == 422
        
        response = client.post("/feedback", json={
            "query_id": 1,
            "rating": 0  # Invalid: < 1
        })
        assert response.status_code == 422


class TestQueriesEndpoint:
    """Tests for the queries history endpoint."""
    
    def test_queries_returns_list(self, client):
        """Test that queries endpoint returns a list."""
        response = client.get("/queries")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "queries" in data
        assert isinstance(data["queries"], list)
    
    def test_queries_accepts_pagination(self, client):
        """Test that queries endpoint accepts pagination parameters."""
        response = client.get("/queries?limit=10&offset=0")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
