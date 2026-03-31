"""
大模型聊天服务 - 统一调用入口
"""
from typing import Optional, List, Dict
import logging
from fastapi import HTTPException

from base.plugins.llm.models.model import LLMModel
from base.plugins.llm.models.api_key import LLMApiKey
from base.plugins.llm.models.conversation import LLMConversation
from base.plugins.llm.models.usage import LLMUsage
from base.plugins.llm.models.provider import LLMProvider

logger = logging.getLogger(__name__)


# 导入各厂商服务
try:
    from base.plugins.llm.services.doubao_service import DoubaoService
except ImportError:
    DoubaoService = None

try:
    from base.plugins.llm.services.openai_service import OpenAIService
except ImportError:
    OpenAIService = None

try:
    from base.plugins.llm.services.anthropic_service import AnthropicService
except ImportError:
    AnthropicService = None

try:
    from base.plugins.llm.services.alibaba_service import AlibabaService
except ImportError:
    AlibabaService = None

try:
    from base.plugins.llm.services.zhipu_service import ZhipuService
except ImportError:
    ZhipuService = None

try:
    from base.plugins.llm.services.deepseek_service import DeepSeekService
except ImportError:
    DeepSeekService = None

try:
    from base.plugins.llm.services.tencent_service import TencentService
except ImportError:
    TencentService = None

try:
    from base.plugins.llm.services.baidu_service import BaiduService
except ImportError:
    BaiduService = None


class ChatService:
    """聊天服务统一管理类"""

    @staticmethod
    async def get_available_api_key(provider_id: int) -> Optional[LLMApiKey]:
        """
        获取可用的API密钥（轮询策略）

        Args:
            provider_id: 厂商ID

        Returns:
            可用的API密钥对象
        """
        # 获取该厂商下所有可用的API密钥
        api_keys = await LLMApiKey.filter(
            provider_id=provider_id,
            status="active"
        ).all()

        # 过滤出真正可用的（配额未超、未过期等）
        available_keys = []
        for key in api_keys:
            if key.is_available:
                available_keys.append(key)

        if not available_keys:
            raise HTTPException(status_code=503, detail="没有可用的API密钥")

        # 简单轮询：选择已使用配额最少的密钥
        available_keys.sort(key=lambda k: k.used_quota)
        return available_keys[0]

    @staticmethod
    async def get_provider_service(provider_name_en: str, api_key: str, endpoint_url: str, api_secret: str = None):
        """
        根据厂商获取对应的服务实例

        Args:
            provider_name_en: 厂商英文标识
            api_key: API密钥
            endpoint_url: API端点
            api_secret: API密钥（部分厂商需要）

        Returns:
            厂商服务实例
        """
        if provider_name_en == "doubao":
            if not DoubaoService:
                raise HTTPException(status_code=500, detail="豆包服务未配置")
            return DoubaoService(api_key=api_key, endpoint_url=endpoint_url)

        elif provider_name_en == "openai":
            if not OpenAIService:
                raise HTTPException(status_code=500, detail="OpenAI服务未配置")
            return OpenAIService(api_key=api_key, endpoint_url=endpoint_url)

        elif provider_name_en == "anthropic":
            if not AnthropicService:
                raise HTTPException(status_code=500, detail="Anthropic服务未配置")
            return AnthropicService(api_key=api_key, endpoint_url=endpoint_url)

        elif provider_name_en == "alibaba":
            if not AlibabaService:
                raise HTTPException(status_code=500, detail="阿里云服务未配置")
            return AlibabaService(api_key=api_key, endpoint_url=endpoint_url)

        elif provider_name_en == "zhipu":
            if not ZhipuService:
                raise HTTPException(status_code=500, detail="智谱AI服务未配置")
            return ZhipuService(api_key=api_key, endpoint_url=endpoint_url)

        elif provider_name_en == "deepseek":
            if not DeepSeekService:
                raise HTTPException(status_code=500, detail="DeepSeek服务未配置")
            return DeepSeekService(api_key=api_key, endpoint_url=endpoint_url)

        elif provider_name_en == "tencent":
            if not TencentService:
                raise HTTPException(status_code=500, detail="腾讯服务未配置")
            return TencentService(api_key=api_key, api_secret=api_secret, endpoint_url=endpoint_url)

        elif provider_name_en == "baidu":
            if not BaiduService:
                raise HTTPException(status_code=500, detail="百度服务未配置")
            if not api_secret:
                raise HTTPException(status_code=400, detail="百度服务需要API Secret")
            return BaiduService(api_key=api_key, api_secret=api_secret, endpoint_url=endpoint_url)

        raise HTTPException(status_code=400, detail=f"不支持的厂商: {provider_name_en}")

    @staticmethod
    async def create_conversation(
        customer_id: int,
        model_id: int,
        messages: List[Dict]
    ) -> LLMConversation:
        """
        创建新对话记录

        Args:
            customer_id: 客户ID
            model_id: 模型ID
            messages: 初始消息列表

        Returns:
            对话对象
        """
        import uuid
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"

        # 简单估算token数（使用豆包的估算方法作为通用方法）
        total_tokens = 0
        for msg in messages:
            content = msg.get("content", "")
            chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
            english_chars = len(content) - chinese_chars
            total_tokens += int(chinese_chars / 1.5 + english_chars / 4)

        conversation = await LLMConversation.create(
            conversation_id=conversation_id,
            customer_id=customer_id,
            model_id=model_id,
            messages=messages,
            total_tokens=total_tokens,
            total_cost=0,
            status="active"
        )

        return conversation

    @staticmethod
    async def update_conversation(
        conversation: LLMConversation,
        assistant_message: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_cost: float
    ):
        """
        更新对话记录

        Args:
            conversation: 对话对象
            assistant_message: 助手回复消息
            prompt_tokens: 输入token数
            completion_tokens: 输出token数
            total_cost: 总费用
        """
        # 添加助手消息到历史
        conversation.messages.append({
            "role": "assistant",
            "content": assistant_message
        })

        # 更新统计
        conversation.total_tokens += (prompt_tokens + completion_tokens)
        conversation.total_cost += total_cost
        await conversation.save()

        # 创建使用记录
        await LLMUsage.create(
            conversation_id=conversation.conversation_id,
            customer_id=conversation.customer_id,
            model_id=conversation.model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=total_cost
        )

    @staticmethod
    async def calculate_cost(model_id: int, prompt_tokens: int, completion_tokens: int) -> float:
        """
        计算费用

        Args:
            model_id: 模型ID
            prompt_tokens: 输入token数
            completion_tokens: 输出token数

        Returns:
            费用（元）
        """
        model = await LLMModel.get_or_none(id=model_id)
        if not model:
            return 0.0

        # 费用 = 输入token * 输入单价 + 输出token * 输出单价
        # 价格单位是元/1K tokens
        input_cost = (prompt_tokens / 1000) * float(model.input_price)
        output_cost = (completion_tokens / 1000) * float(model.output_price)

        return input_cost + output_cost

    @staticmethod
    async def update_api_key_usage(api_key: LLMApiKey, tokens: int):
        """
        更新API密钥使用量

        Args:
            api_key: API密钥对象
            tokens: 本次使用的token数
        """
        from datetime import datetime
        api_key.used_quota += tokens
        api_key.last_used_at = datetime.now()
        await api_key.save()
