"""
豆包语音服务 - 完整实现
"""
import json
import httpx
import asyncio
import websockets
import logging
from typing import AsyncIterator, Dict, Optional, BinaryIO
from pathlib import Path

logger = logging.getLogger(__name__)


class DoubaoVoiceService:
    """豆包语音服务类 - 完整版"""

    def __init__(self, api_key: str, endpoint_url: str = "https://openspeech.bytedance.com"):
        self.api_key = api_key
        self.endpoint_url = endpoint_url.rstrip('/')
        self.app_id = self._extract_app_id(api_key)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _extract_app_id(self, api_key: str) -> str:
        """从API Key提取App ID"""
        # 豆包的API Key格式通常是 app_id:secret
        if ':' in api_key:
            return api_key.split(':')[0]
        return api_key

    # ========== 1. 流式语音识别（ASR实时） ==========

    async def streaming_asr(self, audio_data: bytes, format: str = "wav",
                            sample_rate: int = 16000, language: str = "zh") -> AsyncIterator[Dict]:
        """
        流式语音识别（实时）

        Args:
            audio_data: 音频数据
            format: 音频格式（wav/mp3/opus等）
            sample_rate: 采样率（16000）
            language: 语言（zh/en等）

        Yields:
            识别结果片段
        """
        ws_url = "wss://openspeech.bytedance.com/api/v2/asr"

        payload = {
            "app": {
                "appid": self.app_id,
                "token": self.api_key,
                "cluster": "volcano_tob"
            },
            "user": {
                "uid": "user_001"
            },
            "audio": {
                "format": format,
                "sample_rate": sample_rate,
                "language": language,
                "bits": 16,
                "channel": 1
            },
            "request": {
                "reqid": f"asr_{asyncio.get_event_loop().time()}",
                "nbest": 1,
                "enable_punctuation": True,
                "enable_itn": False
            }
        }

        try:
            async with websockets.connect(ws_url) as ws:
                # 发送配置
                await ws.send(json.dumps(payload))

                # 发送音频数据
                await ws.send(audio_data)

                # 接收结果
                while True:
                    response = await ws.recv()
                    result = json.loads(response)

                    if result.get("result") == "success":
                        yield result
                    elif result.get("is_final"):
                        break
                    elif result.get("error_code"):
                        raise Exception(f"ASR错误: {result.get('message')}")

        except Exception as e:
            logger.error(f"流式ASR失败: {str(e)}")
            raise

    # ========== 2. 录音文件识别（ASR文件） ==========

    async def file_asr(self, audio_file: str, format: str = "wav",
                      sample_rate: int = 16000, language: str = "zh") -> Dict:
        """
        录音文件识别

        Args:
            audio_file: 音频文件路径或URL
            format: 音频格式
            sample_rate: 采样率
            language: 语言

        Returns:
            识别结果
        """
        url = f"{self.endpoint_url}/api/v2/asr"

        # 读取音频文件
        if Path(audio_file).exists():
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
        else:
            # 如果是URL，下载音频
            async with httpx.AsyncClient() as client:
                response = await client.get(audio_file)
                audio_data = response.content

        payload = {
            "app": {
                "appid": self.app_id,
                "token": self.api_key
            },
            "audio": {
                "format": format,
                "sample_rate": sample_rate,
                "language": language
            }
        }

        # 使用multipart上传
        files = {
            "file": ("audio.wav", audio_data, f"audio/{format}")
        }

        data = {
            "payload": json.dumps(payload)
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, data=data, files=files)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"文件ASR错误: {e.response.status_code} - {e.response.text}")
            raise Exception(f"文件ASR失败: {e.response.text}")

    # ========== 3. 语音合成（TTS） ==========

    async def text_to_speech(self, text: str, voice_type: str = "zh_female_shuangkuaisisi_moon_bigtts",
                             speed: float = 1.0, pitch: float = 1.0, volume: float = 1.0,
                             format: str = "mp3", sample_rate: int = 24000) -> bytes:
        """
        文字转语音

        Args:
            text: 要合成的文本
            voice_type: 音色（默认为双快思思）
            speed: 语速（0.2-3.0，默认1.0）
            pitch: 音调（-12到12，默认1.0）
            volume: 音量（0.1-10.0，默认1.0）
            format: 音频格式（mp3/wav/opus等）
            sample_rate: 采样率（24000）

        Returns:
            音频数据（bytes）
        """
        url = f"{self.endpoint_url}/api/v2/tts"

        payload = {
            "app": {
                "appid": self.app_id,
                "token": self.api_key
            },
            "user": {
                "uid": "user_001"
            },
            "audio": {
                "voice_type": voice_type,
                "encoding": format,
                "speed": speed,
                "volume": volume,
                "pitch": pitch,
                "sample_rate": sample_rate
            },
            "request": {
                "reqid": f"tts_{asyncio.get_event_loop().time()}",
                "text": text,
                "text_type": "plain",
                "operation": "query"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()

                # 返回音频数据
                if response.headers.get("content-type", "").startswith("audio"):
                    return response.content
                else:
                    # 如果返回JSON，可能是错误
                    result = response.json()
                    if result.get("error_code"):
                        raise Exception(f"TTS错误: {result.get('message')}")
                    return result

        except httpx.HTTPStatusError as e:
            logger.error(f"TTS错误: {e.response.status_code} - {e.response.text}")
            raise Exception(f"TTS失败: {e.response.text}")

    # ========== 4. 声音复刻 ==========

    async def clone_voice(self, reference_audio: str, voice_name: str,
                          description: str = "") -> Dict:
        """
        声音复刻

        Args:
            reference_audio: 参考音频文件路径
            voice_name: 音色名称
            description: 音色描述

        Returns:
            复刻结果，包含voice_id
        """
        url = f"{self.endpoint_url}/api/v2/voice/clone"

        # 读取参考音频
        if Path(reference_audio).exists():
            with open(reference_audio, 'rb') as f:
                audio_data = f.read()
        else:
            raise FileNotFoundError(f"参考音频不存在: {reference_audio}")

        payload = {
            "app": {
                "appid": self.app_id,
                "token": self.api_key
            },
            "user": {
                "uid": "user_001"
            },
            "audio": {
                "voice_name": voice_name,
                "sample_rate": 24000,
                "encoding": "mp3"
            },
            "request": {
                "reqid": f"clone_{asyncio.get_event_loop().time()}",
                "operation": "submit"
            }
        }

        files = {
            "file": ("reference.mp3", audio_data, "audio/mpeg")
        }

        data = {
            "payload": json.dumps(payload)
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, data=data, files=files)
                response.raise_for_status()
                result = response.json()

                if result.get("error_code"):
                    raise Exception(f"声音复刻错误: {result.get('message')}")

                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"声音复刻错误: {e.response.status_code} - {e.response.text}")
            raise Exception(f"声音复刻失败: {e.response.text}")

    async def check_clone_status(self, clone_id: str) -> Dict:
        """
        查询声音复刻状态

        Args:
            clone_id: 复刻任务ID

        Returns:
            复刻状态
        """
        url = f"{self.endpoint_url}/api/v2/voice/clone"

        payload = {
            "app": {
                "appid": self.app_id,
                "token": self.api_key
            },
            "request": {
                "operation": "query",
                "reqid": clone_id
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"查询复刻状态失败: {str(e)}")
            raise

    # ========== 5. 同声传译 ==========

    async def streaming_translation(self, audio_data: bytes,
                                    source_language: str = "zh",
                                    target_language: str = "en",
                                    format: str = "wav",
                                    sample_rate: int = 16000) -> AsyncIterator[Dict]:
        """
        同声传译（流式）

        Args:
            audio_data: 音频数据
            source_language: 源语言
            target_language: 目标语言
            format: 音频格式
            sample_rate: 采样率

        Yields:
            翻译结果
        """
        ws_url = "wss://openspeech.bytedance.com/api/v2/translation"

        payload = {
            "app": {
                "appid": self.app_id,
                "token": self.api_key,
                "cluster": "volcano_tob"
            },
            "user": {
                "uid": "user_001"
            },
            "audio": {
                "format": format,
                "sample_rate": sample_rate,
                "source_language": source_language,
                "target_language": target_language
            },
            "request": {
                "reqid": f"trans_{asyncio.get_event_loop().time()}",
                "enable_punctuation": True
            }
        }

        try:
            async with websockets.connect(ws_url) as ws:
                # 发送配置
                await ws.send(json.dumps(payload))

                # 发送音频数据
                await ws.send(audio_data)

                # 接收翻译结果
                while True:
                    response = await ws.recv()
                    result = json.loads(response)

                    if result.get("result") == "success":
                        yield result
                    elif result.get("is_final"):
                        break
                    elif result.get("error_code"):
                        raise Exception(f"同声传译错误: {result.get('message')}")

        except Exception as e:
            logger.error(f"同声传译失败: {str(e)}")
            raise

    # ========== 辅助方法 ==========

    @staticmethod
    async def save_audio_file(audio_data: bytes, directory: str = "uploads/voice") -> str:
        """
        保存音频文件

        Args:
            audio_data: 音频数据
            directory: 保存目录

        Returns:
            文件路径
        """
        import os
        import uuid

        # 确保目录存在
        os.makedirs(directory, exist_ok=True)

        # 生成唯一文件名
        filename = f"{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(directory, filename)

        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(audio_data)

        return filepath

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """估算token数量"""
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + english_chars / 4)
