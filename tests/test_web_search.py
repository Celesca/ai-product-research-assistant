"""
Tests for the Web Search tool.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.tools.web_search import WebSearchTool


class TestWebSearchTool:
    """Tests for the WebSearchTool class."""
    
    @pytest.fixture
    def tool(self):
        """Create a WebSearchTool instance."""
        return WebSearchTool()
    
    def test_mock_backend_used_without_api_keys(self, tool):
        """Test that mock backend is used when no API keys are configured."""
        assert tool.backend == "mock"
    
    def test_search_returns_dict(self, tool):
        """Test that search returns a dictionary."""
        result = tool.search_sync("headphones", limit=3)
        assert isinstance(result, dict)
    
    def test_search_has_required_fields(self, tool):
        """Test that search result has required fields."""
        result = tool.search_sync("headphones", limit=3)
        
        assert "status" in result
        assert "query" in result
        assert "results" in result
        assert "source" in result
    
    def test_search_status_is_success(self, tool):
        """Test that search returns success status."""
        result = tool.search_sync("headphones", limit=3)
        assert result["status"] == "success"
    
    def test_search_returns_results(self, tool):
        """Test that search returns results."""
        result = tool.search_sync("headphones", limit=3)
        assert len(result["results"]) > 0
    
    def test_search_respects_limit(self, tool):
        """Test that search respects the limit parameter."""
        result = tool.search_sync("headphones", limit=2)
        assert len(result["results"]) <= 2
    
    def test_search_query_is_preserved(self, tool):
        """Test that original query is preserved in result."""
        query = "wireless headphones 2024"
        result = tool.search_sync(query, limit=3)
        assert result["query"] == query
    
    def test_mock_data_has_answer(self, tool):
        """Test that mock data includes an answer."""
        result = tool.search_sync("headphones", limit=3)
        assert "answer" in result
        assert result["answer"] is not None
    
    def test_results_have_expected_structure(self, tool):
        """Test that each result has expected structure."""
        result = tool.search_sync("headphones", limit=3)
        
        for r in result["results"]:
            assert "title" in r
            assert "url" in r
            assert "content" in r
    
    def test_different_queries_return_relevant_data(self, tool):
        """Test that different queries return relevant mock data."""
        headphones_result = tool.search_sync("headphones", limit=3)
        fitness_result = tool.search_sync("fitness equipment", limit=3)
        
        # Results should be different
        assert headphones_result["answer"] != fitness_result["answer"]
    
    def test_callable_interface(self, tool):
        """Test that tool is callable directly."""
        result = tool("headphones", limit=3)
        assert isinstance(result, dict)
        assert result["status"] == "success"


class TestWebSearchToolWithApiKey:
    """Tests for WebSearchTool with API keys configured."""
    
    def test_tavily_backend_with_key(self):
        """Test that Tavily backend is used when API key is provided."""
        tool = WebSearchTool(tavily_api_key="test_key")
        assert tool.backend == "tavily"
    
    def test_serper_backend_with_key(self):
        """Test that Serper backend is used when API key is provided."""
        tool = WebSearchTool(serper_api_key="test_key")
        assert tool.backend == "serper"
    
    def test_tavily_preferred_over_serper(self):
        """Test that Tavily is preferred when both keys are provided."""
        tool = WebSearchTool(
            tavily_api_key="tavily_key",
            serper_api_key="serper_key"
        )
        assert tool.backend == "tavily"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
