"""
审批规则 Schema 定义
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class RuleCreate(BaseModel):
    """创建审批规则"""
    business_type: str = Field(..., min_length=1, max_length=50, description="业务类型")
    model: Optional[str] = Field(None, max_length=50, description="业务模型标识（按模型匹配审批，缺省用 business_type）")
    path_pattern: Optional[str] = Field(None, max_length=255, description="路径匹配模式（已废弃）")
    methods: List[str] = Field(default=["POST", "PUT", "DELETE"], description="拦截方法列表")
    flow_id: int = Field(..., description="关联审批流程ID")
    is_active: bool = Field(default=True, description="是否启用")
    priority: int = Field(default=0, description="优先级")
    description: Optional[str] = Field(None, description="规则说明")


class RuleUpdate(BaseModel):
    """更新审批规则"""
    business_type: Optional[str] = Field(None, max_length=50, description="业务类型")
    model: Optional[str] = Field(None, max_length=50, description="业务模型标识（按模型匹配审批）")
    path_pattern: Optional[str] = Field(None, max_length=255, description="路径匹配模式（已废弃）")
    methods: Optional[List[str]] = Field(None, description="拦截方法列表")
    flow_id: Optional[int] = Field(None, description="关联审批流程ID")
    is_active: Optional[bool] = Field(None, description="是否启用")
    priority: Optional[int] = Field(None, description="优先级")
    description: Optional[str] = Field(None, description="规则说明")


class RuleResponse(BaseModel):
    """审批规则响应"""
    id: int
    business_type: str
    model: Optional[str] = None
    path_pattern: Optional[str] = None
    methods: List[str]
    flow_id: int
    flow_name: Optional[str] = None
    is_active: bool
    priority: int
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RuleListQuery(BaseModel):
    """审批规则列表查询"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=200, description="每页数量")
    business_type: Optional[str] = Field(None, description="业务类型")
    is_active: Optional[bool] = Field(None, description="是否启用")
