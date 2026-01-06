"""
hello_world Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional


class HelloWorldBase(BaseModel):
    """Hello World 基础 Schema"""
    name: str = Field(..., description="名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="描述")
    is_active: bool = Field(True, description="是否激活")


class HelloWorldCreate(HelloWorldBase):
    """创建 Hello World"""
    pass


class HelloWorldUpdate(BaseModel):
    """更新 Hello World"""
    name: Optional[str] = Field(None, description="名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="描述")
    is_active: Optional[bool] = Field(None, description="是否激活")


class HelloWorldResponse(HelloWorldBase):
    """Hello World 响应 Schema"""
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
