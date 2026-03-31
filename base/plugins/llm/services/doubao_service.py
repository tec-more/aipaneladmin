"""
豆包（火山引擎）大模型服务
"""
import json
import httpx
from typing import AsyncIterator, Optional, List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DoubaoService:
    """豆包大模型服务类"""

    def __init__(self, api_key: str, endpoint_url: str = "https://ark.cn-beijing.volces.com/api/v3"):
        self.api_key = api_key
        self.endpoint_url = endpoint_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

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
        url = f"{self.endpoint_url}/chat/completions"

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
                    headers=self.headers,
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
        url = f"{self.endpoint_url}/chat/completions"

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
                    headers=self.headers,
                    json=payload
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:]  # 去掉 "data: " 前缀

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
        # 简单估算：中文字符 / 1.5 + 英文单词数
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_chars = len(text) - chinese_chars

        # 中文约1.5字符=1token，英文约4字符=1token
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


class DoubaoStreamIterator:
    """豆包流式响应迭代器包装类"""

    def __init__(self, stream_generator: AsyncIterator[Dict]):
        self.generator = stream_generator
        self.buffer = ""
        self.first_chunk = True

    async def __aiter__(self):
        async for chunk in self.generator:
            if self.first_chunk:
                self.first_chunk = False
            yield chunk
