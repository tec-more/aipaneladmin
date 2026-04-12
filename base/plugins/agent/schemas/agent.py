"""
Agent schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class AgentBase(BaseModel):
    """Base agent schema"""
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    status: str = Field(default="active", description="Status: active/inactive")
    config: Optional[dict] = Field(None, description="Agent configuration")
    memory_capacity: int = Field(default=100, description="Memory capacity")


class AgentCreate(AgentBase):
    """Create agent schema"""
    skill_ids: Optional[List[int]] = Field(default=[], description="Skill IDs")


class AgentUpdate(BaseModel):
    """Update agent schema"""
    name: Optional[str] = Field(None, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    status: Optional[str] = Field(None, description="Status: active/inactive")
    config: Optional[dict] = Field(None, description="Agent configuration")
    memory_capacity: Optional[int] = Field(None, description="Memory capacity")
    skill_ids: Optional[List[int]] = Field(None, description="Skill IDs")


class AgentResponse(AgentBase):
    """Agent response schema"""
    id: int = Field(..., description="Agent ID")
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")
    skill_count: int = Field(..., description="Number of skills")
    memory_count: int = Field(..., description="Number of memories")
    
    class Config:
        from_attributes = True