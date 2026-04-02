"""
LLM插件API v1路由

路由由插件管理器自动加载，每个文件需导出 {filename}_router
- provider_router
- model_router
- api_key_router
- conversation_router
- usage_router
- client_router (客户端API)
- voice_router (语音API)
- translation_stream_router (流式翻译API)
"""
from fastapi import APIRouter
from base.plugins.llm.api.v1 import provider, model, api_key, conversation, usage, client, voice, voice_translation_stream

# 创建主路由
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(provider.provider_router)
api_router.include_router(model.model_router)
api_router.include_router(api_key.api_key_router)
api_router.include_router(conversation.conversation_router)
api_router.include_router(usage.usage_router)
api_router.include_router(client.client_router)
api_router.include_router(voice.voice_router)
api_router.include_router(voice_translation_stream.translation_stream_router)

__all__ = ["api_router"]
