"""
- POST /query - Main agent query endpoint
- GET /queries - Retrieve query history
- POST /feedback - Submit user feedback
- GET /health - Health check
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import time
import logging
from contextlib import asynccontextmanager

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.utils.config import settings
from src.utils.database import DatabaseManager, db_manager
from src.agent.research_agent import ResearchAgent, create_agent
from src.models.schemas import (
    QueryRequest, 
    QueryResponse, 
    FeedbackRequest, 
    FeedbackResponse, 
    QueryHistoryItem, 
    QueryHistoryResponse, 
    HealthResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationsListResponse,
    MessageResponse
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    
    logger.info("Starting AI Product Research Assistant...")
    
    logger.info("Initializing database...")
    db_manager.create_tables()
    
    logger.info("Initializing AI agent...")
    try:
        agent = create_agent()
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize agent: {e}. Will retry on first query.")
    
    logger.info("Startup complete!")
    
    yield
    
    logger.info("Shutting down AI Product Research Assistant...")


app = FastAPI(
    title="AI Product Research Assistant",
    description="AI-powered product research assistant using RAG, web search, and price analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance (initialized on startup)
agent: Optional[ResearchAgent] = None


def get_agent() -> ResearchAgent:
    """Dependency to get the agent instance."""
    global agent
    if agent is None:
        agent = create_agent()
    return agent

@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_endpoint(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    agent: ResearchAgent = Depends(get_agent)
):
    logger.info(f"Received query: {request.query[:100]}...")
    
    try:
        conversation_history = None
        conversation_id = request.conversation_id
        
        # If conversation_id provided, load conversation history
        if conversation_id:
            messages = await db_manager.get_conversation_messages(conversation_id)
            if messages:
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ]
                logger.info(f"Loaded {len(messages)} messages from conversation {conversation_id}")
        
        # Process query with agent (with conversation history if available)
        result = await agent.aquery(request.query, conversation_history=conversation_history)
        
        # Save to query history (legacy)
        query_record = await db_manager.save_query(
            query=request.query,
            response=result.get("answer"),
            tools_used=result.get("tools_used", []),
            reasoning=result.get("reasoning"),
            confidence=result.get("confidence"),
            execution_time_ms=result.get("execution_time_ms")
        )
        
        # If conversation_id provided, also save messages to conversation
        if conversation_id:
            # Save user message
            await db_manager.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.query
            )
            # Save assistant message
            await db_manager.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=result.get("answer", ""),
                tools_used=result.get("tools_used", []),
                confidence=result.get("confidence"),
                execution_time_ms=result.get("execution_time_ms")
            )
        
        return QueryResponse(
            status=result.get("status", "success"),
            query=request.query,
            answer=result.get("answer", ""),
            tools_used=result.get("tools_used", []),
            reasoning=result.get("reasoning", ""),
            confidence=result.get("confidence", 0.0),
            execution_time_ms=result.get("execution_time_ms", 0),
            query_id=query_record.id if query_record else None
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Retrieve query history return list of past queries
@app.get("/queries", response_model=QueryHistoryResponse, tags=["History"])
async def get_queries(
    limit: int = 50,
    offset: int = 0
):
    try:
        queries = await db_manager.get_queries(limit=limit, offset=offset)
        
        return QueryHistoryResponse(
            status="success",
            total=len(queries),
            queries=[
                QueryHistoryItem(
                    id=q.id,
                    query=q.query,
                    response=q.response,
                    tools_used=q.tools_used,
                    reasoning=q.reasoning,
                    confidence=q.confidence,
                    execution_time_ms=q.execution_time_ms,
                    created_at=q.created_at.isoformat() if q.created_at else "",
                    feedback=q.feedback.to_dict() if q.feedback else None
                )
                for q in queries
            ]
        )
        
    except Exception as e:
        logger.error(f"Error retrieving queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Submit feedback for a query response
@app.post("/feedback", response_model=FeedbackResponse, tags=["Feedback"])
async def submit_feedback(request: FeedbackRequest):
    try:
        # Check if query exists
        query = await db_manager.get_query_by_id(request.query_id)
        if not query:
            raise HTTPException(status_code=404, detail=f"Query with ID {request.query_id} not found")
        
        # Save feedback
        feedback = await db_manager.save_feedback(
            query_id=request.query_id,
            rating=request.rating,
            helpful=request.helpful,
            comment=request.comment
        )
        
        if feedback:
            return FeedbackResponse(
                status="success",
                message="Feedback submitted successfully",
                feedback_id=feedback.id
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to save feedback")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    services = {}
    
    # Check database
    try:
        # Simple test query
        await db_manager.get_queries(limit=1)
        services["database"] = "healthy"
    except Exception as e:
        services["database"] = f"unhealthy: {str(e)}"
    
    # Qdrant services
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        client.get_collections()
        services["qdrant"] = "healthy"
    except Exception as e:
        services["qdrant"] = f"unhealthy: {str(e)}"
    
    # Ollama services
    try:
        import httpx
        response = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        if response.status_code == 200:
            services["ollama"] = "healthy"
        else:
            services["ollama"] = f"unhealthy: status {response.status_code}"
    except Exception as e:
        services["ollama"] = f"unhealthy: {str(e)}"
    
    all_healthy = all("healthy" == v for v in services.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        services=services
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "AI Product Research Assistant",
        "version": "1.0.0",
        "description": "AI-powered product research using RAG, web search, and price analysis",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/tools", tags=["Info"])
async def list_tools():
    return {
        "tools": [
            {
                "name": "product_catalog_search",
                "description": "Search the internal product catalog using natural language queries",
                "use_cases": [
                    "Find products by description or features",
                    "Search by category or brand",
                    "Filter by price range or ratings",
                    "Check stock availability"
                ]
            },
            {
                "name": "web_search",
                "description": "Search the web for market trends and competitor information",
                "use_cases": [
                    "Get current market prices",
                    "Research competitor products",
                    "Find product reviews",
                    "Discover market trends"
                ]
            },
            {
                "name": "price_analysis",
                "description": "Analyze pricing and calculate profit margins",
                "use_cases": [
                    "Find products with lowest/highest margins",
                    "Analyze margins by category",
                    "Get pricing recommendations",
                    "Identify underpriced products"
                ]
            }
        ]
    }


# === Conversation Endpoints (Multi-Turn Support) ===

@app.post("/conversations", response_model=ConversationResponse, tags=["Conversations"])
async def create_conversation(request: ConversationCreate = Body(default=ConversationCreate())):
    """Create a new conversation session for multi-turn interactions."""
    try:
        title = request.title if request else None
        conversation = await db_manager.create_conversation(title=title)
        
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat() if conversation.created_at else "",
            updated_at=conversation.updated_at.isoformat() if conversation.updated_at else "",
            message_count=0
        )
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations", response_model=ConversationsListResponse, tags=["Conversations"])
async def list_conversations(limit: int = 50, offset: int = 0):
    """List all conversations with pagination."""
    try:
        conversations = await db_manager.get_conversations(limit=limit, offset=offset)
        
        return ConversationsListResponse(
            status="success",
            total=len(conversations),
            conversations=[
                ConversationResponse(
                    id=c.id,
                    title=c.title,
                    created_at=c.created_at.isoformat() if c.created_at else "",
                    updated_at=c.updated_at.isoformat() if c.updated_at else "",
                    message_count=len(c.messages) if hasattr(c, 'messages') and c.messages else 0
                )
                for c in conversations
            ]
        )
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse, tags=["Conversations"])
async def get_conversation(conversation_id: int):
    """Get a specific conversation with all its messages."""
    try:
        conversation = await db_manager.get_conversation_by_id(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        return ConversationDetailResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at.isoformat() if conversation.created_at else "",
            updated_at=conversation.updated_at.isoformat() if conversation.updated_at else "",
            messages=[
                MessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    tools_used=m.tools_used,
                    confidence=m.confidence,
                    execution_time_ms=m.execution_time_ms,
                    created_at=m.created_at.isoformat() if m.created_at else ""
                )
                for m in conversation.messages
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversations/{conversation_id}", tags=["Conversations"])
async def delete_conversation(conversation_id: int):
    """Delete a conversation and all its messages."""
    try:
        deleted = await db_manager.delete_conversation(conversation_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        return {"status": "success", "message": f"Conversation {conversation_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
