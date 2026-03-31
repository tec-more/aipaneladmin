"""
豆包语音API接口
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional
import logging
import json

from base.common.response import SuccessResponse
from base.common.security import get_current_user_id
from base.plugins.llm.models.voice import LLMVoiceRecord, LLMTTSRecord, LLMVoiceClone
from base.plugins.llm.models.model import LLMModel

logger = logging.getLogger(__name__)

voice_router = APIRouter(
    prefix="/voice",
    tags=["语音服务"],
    dependencies=[Depends(get_current_user_id)]
)

# 导入服务
try:
    from base.plugins.llm.services.doubao_voice_service import DoubaoVoiceService
except ImportError:
    DoubaoVoiceService = None


# ========== 1. 流式语音识别 ==========

@voice_router.post("/asr/streaming", summary="流式语音识别")
async def streaming_asr(
    audio_file: UploadFile,
    format: str = Form("wav"),
    sample_rate: int = Form(16000),
    language: str = Form("zh"),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    流式语音识别（实时）

    上传音频文件进行实时语音识别
    """
    if not DoubaoVoiceService:
        raise HTTPException(status_code=500, detail="语音服务未配置")

    try:
        # 读取音频数据
        audio_data = await audio_file.read()

        # 创建记录
        record = await LLMVoiceRecord.create(
            record_id=f"asr_{audio_file.filename}",
            customer_id=current_user_id,
            model_id=0,  # TODO: 获取语音模型ID
            recognition_type="streaming",
            audio_file=audio_file.filename,
            audio_format=format,
            status="processing"
        )

        # 调用服务
        service = DoubaoVoiceService(api_key="your_api_key")  # TODO: 从API密钥表获取

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
    format: str = Form("wav"),
    sample_rate: int = Form(16000),
    language: str = Form("zh"),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    上传音频文件进行语音识别
    """
    if not DoubaoVoiceService:
        raise HTTPException(status_code=500, detail="语音服务未配置")

    try:
        # 保存音频文件
        audio_path = await DoubaoVoiceService.save_audio_file(await audio_file.read())

        # 创建记录
        record = await LLMVoiceRecord.create(
            record_id=f"file_asr_{audio_file.filename}",
            customer_id=current_user_id,
            model_id=0,
            recognition_type="file",
            audio_file=audio_path,
            audio_format=format,
            status="processing"
        )

        # 调用服务
        service = DoubaoVoiceService(api_key="your_api_key")  # TODO: 从API密钥表获取
        result = await service.file_asr(audio_path, format, sample_rate, language)

        # 更新记录
        if result.get("result") == "success":
            await LLMVoiceRecord.filter(id=record.id).update(
                recognized_text=result.get("text", ""),
                confidence=result.get("confidence", 0),
                status="completed"
            )

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
    if not DoubaoVoiceService:
        raise HTTPException(status_code=500, detail="语音服务未配置")

    try:
        # 创建记录
        record = await LLMTTSRecord.create(
            record_id=f"tts_{hash(text)}",
            customer_id=current_user_id,
            model_id=0,
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
        service = DoubaoVoiceService(api_key="your_api_key")  # TODO: 从API密钥表获取
        audio_data = await service.text_to_speech(
            text, voice_type, speed, pitch, volume, format
        )

        # 保存音频文件
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
    voice_name: str = Form(...),
    description: str = Form(""),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    提交声音复刻任务

    上传参考音频，创建自定义音色
    """
    if not DoubaoVoiceService:
        raise HTTPException(status_code=500, detail="语音服务未配置")

    try:
        # 保存参考音频
        audio_path = await DoubaoVoiceService.save_audio_file(await reference_audio.read())

        # 创建记录
        clone = await LLMVoiceClone.create(
            clone_id=f"clone_{hash(audio_path)}",
            customer_id=current_user_id,
            model_id=0,
            reference_audio=audio_path,
            voice_name=voice_name,
            voice_description=description,
            status="processing"
        )

        # 调用服务
        service = DoubaoVoiceService(api_key="your_api_key")  # TODO: 从API密钥表获取
        result = await service.clone_voice(audio_path, voice_name, description)

        # 更新记录
        if result.get("voice_id"):
            await LLMVoiceClone.filter(id=clone.id).update(
                voice_id=result.get("voice_id"),
                status="completed"
            )

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
    current_user_id: int = Depends(get_current_user_id)
):
    """查询声音复刻任务状态"""
    if not DoubaoVoiceService:
        raise HTTPException(status_code=500, detail="语音服务未配置")

    try:
        service = DoubaoVoiceService(api_key="your_api_key")  # TODO: 从API密钥表获取
        result = await service.check_clone_status(clone_id)

        return SuccessResponse(data=result)

    except Exception as e:
        logger.error(f"查询复刻状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


# ========== 5. 同声传译 ==========

@voice_router.post("/translation/streaming", summary="同声传译")
async def streaming_translation(
    audio_file: UploadFile,
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
    if not DoubaoVoiceService:
        raise HTTPException(status_code=500, detail="语音服务未配置")

    try:
        # 读取音频数据
        audio_data = await audio_file.read()

        # 创建记录
        record = await LLMVoiceRecord.create(
            record_id=f"trans_{audio_file.filename}",
            customer_id=current_user_id,
            model_id=0,
            recognition_type="translation",
            audio_file=audio_file.filename,
            audio_format=format,
            source_language=source_language,
            target_language=target_language,
            status="processing"
        )

        # 调用服务
        service = DoubaoVoiceService(api_key="your_api_key")  # TODO: 从API密钥表获取

        results = []
        async for result in service.streaming_translation(
            audio_data, source_language, target_language, format, sample_rate
        ):
            results.append(result)

        # 更新记录
        if results:
            final_result = results[-1]
            await LLMVoiceRecord.filter(id=record.id).update(
                recognized_text=final_result.get("source_text", ""),
                translated_text=final_result.get("target_text", ""),
                status="completed"
            )

        return SuccessResponse(data={
            "record_id": record.record_id,
            "results": results
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
