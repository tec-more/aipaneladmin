"""
真正的实时语音翻译 - WebSocket双向通信
音频流式传输到豆包AST，边收边翻译
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import logging
import json
import uuid
import asyncio
import websockets
from websockets import Headers
from pathlib import Path

from base.common.security import get_current_user_id_ws
from base.plugins.llm.models.voice import LLMVoiceRecord
from base.plugins.llm.services.voice_helper import VoiceServiceHelper

logger = logging.getLogger(__name__)

voice_websocket_v2_router = APIRouter(
    prefix="/voice",
    tags=["语音服务-WebSocket-V2"],
)


@voice_websocket_v2_router.websocket("/translation/streaming/v2")
async def websocket_translation_v2(
    websocket: WebSocket,
    provider_id: int = Query(..., description="厂商ID"),
    token: Optional[str] = Query(None, description="认证token")
):
    """
    真正的实时语音翻译 - 边收边翻译

    工作原理：
    1. 客户端发送start消息
    2. 服务器立即连接豆包AST WebSocket
    3. 收到音频块 → 立即转发给豆包AST
    4. 豆包AST返回翻译 → 立即转发给客户端
    5. 客户端发送end → 结束会话

    与旧版本的区别：
    ❌ 旧版：缓存所有音频 → 收到end → 开始翻译
    ✅ 新版：收到音频块 → 立即翻译 → 实时返回

    客户端使用示例：
    ```javascript
    const ws = new WebSocket('ws://localhost:9998/v1/llm/voice/translation/streaming/v2?provider_id=1&token=xxx');

    // 1. 发送开始消息
    ws.send(JSON.stringify({
        type: 'start',
        source_language: 'zh',
        target_language: 'en'
    }));

    // 2. 边录音边发送音频块（纯PCM，16bit, 16kHz, 单声道）
    function onAudioChunk(chunk) {
        ws.send(chunk);  // 立即发送，等待翻译结果
    }

    // 3. 接收实时翻译结果
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'translation') {
            console.log('实时翻译:', data.text);
        }
    };

    // 4. 结束录音
    ws.send(JSON.stringify({type: 'end'}));
    ```
    """
    logger.info(f"[实时翻译V2] ========== 新连接 ==========")
    logger.info(f"[实时翻译V2] provider_id={provider_id}")

    await websocket.accept()
    logger.info(f"[实时翻译V2] ✅ WebSocket已accept")

    session_id = None
    record = None
    config = {}

    # 豆包WebSocket连接
    doubao_ws = None
    doubao_connected = False

    # 异步任务
    audio_queue = None
    sender_task = None
    receiver_task = None

    try:
        # 验证用户
        user_id = await get_current_user_id_ws(token)
        if not user_id:
            await websocket.send_json({"type": "error", "message": "未授权"})
            await websocket.close(code=1008, reason="Unauthorized")
            return

        logger.info(f"[实时翻译V2] ✅ 用户验证成功: {user_id}")

        while True:
            message = await websocket.receive()

            # 处理控制消息
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")

                    logger.info(f"[实时翻译V2] 收到控制消息: {msg_type}")

                    if msg_type == "start":
                        # 创建会话
                        session_id = f"rt_v2_{uuid.uuid4().hex[:16]}"
                        config = {
                            "format": data.get("format", "wav"),
                            "sample_rate": data.get("sample_rate", 16000),
                            "source_language": data.get("source_language", "zh"),
                            "target_language": data.get("target_language", "en"),
                        }

                        logger.info(f"[实时翻译V2] ========== 会话开始 ==========")
                        logger.info(f"[实时翻译V2] SessionID: {session_id}")
                        logger.info(f"[实时翻译V2] 配置: {config}")

                        # 创建数据库记录
                        record = await LLMVoiceRecord.create(
                            record_id=session_id,
                            customer_id=user_id,
                            model_id=provider_id,
                            recognition_type="translation",
                            audio_file="websocket_v2",
                            audio_format=config["format"],
                            source_language=config["source_language"],
                            target_language=config["target_language"],
                            status="processing"
                        )

                        logger.info(f"[实时翻译V2] ✅ 数据库记录已创建")

                        # 立即连接豆包AST
                        logger.info(f"[实时翻译V2] ========== 连接豆包AST ==========")

                        try:
                            service = await VoiceServiceHelper.get_voice_service(provider_id)

                            from base.plugins.llm.services.doubao_voice_service import DoubaoVoiceService
                            if not isinstance(service, DoubaoVoiceService):
                                raise ValueError("需要豆包AST服务")

                            # 准备连接参数
                            ws_url = "wss://openspeech.bytedance.com/api/v4/ast/v2/translate"
                            conn_id = str(uuid.uuid4())

                            headers = Headers({
                                "X-Api-App-Key": service.api_id or service.api_key,
                                "X-Api-Access-Key": service.access_token or service.api_key,
                                "X-Api-Resource-Id": "volc.service_type.10053",
                                "X-Api-Connect-Id": conn_id
                            })

                            logger.info(f"[实时翻译V2] 连接到豆包AST...")
                            logger.info(f"[实时翻译V2] App-Key: {service.api_id}")

                            # 连接豆包AST
                            doubao_ws = await websockets.connect(
                                ws_url,
                                additional_headers=headers,
                                max_size=1000000000,
                                ping_interval=None,
                                close_timeout=30
                            )

                            doubao_connected = True
                            logger.info(f"[实时翻译V2] ✅ 豆包AST连接成功")

                            # 发送StartSession
                            from python_protogen.products.understanding.ast.ast_service_pb2 import TranslateRequest
                            from python_protogen.common.events_pb2 import Type

                            request_data = TranslateRequest()
                            request_data.request_meta.SessionID = session_id
                            request_data.event = Type.StartSession
                            request_data.user.uid = "ast_py_client"
                            request_data.user.did = "ast_py_client"
                            request_data.source_audio.format = "wav"
                            request_data.source_audio.rate = 16000
                            request_data.source_audio.bits = 16
                            request_data.source_audio.channel = 1
                            request_data.target_audio.format = "ogg_opus"
                            request_data.target_audio.rate = 24000
                            request_data.request.mode = "s2s"
                            request_data.request.source_language = config["source_language"]
                            request_data.request.target_language = config["target_language"]

                            await doubao_ws.send(request_data.SerializeToString())
                            logger.info(f"[实时翻译V2] ✅ StartSession已发送")

                            # 等待SessionStarted
                            response_data = await doubao_ws.recv()
                            from python_protogen.products.understanding.ast.ast_service_pb2 import TranslateResponse
                            Response_data = TranslateResponse()
                            Response_data.ParseFromString(response_data)

                            if Response_data.event != Type.SessionStarted:
                                error_msg = f"会话建立失败: {Response_data.response_meta.Message}"
                                logger.error(f"[实时翻译V2] {error_msg}")
                                await websocket.send_json({"type": "error", "message": error_msg})
                                break

                            logger.info(f"[实时翻译V2] ✅ 会话已建立，可以开始发送音频")

                            # 创建音频队列
                            audio_queue = asyncio.Queue()

                            # 启动音频发送任务
                            async def forward_audio_to_doubao():
                                """转发音频到豆包AST"""
                                try:
                                    chunk_count = 0
                                    total_bytes = 0

                                    logger.info(f"[实时翻译V2-发送] ========== 音频发送任务启动 ==========")

                                    while True:
                                        # 从队列获取音频块
                                        audio_chunk = await audio_queue.get()

                                        if audio_chunk is None:  # 结束信号
                                            logger.info(f"[实时翻译V2-发送] ========== 收到结束信号 ==========")
                                            logger.info(f"[实时翻译V2-发送] 总共发送 {chunk_count} 块, {total_bytes} bytes")

                                            # 发送FinishSession
                                            request_data = TranslateRequest()
                                            request_data.request_meta.SessionID = session_id
                                            request_data.event = Type.FinishSession
                                            request_data.user.uid = "ast_py_client"
                                            request_data.user.did = "ast_py_client"
                                            request_data.source_audio.format = "wav"
                                            request_data.source_audio.rate = 16000
                                            request_data.source_audio.bits = 16
                                            request_data.source_audio.channel = 1
                                            request_data.target_audio.format = "ogg_opus"
                                            request_data.target_audio.rate = 24000

                                            await doubao_ws.send(request_data.SerializeToString())
                                            logger.info(f"[实时翻译V2-发送] ✅ FinishSession已发送")
                                            break

                                        # 发送音频块到豆包
                                        chunk_count += 1
                                        total_bytes += len(audio_chunk)

                                        logger.info(f"[实时翻译V2-发送] ========== 发送第{chunk_count}块 ==========")
                                        logger.info(f"[实时翻译V2-发送] 大小: {len(audio_chunk)} bytes")
                                        logger.info(f"[实时翻译V2-发送] 累计: {chunk_count} 块, {total_bytes} bytes")

                                        request_data = TranslateRequest()
                                        request_data.request_meta.SessionID = session_id
                                        request_data.event = Type.TaskRequest
                                        request_data.user.uid = "ast_py_client"
                                        request_data.user.did = "ast_py_client"
                                        request_data.source_audio.format = "wav"
                                        request_data.source_audio.rate = 16000
                                        request_data.source_audio.bits = 16
                                        request_data.source_audio.channel = 1
                                        if audio_chunk:
                                            request_data.source_audio.binary_data = audio_chunk
                                        request_data.target_audio.format = "ogg_opus"
                                        request_data.target_audio.rate = 24000
                                        request_data.request.mode = "s2s"
                                        request_data.request.source_language = config["source_language"]
                                        request_data.request.target_language = config["target_language"]

                                        serialized = request_data.SerializeToString()
                                        await doubao_ws.send(serialized)

                                        logger.info(f"[实时翻译V2-发送] ✅ 已发送到豆包AST ({len(serialized)} bytes)")

                                        # 每10块打印一次统计
                                        if chunk_count % 10 == 0:
                                            logger.info(f"[实时翻译V2-发送] 📊 进度: 已发送 {chunk_count} 块, {total_bytes} bytes")

                                except Exception as e:
                                    logger.error(f"[实时翻译V2-发送] 异常: {e}", exc_info=True)

                            sender_task = asyncio.create_task(forward_audio_to_doubao())

                            # 启动翻译接收任务
                            async def receive_translation_from_doubao():
                                """接收豆包AST的翻译结果"""
                                try:
                                    translation_segments = []
                                    response_count = 0

                                    logger.info(f"[实时翻译V2-接收] ========== 开始接收豆包AST响应 ==========")

                                    while True:
                                        response_data = await doubao_ws.recv()
                                        response_count += 1

                                        Response_data = TranslateResponse()
                                        Response_data.ParseFromString(response_data)

                                        logger.info(f"[实时翻译V2-接收] ========== 响应 #{response_count} ==========")
                                        logger.info(f"[实时翻译V2-接收] Event类型: {Response_data.event}")
                                        logger.info(f"[实时翻译V2-接收] Event名称: {Type.Name(Response_data.event)}")

                                        # 打印完整的响应内容（调试用）
                                        from google.protobuf.json_format import MessageToDict
                                        try:
                                            response_dict = MessageToDict(Response_data)
                                            logger.info(f"[实时翻译V2-接收] 完整响应: {response_dict}")
                                        except:
                                            logger.warning(f"[实时翻译V2-接收] 无法转换为JSON")

                                        if Response_data.event == Type.SessionFailed:
                                            error_msg = Response_data.response_meta.Message
                                            logger.error(f"[实时翻译V2] ❌ 会话失败: {error_msg}")
                                            await websocket.send_json({"type": "error", "message": error_msg})
                                            break

                                        if Response_data.event == Type.SessionFinished:
                                            logger.info(f"[实时翻译V2] ✅ 会话完成")
                                            logger.info(f"[实时翻译V2] 翻译片段数: {len(translation_segments)}")

                                            from google.protobuf.json_format import MessageToDict
                                            response_dict = MessageToDict(Response_data)

                                            final_result = {
                                                "session_id": session_id,
                                                "source_text": " ".join(translation_segments),
                                                "translation_text": " ".join(translation_segments),
                                                "segments": translation_segments,
                                                "tokens": response_dict
                                            }

                                            await websocket.send_json({
                                                "type": "session_finished",
                                                "result": final_result
                                            })
                                            break

                                        if Response_data.event == Type.UsageResponse:
                                            from google.protobuf.json_format import MessageToDict
                                            response_dict = MessageToDict(Response_data)
                                            logger.info(f"[实时翻译V2] 📊 Token使用情况: {response_dict}")
                                        else:
                                            # 检查是否有翻译文本
                                            if hasattr(Response_data, 'text') and Response_data.text:
                                                translation_segments.append(Response_data.text)
                                                logger.info(f"[实时翻译V2] 📝 翻译: {Response_data.text}")
                                                logger.info(f"[实时翻译V2] 片段总数: {len(translation_segments)}")

                                                # 立即发送给客户端
                                                await websocket.send_json({
                                                    "type": "translation",
                                                    "text": Response_data.text,
                                                    "sequence": Response_data.response_meta.Sequence
                                                })
                                                logger.info(f"[实时翻译V2] ✅ 翻译已发送给客户端")
                                            else:
                                                logger.info(f"[实时翻译V2-接收] 此响应不包含文本")

                                except Exception as e:
                                    logger.error(f"[实时翻译V2-接收] 异常: {e}", exc_info=True)

                            receiver_task = asyncio.create_task(receive_translation_from_doubao())

                            await websocket.send_json({
                                "type": "started",
                                "session_id": session_id
                            })

                            logger.info(f"[实时翻译V2] ✅ 会话已启动，可以开始发送音频")

                        except Exception as e:
                            logger.error(f"[实时翻译V2] 连接豆包AST失败: {e}", exc_info=True)
                            await websocket.send_json({
                                "type": "error",
                                "message": f"连接翻译服务失败: {str(e)}"
                            })
                            break

                    elif msg_type == "end":
                        logger.info(f"[实时翻译V2] ========== 收到end消息 ==========")

                        # 发送结束信号到音频队列
                        if audio_queue:
                            await audio_queue.put(None)

                        # 等待任务完成
                        if sender_task:
                            await sender_task
                        if receiver_task:
                            await receiver_task

                        # 关闭豆包连接
                        if doubao_ws:
                            await doubao_ws.close()
                            doubao_connected = False

                        # 更新数据库
                        if record:
                            record.status = "completed"
                            await record.save()

                        await websocket.send_json({
                            "type": "ended",
                            "session_id": session_id
                        })

                        logger.info(f"[实时翻译V2] ✅ 会话正常结束")
                        break

                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"未知消息类型: {msg_type}"
                        })

                except json.JSONDecodeError as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"JSON解析错误: {str(e)}"
                    })

            # 处理音频数据 - 立即转发到豆包AST
            elif "bytes" in message:
                audio_chunk = message["bytes"]

                logger.info(f"[实时翻译V2] ========== 📥 收到音频块 ==========")
                logger.info(f"[实时翻译V2] 大小: {len(audio_chunk)} bytes")
                logger.info(f"[实时翻译V2] 队列状态: {'可用' if audio_queue else '不可用'}")
                logger.info(f"[实时翻译V2] 豆包连接: {'已连接' if doubao_connected else '未连接'}")

                # 提取PCM（如果是WAV格式）
                pcm_data = audio_chunk
                try:
                    if len(audio_chunk) >= 4 and audio_chunk[:4] == b'RIFF':
                        import io
                        import wave
                        audio_file_obj = io.BytesIO(audio_chunk)
                        with wave.open(audio_file_obj, 'rb') as wf:
                            pcm_data = wf.readframes(wf.getnframes())
                        logger.info(f"[实时翻译V2] 提取PCM: {len(audio_chunk)} -> {len(pcm_data)} bytes")
                except Exception as e:
                    logger.warning(f"[实时翻译V2] PCM提取失败: {e}")

                # 立即放入队列，转发给豆包AST
                if audio_queue and doubao_connected:
                    await audio_queue.put(pcm_data)
                    logger.info(f"[实时翻译V2] ✅ 音频块已放入队列，队列大小: {audio_queue.qsize()}")
                else:
                    logger.warning(f"[实时翻译V2] ⚠️  豆包未连接，丢弃音频块 ({len(audio_chunk)} bytes)")

    except WebSocketDisconnect:
        logger.info(f"[实时翻译V2] 客户端断开连接")

        # 清理资源
        if audio_queue:
            await audio_queue.put(None)

        if sender_task:
            try:
                await asyncio.wait_for(sender_task, timeout=5)
            except:
                sender_task.cancel()

        if receiver_task:
            try:
                await asyncio.wait_for(receiver_task, timeout=5)
            except:
                receiver_task.cancel()

        if doubao_ws:
            await doubao_ws.close()

        if record and record.status == "processing":
            record.status = "failed"
            await record.save()

    except Exception as e:
        logger.error(f"[实时翻译V2] 异常: {e}", exc_info=True)

        try:
            await websocket.send_json({
                "type": "error",
                "message": f"服务器错误: {str(e)}"
            })
        except:
            pass

        # 清理资源
        if audio_queue:
            await audio_queue.put(None)

        if sender_task:
            sender_task.cancel()

        if receiver_task:
            receiver_task.cancel()

        if doubao_ws:
            await doubao_ws.close()

        if record:
            try:
                record.status = "failed"
                record.error_message = str(e)
                await record.save()
            except:
                pass

    finally:
        logger.info(f"[实时翻译V2] ========== 会话结束 ==========")


__all__ = ["voice_websocket_v2_router"]
