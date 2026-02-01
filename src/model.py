from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

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
