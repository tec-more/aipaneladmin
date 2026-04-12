"""
Memory schemas
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class MemoryBase(BaseModel):
    """Base memory schema"""
    content: str = Field(..., description="Memory content")
    type: str = Field(default="short_term", description="Memory type: short_term/long_term")
    importance: float = Field(default=0.5, description="Memory importance (0-1)")


class MemoryCreate(MemoryBase):
    """Create memory schema"""
    agent_id: int = Field(..., description="Agent ID")


class MemoryUpdate(BaseModel):
    """Update memory schema"""
    content: Optional[str] = Field(None, description="Memory content")
    type: Optional[str] = Field(None, description="Memory type: short_term/long_term")
    importance: Optional[float] = Field(None, description="Memory importance (0-1)")


class MemoryResponse(MemoryBase):
    """Memory response schema"""
    id: int = Field(..., description="Memory ID")
    agent_id: int = Field(..., description="Agent ID")
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")
    recall_count: int = Field(..., description="Recall count")
    last_recalled_at: Optional[datetime] = Field(None, description="Last recalled time")
    
    class Config:
        from_attributes = True