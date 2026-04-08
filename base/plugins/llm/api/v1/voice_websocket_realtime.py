"""
实时语音翻译 - WebSocket双向通信（真正的实时版本）

支持客户端边录音边发送音频数据，服务器实时接收并边翻译边返回结果
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import logging
import json
import uuid
import io
import wave
import asyncio
from pathlib import Path

from base.common.security import get_current_user_id_ws
from base.plugins.llm.models.usage import LLMUsageRecord
from base.plugins.llm.services.voice_helper import VoiceServiceHelper

logger = logging.getLogger(__name__)

voice_websocket_realtime_router = APIRouter(
    prefix="/voice",
    tags=["语音服务-WebSocket-实时"],
)

# 别名，用于向后兼容
websocket_router = voice_websocket_realtime_router


@voice_websocket_realtime_router.websocket("/translation/streaming/deprecated2")
async def websocket_translation_realtime(
    websocket: WebSocket,
    provider_id: int = Query(..., description="厂商ID"),
    token: Optional[str] = Query(None, description="认证token")
):
    """
    实时语音翻译 - WebSocket接口（真正的实时版本）

    工作流程：
    1. 客户端连接后发送start消息
    2. 服务器立即连接豆包AST
    3. 客户端每发送一个音频块，服务器立即：
       - 提取PCM数据
       - 发送给豆包
       - 接收翻译结果并转发给客户端
    4. 客户端发送end消息时，服务器完成翻译

    实时返回翻译结果，无需等待录音完成！
    """
    # 添加调试日志
    logger.info(f"[实时翻译] 收到连接请求")
    logger.info(f"[实时翻译] provider_id={provider_id}")
    logger.info(f"[实时翻译] token前10位: {token[:10] if token else 'None'}...")

    await websocket.accept()
    logger.info(f"[实时翻译] WebSocket连接已accept")

    session_id = None
    record = None

    # 豆包连接和任务
    doubao_task = None
    doubao_queue = asyncio.Queue()
    config = {}
    final_result = None

    try:
        # 验证用户身份
        user_id = await get_current_user_id_ws(token)
        logger.info(f"[实时翻译] token验证结果: user_id={user_id}")

        if not user_id:
            logger.error(f"[实时翻译] token验证失败，user_id为None")
            await websocket.send_json({"type": "error", "message": "未授权"})
            await websocket.close(code=1008, reason="Unauthorized")
            return

        logger.info(f"[实时翻译] 翻译会话开始，用户ID: {user_id}")

        # 启动豆包翻译转发任务
        async def forward_to_doubao():
            """转发音频到豆包的异步任务"""
            nonlocal final_result
            service = await VoiceServiceHelper.get_voice_service(provider_id)

            audio_data = await doubao_queue.get()
            logger.info(f"[实时翻译] 豆包任务收到音频: {len(audio_data)} bytes")

            # 调用翻译服务
            async for result in service.streaming_translation(
                audio_data,
                config["source_language"],
                config["target_language"],
                config["format"],
                config["sample_rate"]
            ):
                # 实时转发豆包的返回结果给客户端
                await websocket.send_json(result)

                logger.info(f"[实时翻译] 豆包返回: {result.get('event')}")

                if result.get("event") == "session_finished":
                    final_result = result.get("result", {})
                    break
                elif result.get("event") == "error":
                    break

            return final_result

        while True:
            # 接收消息
            message = await websocket.receive()

            # 处理文本消息（控制消息）
            if "text" in message:
                try:
                    data = json.loads(message["text"])

                    if data.get("type") == "start":
                        # 开始会话
                        session_id = f"ws_trans_{uuid.uuid4().hex[:16]}"
                        config = {
                            "format": data.get("format", "wav"),
                            "sample_rate": data.get("sample_rate", 16000),
                            "source_language": data.get("source_language", "zh"),
                            "target_language": data.get("target_language", "en"),
                        }

                        logger.info(f"[实时翻译] ========== 创建新会话 ==========")
                        logger.info(f"[实时翻译] Session ID: {session_id}")
                        logger.info(f"[实时翻译] 配置: {config}")

                        # 创建记录
                        from datetime import datetime
                        import pytz
                        record = await LLMUsageRecord.create(
                            record_id=session_id,
                            customer_id=user_id,
                            model_id=provider_id,
                            record_type="voice",
                            audio_file="websocket_realtime",
                            audio_format=config["format"],
                            source_language=config["source_language"],
                            target_language=config["target_language"],
                            status="processing",
                            start_time=datetime.now(pytz.UTC)
                        )

                        logger.info(f"[实时翻译] 数据库记录已创建, ID: {record.id}")

                        await websocket.send_json({
                            "type": "started",
                            "session_id": session_id
                        })

                        logger.info(f"[实时翻译] 会话已开始，等待音频数据...")

                    elif data.get("type") == "end":
                        # 结束音频传输
                        logger.info(f"[实时翻译] ========== 收到end消息，完成翻译 ==========")

                        # 通知豆包任务完成
                        await doubao_queue.put(None)  # 发送结束信号

                        # 等待翻译完成
                        if doubao_task and not doubao_task.done():
                            await doubao_task

                        logger.info(f"[实时翻译] 翻译完成")

                        if record:
                            from datetime import datetime
                            import pytz
                            end_time = datetime.now(pytz.UTC)
                            duration_seconds = 0
                            if record.start_time:
                                duration_seconds = int((end_time - record.start_time).total_seconds())
                            
                            # 写入input_text和output_text
                            if final_result:
                                record.input_text = final_result.get("source_text", "")
                                record.output_text = final_result.get("translation_text", "")
                            
                            record.audio_duration = duration_seconds
                            record.status = "completed"
                            record.end_time = end_time
                            await record.save()

                except json.JSONDecodeError as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"JSON解析错误: {str(e)}"
                    })

            # 处理二进制消息（音频数据）- 实时转发！
            elif "bytes" in message:
                audio_chunk = message["bytes"]

                logger.info(f"[实时翻译] 收到音频块: {len(audio_chunk)} bytes")

                # 提取PCM数据（如果是WAV）
                try:
                    if len(audio_chunk) >= 4 and audio_chunk[:4] == b'RIFF':
                        # WAV格式，提取PCM
                        audio_file_obj = io.BytesIO(audio_chunk)
                        with wave.open(audio_file_obj, 'rb') as wf:
                            pcm_data = wf.readframes(wf.getnframes())
                        logger.info(f"[实时翻译] 提取PCM: {len(audio_chunk)} -> {len(pcm_data)} bytes")
                    else:
                        # 纯PCM
                        pcm_data = audio_chunk
                        logger.info(f"[实时翻译] 纯PCM数据: {len(pcm_data)} bytes")

                    # 启动豆包任务（如果还没启动）
                    if not doubao_task:
                        doubao_task = asyncio.create_task(forward_to_doubao())
                        logger.info(f"[实时翻译] 启动豆包翻译任务")

                    # 发送给豆包任务
                    await doubao_queue.put(pcm_data)

                except Exception as e:
                    logger.error(f"[实时翻译] 音频处理失败: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"音频处理失败: {str(e)}"
                    })

    except WebSocketDisconnect:
        logger.info(f"[实时翻译] 客户端断开连接: {session_id}")
        
        # 更新当前记录
        if record:
            from datetime import datetime
            import pytz
            if record.status == "processing":
                record.status = "failed"
                record.end_time = datetime.now(pytz.UTC)
                await record.save()
                logger.info(f"[实时翻译] 记录已标记为失败: {record.record_id}")

        # 确保所有相关的processing记录都被更新
        if session_id:
            from datetime import datetime
            import pytz
            processing_records = await LLMUsageRecord.filter(
                record_id=session_id,
                status="processing"
            )
            for rec in processing_records:
                rec.status = "failed"
                rec.end_time = datetime.now(pytz.UTC)
                await rec.save()
                logger.info(f"[实时翻译] 清理残留记录: {rec.record_id}")
    except Exception as e:
        logger.error(f"[实时翻译] 处理异常: {e}", exc_info=True)
    finally:
        logger.info(f"[实时翻译] 会话结束: {session_id}")


__all__ = ["voice_websocket_realtime_router"]
