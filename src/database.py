"""
Database models and session management for the AI Product Research Assistant.
Uses SQLAlchemy with async SQLite for storing query history and feedback.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON, create_engine
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker as async_sessionmaker

from .config import settings

# Base class for models
Base = declarative_base()


class QueryHistory(Base):
    """Model for storing query history."""
    
    __tablename__ = "query_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    tools_used = Column(JSON, nullable=True)  # List of tools used
    reasoning = Column(Text, nullable=True)  # Agent's reasoning
    confidence = Column(Float, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to feedback
    feedback = relationship("Feedback", back_populates="query", uselist=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "query": self.query,
            "response": self.response,
            "tools_used": self.tools_used,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "feedback": self.feedback.to_dict() if self.feedback else None
        }


class Feedback(Base):
    """Model for storing user feedback on queries."""
    
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("query_history.id"), nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 rating
    helpful = Column(Integer, nullable=True)  # Boolean as int (0/1)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to query
    query = relationship("QueryHistory", back_populates="feedback")
    
    def to_dict(self):
        return {
            "id": self.id,
            "query_id": self.query_id,
            "rating": self.rating,
            "helpful": bool(self.helpful) if self.helpful is not None else None,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class DatabaseManager:
    """
    Manager class for database operations.
    Handles connection pooling and session management.
    """
    
    def __init__(self, database_url: str = None):
        """
        Initialize the database manager.
        
        Args:
            database_url: SQLAlchemy database URL. Defaults to settings.DATABASE_URL
        """
        self.database_url = database_url or settings.DATABASE_URL
        
        # Convert sqlite:// to sqlite+aiosqlite:// for async support
        if self.database_url.startswith("sqlite://") and "aiosqlite" not in self.database_url:
            self.async_database_url = self.database_url.replace("sqlite://", "sqlite+aiosqlite://")
        else:
            self.async_database_url = self.database_url
        
        # Sync engine for migrations/setup
        self.sync_engine = create_engine(
            self.database_url,
            echo=False,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {}
        )
        
        # Async engine for runtime operations
        self.async_engine = create_async_engine(
            self.async_database_url,
            echo=False
        )
        
        # Session factories
        self.SyncSession = sessionmaker(bind=self.sync_engine)
        self.AsyncSession = async_sessionmaker(
            self.async_engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
    
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(self.sync_engine)
    
    def get_sync_session(self):
        """Get a synchronous database session."""
        return self.SyncSession()
    
    async def get_async_session(self) -> AsyncSession:
        """Get an async database session."""
        async with self.AsyncSession() as session:
            yield session
    
    async def save_query(
        self, 
        query: str, 
        response: str = None,
        tools_used: List[str] = None,
        reasoning: str = None,
        confidence: float = None,
        execution_time_ms: int = None
    ) -> QueryHistory:
        """
        Save a query to the database.
        
        Args:
            query: The user's query
            response: The assistant's response
            tools_used: List of tools used to answer the query
            reasoning: Agent's reasoning for tool selection
            confidence: Confidence score of the response
            execution_time_ms: Time taken to process the query
            
        Returns:
            The saved QueryHistory object
        """
        async with self.AsyncSession() as session:
            query_record = QueryHistory(
                query=query,
                response=response,
                tools_used=tools_used,
                reasoning=reasoning,
                confidence=confidence,
                execution_time_ms=execution_time_ms
            )
            session.add(query_record)
            await session.commit()
            await session.refresh(query_record)
            return query_record
    
    async def get_queries(
        self, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[QueryHistory]:
        """
        Retrieve query history.
        
        Args:
            limit: Maximum number of queries to return
            offset: Number of queries to skip
            
        Returns:
            List of QueryHistory objects
        """
        from sqlalchemy import select
        
        async with self.AsyncSession() as session:
            stmt = select(QueryHistory).order_by(
                QueryHistory.created_at.desc()
            ).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_query_by_id(self, query_id: int) -> Optional[QueryHistory]:
        """Get a specific query by ID."""
        from sqlalchemy import select
        
        async with self.AsyncSession() as session:
            stmt = select(QueryHistory).where(QueryHistory.id == query_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def save_feedback(
        self, 
        query_id: int, 
        rating: int = None,
        helpful: bool = None,
        comment: str = None
    ) -> Optional[Feedback]:
        """
        Save feedback for a query.
        
        Args:
            query_id: ID of the query to provide feedback for
            rating: Rating from 1-5
            helpful: Whether the response was helpful
            comment: Optional comment
            
        Returns:
            The saved Feedback object, or None if query not found
        """
        async with self.AsyncSession() as session:
            # Check if query exists
            from sqlalchemy import select
            stmt = select(QueryHistory).where(QueryHistory.id == query_id)
            result = await session.execute(stmt)
            query = result.scalar_one_or_none()
            
            if not query:
                return None
            
            feedback = Feedback(
                query_id=query_id,
                rating=rating,
                helpful=1 if helpful else 0 if helpful is not None else None,
                comment=comment
            )
            session.add(feedback)
            await session.commit()
            await session.refresh(feedback)
            return feedback


# Global database manager instance
db_manager = DatabaseManager()
