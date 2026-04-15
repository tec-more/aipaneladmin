"""
豆包（火山引擎）大模型服务 - 使用官方 SDK
"""
import logging
from typing import AsyncIterator, Optional, List, Dict

logger = logging.getLogger(__name__)

try:
    from volcenginesdkarkruntime import Ark
    HAS_ARK_SDK = True
except ImportError:
    HAS_ARK_SDK = False
    logger.warning("volcenginesdkarkruntime 未安装，将使用 HTTP 方式调用")


class DoubaoService:
    """豆包大模型服务类"""

    def __init__(self, api_key: str, endpoint_url: str = "https://ark.cn-beijing.volces.com/api/v3"):
        self.api_key = api_key
        self.endpoint_url = endpoint_url.rstrip('/')
        
        logger.info(f"[DoubaoService] 初始化参数:")
        logger.info(f"  endpoint_url: {self.endpoint_url}")
        logger.info(f"  api_key provided: {api_key is not None and len(api_key) > 0}")
        if api_key:
            logger.info(f"  api_key length: {len(api_key)}")
            logger.info(f"  api_key starts with: {api_key[:8] if len(api_key) > 8 else api_key}...")
        
        if HAS_ARK_SDK:
            logger.info(f"[DoubaoService] 使用官方 SDK")
            self.client = Ark(
                base_url=self.endpoint_url,
                api_key=self.api_key
            )
        else:
            logger.info(f"[DoubaoService] SDK 不可用，将使用 HTTP 方式")
            self.client = None

    async def chat(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 0.9,
        stream: bool = False,
        stop: Optional[List[str]] = None
    ) -> Dict:
        """
        非流式聊天

        Args:
            model: 模型名称，如 doubao-pro-4k
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数 0-1
            max_tokens: 最大token数
            top_p: 采样参数
            stream: 是否流式输出
            stop: 停止词列表

        Returns:
            响应结果 {
                "id": "...",
                "choices": [{
                    "message": {"role": "assistant", "content": "..."},
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        """
        if HAS_ARK_SDK and self.client:
            try:
                logger.info(f"[DoubaoService] 使用官方 SDK 调用")
                logger.info(f"[DoubaoService] 调用参数:")
                logger.info(f"  model: {model}")
                logger.info(f"  temperature: {temperature}")
                logger.info(f"  max_tokens: {max_tokens}")
                logger.info(f"  top_p: {top_p}")
                logger.info(f"  stream: {stream}")
                logger.info(f"  messages count: {len(messages)}")
                if messages:
                    logger.info(f"  last message: {messages[-1].get('content', '')[:100]}...")
                
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    stream=False,
                    stop=stop
                )
                
                result = {
                    "id": completion.id,
                    "choices": [],
                    "usage": {
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    }
                }
                
                for choice in completion.choices:
                    result["choices"].append({
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    })
                
                return result
                
            except Exception as e:
                logger.warning(f"[DoubaoService] SDK调用失败，尝试HTTP方式: {str(e)}")
        
        logger.info(f"[DoubaoService] 使用HTTP方式调用")
        return await self._chat_http(model, messages, temperature, max_tokens, top_p, stop)

    async def _chat_http(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None
    ) -> Dict:
        """HTTP 方式调用（备用方案）"""
        import httpx
        
        url = f"{self.endpoint_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False
        }

        if stop:
            payload["stop"] = stop

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"豆包API错误: {e.response.status_code} - {e.response.text}")
            raise Exception(f"豆包API调用失败: {e.response.text}")
        except Exception as e:
            logger.error(f"豆包服务异常: {str(e)}")
            raise

    async def chat_stream(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None
    ) -> AsyncIterator[Dict]:
        """
        流式聊天

        Args:
            同 chat 方法

        Yields:
            流式数据块 {
                "id": "...",
                "choices": [{
                    "delta": {"content": "..."},
                    "finish_reason": None
                }],
                "usage": {...}  # 仅在最后一块包含
            }
        """
        if HAS_ARK_SDK and self.client:
            try:
                logger.info(f"[DoubaoService] 使用官方 SDK 流式调用")
                stream = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    stream=True,
                    stop=stop
                )
                
                for chunk in stream:
                    result = {
                        "id": chunk.id,
                        "choices": [],
                        "usage": None
                    }
                    
                    for choice in chunk.choices:
                        delta = {}
                        if choice.delta.role:
                            delta["role"] = choice.delta.role
                        if choice.delta.content:
                            delta["content"] = choice.delta.content
                        
                        result["choices"].append({
                            "delta": delta,
                            "finish_reason": choice.finish_reason
                        })
                    
                    if chunk.usage:
                        result["usage"] = {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }
                    
                    yield result
                    
            except Exception as e:
                logger.warning(f"[DoubaoService] SDK流式调用失败，尝试HTTP方式: {str(e)}")
                async for chunk in self._chat_stream_http(model, messages, temperature, max_tokens, top_p, stop):
                    yield chunk
                return
        
        logger.info(f"[DoubaoService] 使用HTTP方式流式调用")
        async for chunk in self._chat_stream_http(model, messages, temperature, max_tokens, top_p, stop):
            yield chunk

    async def _chat_stream_http(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None
    ) -> AsyncIterator[Dict]:
        """HTTP 方式流式调用（备用方案）"""
        import httpx
        import json
        
        url = f"{self.endpoint_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": True
        }

        if stop:
            payload["stop"] = stop

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:]

                            if data_str.strip() == "[DONE]":
                                break

                            try:
                                chunk = json.loads(data_str)
                                yield chunk
                            except json.JSONDecodeError:
                                logger.warning(f"无法解析SSE数据: {data_str}")
                                continue

        except httpx.HTTPStatusError as e:
            logger.error(f"豆包流式API错误: {e.response.status_code}")
            raise Exception(f"豆包流式调用失败: {e.response.text}")
        except Exception as e:
            logger.error(f"豆包流式服务异常: {str(e)}")
            raise

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        估算token数量（粗略计算）
        豆包使用类似GPT的分词方式，中文字符约1.5-2字符/token

        Args:
            text: 文本内容

        Returns:
            估算的token数
        """
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_chars = len(text) - chinese_chars

        return int(chinese_chars / 1.5 + english_chars / 4)

    @staticmethod
    def format_messages(messages: List[Dict]) -> List[Dict]:
        """
        格式化消息列表，确保符合豆包API要求

        Args:
            messages: 原始消息列表

        Returns:
            格式化后的消息列表
        """
        formatted = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                formatted.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        return formatted
