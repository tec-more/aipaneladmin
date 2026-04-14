"""
Skill schemas
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SkillBase(BaseModel):
    """Base skill schema"""
    name: str = Field(..., description="Skill name")
    description: Optional[str] = Field(None, description="Skill description")
    type: str = Field(..., description="Skill type")
    parameters: Optional[dict] = Field(None, description="Skill parameters")
    implementation: Optional[str] = Field(None, description="Skill implementation code")
    status: str = Field(default="active", description="Status: active/inactive")


class SkillCreate(SkillBase):
    """Create skill schema"""
    pass


class SkillUpdate(BaseModel):
    """Update skill schema"""
    name: Optional[str] = Field(None, description="Skill name")
    description: Optional[str] = Field(None, description="Skill description")
    type: Optional[str] = Field(None, description="Skill type")
    parameters: Optional[dict] = Field(None, description="Skill parameters")
    implementation: Optional[str] = Field(None, description="Skill implementation code")
    status: Optional[str] = Field(None, description="Status: active/inactive")


class SkillResponse(BaseModel):
    """Skill response schema"""
    id: Optional[int] = Field(None, description="Skill ID")
    name: str = Field(..., description="Skill name")
    description: Optional[str] = Field(None, description="Skill description")
    type: str = Field(..., description="Skill type")
    parameters: Optional[dict] = Field(None, description="Skill parameters")
    implementation: Optional[str] = Field(None, description="Skill implementation code")
    status: str = Field(default="active", description="Status: active/inactive")
    created_at: Optional[datetime] = Field(None, description="Created at")
    updated_at: Optional[datetime] = Field(None, description="Updated at")
    agent_count: int = Field(..., description="Number of agents using this skill")
    source: Optional[str] = Field("database", description="Skill source: database or code")
    
    class Config:
        from_attributes = True