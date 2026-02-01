"""
Pydantic models / schemas for API requests, responses, and tool inputs.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# --- Server API Models ---

class QueryRequest(BaseModel):
    """Request model for the query endpoint."""
    query: str = Field(..., description="The user's query", min_length=1, max_length=2000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What wireless headphones do we have in stock?"
            }
        }

class QueryResponse(BaseModel):
    """Response model for the query endpoint."""
    status: str
    query: str
    answer: str
    tools_used: List[str]
    reasoning: str
    confidence: float
    execution_time_ms: int
    query_id: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "query": "What wireless headphones do we have in stock?",
                "answer": "We have 3 wireless headphones in stock...",
                "tools_used": ["product_catalog_search"],
                "reasoning": "Used product catalog search to find wireless headphones",
                "confidence": 0.92,
                "execution_time_ms": 1234,
                "query_id": 1
            }
        }


class FeedbackRequest(BaseModel):
    """Request model for the feedback endpoint."""
    query_id: int = Field(..., description="ID of the query to provide feedback for")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1-5")
    helpful: Optional[bool] = Field(None, description="Whether the response was helpful")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_id": 1,
                "rating": 5,
                "helpful": True,
                "comment": "Very accurate product information!"
            }
        }


class FeedbackResponse(BaseModel):
    """Response model for the feedback endpoint."""
    status: str
    message: str
    feedback_id: Optional[int] = None


class QueryHistoryItem(BaseModel):
    """Model for query history items."""
    id: int
    query: str
    response: Optional[str]
    tools_used: Optional[List[str]]
    reasoning: Optional[str]
    confidence: Optional[float]
    execution_time_ms: Optional[int]
    created_at: str
    feedback: Optional[Dict[str, Any]]


class QueryHistoryResponse(BaseModel):
    """Response model for query history endpoint."""
    status: str
    total: int
    queries: List[QueryHistoryItem]


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]


# --- Agent Tool Input Schemas ---

class ProductSearchInput(BaseModel):
    """Input schema for product catalog search."""
    query: str = Field(description="Natural language search query for products")
    category: Optional[str] = Field(default=None, description="Filter by product category")
    brand: Optional[str] = Field(default=None, description="Filter by brand name")
    min_price: Optional[float] = Field(default=None, description="Minimum price filter")
    max_price: Optional[float] = Field(default=None, description="Maximum price filter")
    min_rating: Optional[float] = Field(default=None, description="Minimum rating filter")
    in_stock: Optional[bool] = Field(default=None, description="Filter for products in stock only")
    limit: int = Field(default=5, description="Maximum number of results to return")


class WebSearchInput(BaseModel):
    """Input schema for web search."""
    query: str = Field(description="Search query for web search")
    limit: int = Field(default=5, description="Maximum number of results")


class PriceAnalysisInput(BaseModel):
    """Input schema for price analysis."""
    analysis_type: str = Field(
        default="lowest_margins",
        description="Type of analysis: lowest_margins, highest_margins, below_threshold, category_analysis, brand_analysis"
    )
    category: Optional[str] = Field(default=None, description="Filter by category")
    brand: Optional[str] = Field(default=None, description="Filter by brand")
    threshold: float = Field(default=40.0, description="Margin threshold for below_threshold analysis")
    limit: int = Field(default=10, description="Maximum number of products to return")
