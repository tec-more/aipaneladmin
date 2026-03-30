"""
厂商和模型相关Schema
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ============ 厂商相关 ============

class ProviderBase(BaseModel):
    """厂商基础模型"""
    name: str = Field(..., min_length=1, max_length=50, description="厂商名称")
    name_en: str = Field(..., min_length=1, max_length=50, description="英文标识")
    logo_url: Optional[str] = Field(None, description="厂商Logo URL")
    official_url: Optional[str] = Field(None, description="官方网站")
    status: str = Field("active", description="状态")
    description: Optional[str] = Field(None, description="描述")


class ProviderCreate(ProviderBase):
    """创建厂商"""
    pass


class ProviderUpdate(BaseModel):
    """更新厂商"""
    name: Optional[str] = None
    name_en: Optional[str] = None
    logo_url: Optional[str] = None
    official_url: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


class ProviderResponse(ProviderBase):
    """厂商响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 模型相关 ============

class ModelBase(BaseModel):
    """模型基础模型"""
    provider_id: int = Field(..., description="厂商ID")
    model_id: str = Field(..., min_length=1, max_length=100, description="模型标识")
    model_name: str = Field(..., min_length=1, max_length=100, description="模型名称")
    context_length: int = Field(4096, description="上下文长度")
    input_price: Decimal = Field(0, ge=0, description="输入价格 (元/1K tokens)")
    output_price: Decimal = Field(0, ge=0, description="输出价格 (元/1K tokens)")
    supports_streaming: bool = Field(True, description="是否支持流式")
    supports_vision: bool = Field(False, description="是否支持视觉")
    supports_function: bool = Field(False, description="是否支持函数调用")
    status: str = Field("active", description="状态")
    description: Optional[str] = Field(None, description="模型描述")


class ModelCreate(ModelBase):
    """创建模型"""
    pass


class ModelUpdate(BaseModel):
    """更新模型"""
    provider_id: Optional[int] = None
    model_id: Optional[str] = None
    model_name: Optional[str] = None
    context_length: Optional[int] = None
    input_price: Optional[Decimal] = None
    output_price: Optional[Decimal] = None
    supports_streaming: Optional[bool] = None
    supports_vision: Optional[bool] = None
    supports_function: Optional[bool] = None
    status: Optional[str] = None
    description: Optional[str] = None


class ModelResponse(ModelBase):
    """模型响应"""
    id: int
    provider: ProviderResponse
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ API密钥相关 ============

class ApiKeyBase(BaseModel):
    """API密钥基础模型"""
    provider_id: int = Field(..., description="厂商ID")
    name: str = Field(..., min_length=1, max_length=100, description="密钥名称")
    api_key: str = Field(..., min_length=1, description="API密钥")
    api_secret: Optional[str] = Field(None, description="API密钥(某些厂商需要)")
    endpoint_url: Optional[str] = Field(None, description="自定义端点URL")
    max_quota: int = Field(100000, description="每日配额限制")
    description: Optional[str] = Field(None, description="备注")


class ApiKeyCreate(ApiKeyBase):
    """创建API密钥"""
    pass


class ApiKeyUpdate(BaseModel):
    """更新API密钥"""
    provider_id: Optional[int] = None
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    endpoint_url: Optional[str] = None
    max_quota: Optional[int] = None
    description: Optional[str] = None


class ApiKeyResponse(ApiKeyBase):
    """API密钥响应"""
    id: int
    provider: ProviderResponse
    remaining_quota: int
    is_available: bool
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 对话相关 ============

class Message(BaseModel):
    """对话消息"""
    role: str = Field(..., description="角色: system/user/assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """对话请求"""
    model: str = Field(..., description="模型标识")
    messages: List[Message] = Field(..., min_items=1, description="对话历史")
    stream: bool = Field(False, description="是否流式响应")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, description="最大Token数")
    top_p: Optional[float] = Field(None, ge=0, le=1, description="top_p采样")
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2, description="频率惩罚")
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2, description="存在惩罚")


class ChatResponse(BaseModel):
    """对话响应"""
    id: str
    object: str
    created: int
    model: str
    choices: List[dict]


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    conversation_id: str
    customer_id: int
    model: Optional[ModelResponse]
    messages: List[Message]
    total_tokens: int
    total_cost: Decimal
    created_at: datetime
    updated_at: datetime
