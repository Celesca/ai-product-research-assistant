"""
SQLAlchemy models for the AI Product Research Assistant.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base

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
