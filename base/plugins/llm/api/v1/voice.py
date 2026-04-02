"""
语音API接口 - 支持语音专用API Key
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional
import logging
import json

from base.common.response import SuccessResponse
from base.common.security import get_current_user_id
from base.plugins.llm.models.voice import LLMVoiceRecord, LLMTTSRecord, LLMVoiceClone
from base.plugins.llm.services.voice_helper import VoiceServiceHelper

logger = logging.getLogger(__name__)

voice_router = APIRouter(
    prefix="/voice",
    tags=["语音服务"],
    dependencies=[Depends(get_current_user_id)]
)

# 测试endpoint：验证新代码是否加载
@voice_router.get("/test/new_code", summary="测试新代码是否加载")
async def test_new_code():
    """测试新的audio_format_utils是否可用"""
    try:
        from base.plugins.llm.services.audio_format_utils import detect_audio_format
        return {
            "status": "success",
            "message": "新代码已加载",
            "module": "audio_format_utils",
            "available_functions": ["detect_audio_format", "convert_float32_to_int16_pcm", "convert_audio_to_wav"]
        }
    except ImportError as e:
        return {
            "status": "error",
            "message": "新代码未加载",
            "error": str(e)
        }


# ========== 1. 流式语音识别 ==========

@voice_router.post("/asr/streaming", summary="流式语音识别")
async def streaming_asr(
    audio_file: UploadFile,
    provider_id: int = Form(..., description="厂商ID"),
    format: str = Form("wav"),
    sample_rate: int = Form(16000),
    language: str = Form("zh"),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    流式语音识别（实时）

    上传音频文件进行实时语音识别
    """
    try:
        # 获取语音服务（自动使用语音专用API Key）
        service = await VoiceServiceHelper.get_voice_service(provider_id)

        # 读取音频数据
        audio_data = await audio_file.read()

        # 创建记录
        record = await LLMVoiceRecord.create(
            record_id=f"asr_{audio_file.filename}",
            customer_id=current_user_id,
            model_id=provider_id,
            recognition_type="streaming",
            audio_file=audio_file.filename,
            audio_format=format,
            status="processing"
        )

        # 调用服务
        results = []
        async for result in service.streaming_asr(audio_data, format, sample_rate, language):
            results.append(result)

        # 更新记录
        if results:
            final_result = results[-1]
            await LLMVoiceRecord.filter(id=record.id).update(
                recognized_text=final_result.get("text", ""),
                confidence=final_result.get("confidence", 0),
                status="completed"
            )

        # 更新使用量
        await VoiceServiceHelper.update_voice_usage(service, tokens=100)

        return SuccessResponse(data={
            "record_id": record.record_id,
            "results": results
        })

    except Exception as e:
        logger.error(f"流式ASR失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"流式ASR失败: {str(e)}")


# ========== 2. 录音文件识别 ==========

@voice_router.post("/asr/file", summary="录音文件识别")
async def file_asr(
    audio_file: UploadFile,
    provider_id: int = Form(..., description="厂商ID"),
    format: str = Form("wav"),
    sample_rate: int = Form(16000),
    language: str = Form("zh"),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    上传音频文件进行语音识别
    """
    try:
        # 获取语音服务
        service = await VoiceServiceHelper.get_voice_service(provider_id)

        # 保存音频文件
        from base.plugins.llm.services.doubao_voice_service import DoubaoVoiceService
        audio_path = await DoubaoVoiceService.save_audio_file(await audio_file.read())

        # 创建记录
        record = await LLMVoiceRecord.create(
            record_id=f"file_asr_{audio_file.filename}",
            customer_id=current_user_id,
            model_id=provider_id,
            recognition_type="file",
            audio_file=audio_path,
            audio_format=format,
            status="processing"
        )

        # 调用服务
        result = await service.file_asr(audio_path, format, sample_rate, language)

        # 更新记录
        if result.get("result") == "success":
            await LLMVoiceRecord.filter(id=record.id).update(
                recognized_text=result.get("text", ""),
                confidence=result.get("confidence", 0),
                status="completed"
            )

        # 更新使用量
        await VoiceServiceHelper.update_voice_usage(service, tokens=100)

        return SuccessResponse(data={
            "record_id": record.record_id,
            "result": result
        })

    except Exception as e:
        logger.error(f"文件ASR失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件ASR失败: {str(e)}")


# ========== 3. 语音合成 ==========

@voice_router.post("/tts", summary="文字转语音")
async def text_to_speech(
    text: str = Form(..., min_length=1),
    provider_id: int = Form(..., description="厂商ID"),
    voice_type: str = Form("zh_female_shuangkuaisisi_moon_bigtts"),
    speed: float = Form(1.0),
    pitch: float = Form(1.0),
    volume: float = Form(1.0),
    format: str = Form("mp3"),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    文字转语音

    返回音频文件供下载
    """
    try:
        # 获取语音服务（自动使用语音专用API Key）
        service = await VoiceServiceHelper.get_voice_service(provider_id)

        # 创建记录
        record = await LLMTTSRecord.create(
            record_id=f"tts_{hash(text)}",
            customer_id=current_user_id,
            model_id=provider_id,
            input_text=text,
            text_length=len(text),
            voice_type=voice_type,
            speed=speed,
            pitch=pitch,
            volume=volume,
            audio_format=format,
            status="processing"
        )

        # 调用服务
        audio_data = await service.text_to_speech(
            text, voice_type, speed, pitch, volume, format
        )

        # 保存音频文件
        from base.plugins.llm.services.doubao_voice_service import DoubaoVoiceService
        audio_path = await DoubaoVoiceService.save_audio_file(audio_data)

        # 更新记录
        from pathlib import Path
        audio_size = len(audio_data)
        await LLMTTSRecord.filter(id=record.id).update(
            audio_file=audio_path,
            audio_size=audio_size,
            tokens=DoubaoVoiceService.estimate_tokens(text),
            status="completed"
        )

        # 更新使用量
        await VoiceServiceHelper.update_voice_usage(
            service,
            tokens=DoubaoVoiceService.estimate_tokens(text)
        )

        # 返回音频文件
        return FileResponse(
            path=audio_path,
            media_type=f"audio/{format}",
            filename=f"{record.record_id}.{format}"
        )

    except Exception as e:
        logger.error(f"TTS失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS失败: {str(e)}")


# ========== 4. 声音复刻 ==========

@voice_router.post("/clone/submit", summary="提交声音复刻任务")
async def submit_clone(
    reference_audio: UploadFile,
    provider_id: int = Form(..., description="厂商ID"),
    voice_name: str = Form(...),
    description: str = Form(""),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    提交声音复刻任务

    上传参考音频，创建自定义音色
    """
    try:
        # 获取语音服务
        service = await VoiceServiceHelper.get_voice_service(provider_id)

        # 保存参考音频
        from base.plugins.llm.services.doubao_voice_service import DoubaoVoiceService
        audio_path = await DoubaoVoiceService.save_audio_file(await reference_audio.read())

        # 创建记录
        clone = await LLMVoiceClone.create(
            clone_id=f"clone_{hash(audio_path)}",
            customer_id=current_user_id,
            model_id=provider_id,
            reference_audio=audio_path,
            voice_name=voice_name,
            voice_description=description,
            status="processing"
        )

        # 调用服务
        result = await service.clone_voice(audio_path, voice_name, description)

        # 更新记录
        if result.get("voice_id"):
            await LLMVoiceClone.filter(id=clone.id).update(
                voice_id=result.get("voice_id"),
                status="completed"
            )

        # 更新使用量
        await VoiceServiceHelper.update_voice_usage(service, tokens=100)

        return SuccessResponse(data={
            "clone_id": clone.clone_id,
            "voice_id": result.get("voice_id"),
            "status": "submitted"
        })

    except Exception as e:
        logger.error(f"声音复刻失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"声音复刻失败: {str(e)}")


@voice_router.get("/clone/{clone_id}", summary="查询声音复刻状态")
async def check_clone_status(
    clone_id: str,
    provider_id: int = Query(..., description="厂商ID"),
    current_user_id: int = Depends(get_current_user_id)
):
    """查询声音复刻任务状态"""
    try:
        service = await VoiceServiceHelper.get_voice_service(provider_id)
        result = await service.check_clone_status(clone_id)

        return SuccessResponse(data=result)

    except Exception as e:
        logger.error(f"查询复刻状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


# ========== 5. 同声传译 ==========

@voice_router.post("/translation/streaming", summary="同声传译")
async def streaming_translation(
    audio_file: UploadFile,
    provider_id: int = Form(..., description="厂商ID"),
    source_language: str = Form("zh"),
    target_language: str = Form("en"),
    format: str = Form("wav"),
    sample_rate: int = Form(16000),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    同声传译（流式）

    上传音频文件进行实时翻译
    """
    logger.info(f"[DEBUG] streaming_translation 函数开始执行")
    try:
        # 获取语音服务
        service = await VoiceServiceHelper.get_voice_service(provider_id)

        # 读取音频数据
        raw_audio_data = await audio_file.read()
        logger.info(f"[DEBUG] 原始音频数据大小: {len(raw_audio_data)} bytes")

        # 智能处理音频数据（支持Float32自动检测和转换）
        logger.info(f"[DEBUG] 开始导入 audio_format_utils")
        from base.plugins.llm.services.audio_format_utils import convert_audio_to_wav
        logger.info(f"[DEBUG] audio_format_utils 导入成功")

        logger.info(f"[DEBUG] 调用 convert_audio_to_wav...")
        audio_data, audio_info = convert_audio_to_wav(
            raw_audio_data,
            filename=audio_file.filename,
            sample_rate=sample_rate,
            channels=1,
            bits=16
        )
        logger.info(f"[DEBUG] convert_audio_to_wav 返回成功")

        logger.info(f"[音频处理] 原始大小: {audio_info['original_size']} bytes")
        logger.info(f"[音频处理] 原始格式: {audio_info['original_format']}")
        if audio_info.get('converted'):
            logger.info(f"[音频处理] ✅ 音频转换完成")
            logger.info(f"[音频处理] 最终大小: {audio_info['final_size']} bytes")
        else:
            logger.info(f"[音频处理] 格式: {audio_info['final_format']}")

        # 保存音频文件用于调试
        import time
        from pathlib import Path
        debug_dir = Path("debug_audio")
        debug_dir.mkdir(exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        debug_filename = debug_dir / f"translation_{timestamp}.wav"

        with open(debug_filename, 'wb') as f:
            f.write(audio_data)

        logger.info(f"[音频调试] 文件已保存: {debug_filename}")

        # 创建记录
        record = await LLMVoiceRecord.create(
            record_id=f"trans_{audio_file.filename}",
            customer_id=current_user_id,
            model_id=provider_id,
            recognition_type="translation",
            audio_file=audio_file.filename,
            audio_format=format,
            source_language=source_language,
            target_language=target_language,
            status="processing"
        )

        # 调用服务
        results = []
        final_result = None

        async for result in service.streaming_translation(
            audio_data, source_language, target_language, format, sample_rate
        ):
            results.append(result)

            # 最后一个是session_finished事件，包含完整结果
            if result.get("event") == "session_finished":
                final_result = result.get("result", {})

        # 更新记录
        if final_result:
            await LLMVoiceRecord.filter(id=record.id).update(
                recognized_text=final_result.get("source_text", ""),
                translated_text=final_result.get("translation_text", ""),
                status="completed"
            )

            # 更新使用量（如果有token信息）
            tokens = final_result.get("tokens", {})
            total_tokens = sum(tokens.values()) if tokens else 100
            await VoiceServiceHelper.update_voice_usage(service, tokens=int(total_tokens))
        else:
            # 如果没有最终结果，仍然更新使用量
            await VoiceServiceHelper.update_voice_usage(service, tokens=100)

        return SuccessResponse(data={
            "record_id": record.record_id,
            "results": results,
            "final_result": final_result
        })

    except Exception as e:
        logger.error(f"同声传译失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"同声传译失败: {str(e)}")


# ========== 查询接口 ==========

@voice_router.get("/records", summary="获取语音记录列表")
async def get_voice_records(
    recognition_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    current_user_id: int = Depends(get_current_user_id)
):
    """获取语音识别记录"""
    query = LLMVoiceRecord.filter(customer_id=current_user_id)

    if recognition_type:
        query = query.filter(recognition_type=recognition_type)
    if status:
        query = query.filter(status=status)

    total = await query.count()
    records = await query.offset((page - 1) * page_size).limit(page_size).order_by('-created_at')

    result = []
    for record in records:
        result.append({
            "id": record.id,
            "record_id": record.record_id,
            "recognition_type": record.recognition_type,
            "audio_file": record.audio_file,
            "recognized_text": record.recognized_text,
            "translated_text": record.translated_text,
            "status": record.status,
            "created_at": record.created_at.isoformat() if record.created_at else None
        })

    return SuccessResponse(data={
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size
    })


@voice_router.get("/tts/records", summary="获取语音合成记录")
async def get_tts_records(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    current_user_id: int = Depends(get_current_user_id)
):
    """获取语音合成记录"""
    query = LLMTTSRecord.filter(customer_id=current_user_id)

    if status:
        query = query.filter(status=status)

    total = await query.count()
    records = await query.offset((page - 1) * page_size).limit(page_size).order_by('-created_at')

    result = []
    for record in records:
        result.append({
            "id": record.id,
            "record_id": record.record_id,
            "input_text": record.input_text[:100] + "..." if record.input_text and len(record.input_text) > 100 else record.input_text,
            "voice_type": record.voice_type,
            "audio_file": record.audio_file,
            "status": record.status,
            "created_at": record.created_at.isoformat() if record.created_at else None
        })

    return SuccessResponse(data={
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size
    })
