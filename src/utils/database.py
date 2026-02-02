from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker as async_sessionmaker
from sqlalchemy import select

from .config import settings
from src.models.sql_models import Base, QueryHistory, Feedback


class DatabaseManager:
    
    def __init__(self, database_url: str = None):

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
        Base.metadata.create_all(self.sync_engine)
    
    def get_sync_session(self):
        return self.SyncSession()
    
    async def get_async_session(self) -> AsyncSession:
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
        
        async with self.AsyncSession() as session:
            stmt = select(QueryHistory).order_by(
                QueryHistory.created_at.desc()
            ).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_query_by_id(self, query_id: int) -> Optional[QueryHistory]:
        """Get a specific query by ID."""
        
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
