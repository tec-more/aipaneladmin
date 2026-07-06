"""
审批流程 Schema 定义
"""
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


# ==================== 流程定义 ====================

class FlowCreate(BaseModel):
    """创建流程"""
    name: str = Field(..., min_length=1, max_length=100, description="流程名称")
    code: str = Field(..., min_length=1, max_length=100, description="流程编码")
    description: Optional[str] = Field(None, description="流程描述")
    form_config: List[Any] = Field(default=[], description="表单配置")
    flow_config: Dict[str, Any] = Field(default={}, description="流程配置")
    business_type: Optional[str] = Field(None, description="业务类型")
    is_active: bool = Field(default=True, description="是否启用")


class FlowUpdate(BaseModel):
    """更新流程"""
    name: Optional[str] = Field(None, max_length=100, description="流程名称")
    description: Optional[str] = Field(None, description="流程描述")
    form_config: Optional[List[Any]] = Field(None, description="表单配置")
    flow_config: Optional[Dict[str, Any]] = Field(None, description="流程配置")
    business_type: Optional[str] = Field(None, description="业务类型")
    is_active: Optional[bool] = Field(None, description="是否启用")


class FlowResponse(BaseModel):
    """流程响应"""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool
    form_config: List[Any] = []
    flow_config: Dict[str, Any] = {}
    business_type: Optional[str] = None
    is_system: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FlowListQuery(BaseModel):
    """流程列表查询"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=200, description="每页数量")
    name: Optional[str] = Field(None, description="流程名称(模糊搜索)")
    business_type: Optional[str] = Field(None, description="业务类型")
    is_active: Optional[bool] = Field(None, description="是否启用")
