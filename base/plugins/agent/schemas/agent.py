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
    system_prompt: Optional[str] = Field(None, description="System prompt")
    reasoning_strategy: str = Field(default="function_call", description="Reasoning strategy: function_call/react")


class AgentCreate(AgentBase):
    """Create agent schema"""
    pass


class AgentUpdate(BaseModel):
    """Update agent schema"""
    name: Optional[str] = Field(None, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    status: Optional[str] = Field(None, description="Status: active/inactive")
    config: Optional[dict] = Field(None, description="Agent configuration")
    memory_capacity: Optional[int] = Field(None, description="Memory capacity")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    reasoning_strategy: Optional[str] = Field(None, description="Reasoning strategy: function_call/react")


class AgentResponse(AgentBase):
    """Agent response schema"""
    id: int = Field(..., description="Agent ID")
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")
    skill_count: int = Field(..., description="Number of skills")
    memory_count: int = Field(..., description="Number of memories")
    reasoning_strategy: str = Field(..., description="Reasoning strategy: function_call/react")
    
    class Config:
        from_attributes = True
