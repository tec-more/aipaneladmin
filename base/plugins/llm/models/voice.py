"""
语音相关数据模型
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin
import uuid


class LLMVoiceRecord(BaseModel, TimestampMixin):
    """语音识别记录表"""

    record_id = fields.CharField(max_length=64, unique=True, description="记录ID")
    customer_id = fields.IntField(description="客户ID")
    model_id = fields.IntField(description="使用的模型ID")

    # 识别类型：streaming（流式）、file（文件）、translation（同声传译）
    recognition_type = fields.CharField(max_length=20, description="识别类型")

    # 音频信息
    audio_file = fields.CharField(max_length=255, null=True, description="音频文件路径")
    audio_duration = fields.IntField(null=True, description="音频时长（秒）")
    audio_format = fields.CharField(max_length=20, null=True, description="音频格式")

    # 识别结果
    recognized_text = fields.TextField(null=True, description="识别的文本")
    confidence = fields.FloatField(null=True, description="识别置信度")

    # 同声传译相关
    source_language = fields.CharField(max_length=20, null=True, description="源语言")
    target_language = fields.CharField(max_length=20, null=True, description="目标语言")
    translated_text = fields.TextField(null=True, description="翻译结果")

    # 状态
    status = fields.CharField(max_length=20, default="processing", description="状态")
    error_message = fields.TextField(null=True, description="错误信息")

    # Token和费用
    audio_tokens = fields.IntField(default=0, description="音频token数")
    text_tokens = fields.IntField(default=0, description="文本token数")
    total_tokens = fields.IntField(default=0, description="总token数")
    cost = fields.DecimalField(max_digits=10, decimal_places=4, default=0, description="费用")

    class Meta:
        table = "llm_voice_record"

    def __str__(self):
        return f"{self.record_id}"


class LLMTTSRecord(BaseModel, TimestampMixin):
    """语音合成记录表"""

    record_id = fields.CharField(max_length=64, unique=True, description="记录ID")
    customer_id = fields.IntField(description="客户ID")
    model_id = fields.IntField(description="使用的模型ID")

    # 输入文本
    input_text = fields.TextField(description="要合成的文本")
    text_length = fields.IntField(description="文本长度")

    # 音频输出
    audio_file = fields.CharField(max_length=255, description="生成的音频文件路径")
    audio_duration = fields.IntField(description="音频时长（秒）")
    audio_format = fields.CharField(max_length=20, description="音频格式")
    audio_size = fields.IntField(description="音频大小（字节）")

    # 语音参数
    voice_type = fields.CharField(max_length=50, description="音色")
    speed = fields.FloatField(default=1.0, description="语速")
    pitch = fields.FloatField(default=1.0, description="音调")
    volume = fields.FloatField(default=1.0, description="音量")

    # 状态
    status = fields.CharField(max_length=20, default="processing", description="状态")
    error_message = fields.TextField(null=True, description="错误信息")

    # Token和费用
    tokens = fields.IntField(default=0, description="token数")
    cost = fields.DecimalField(max_digits=10, decimal_places=4, default=0, description="费用")

    class Meta:
        table = "llm_tts_record"

    def __str__(self):
        return f"{self.record_id}"


class LLMVoiceClone(BaseModel, TimestampMixin):
    """声音复刻记录表"""

    clone_id = fields.CharField(max_length=64, unique=True, description="复刻ID")
    customer_id = fields.IntField(description="客户ID")
    model_id = fields.IntField(description="使用的模型ID")

    # 参考音频
    reference_audio = fields.CharField(max_length=255, description="参考音频文件路径")
    reference_duration = fields.IntField(description="参考音频时长（秒）")

    # 复刻的音色信息
    voice_id = fields.CharField(max_length=100, unique=True, description="生成的音色ID")
    voice_name = fields.CharField(max_length=100, description="音色名称")
    voice_description = fields.TextField(null=True, description="音色描述")

    # 状态
    status = fields.CharField(max_length=20, default="processing", description="状态：processing/completed/failed")
    error_message = fields.TextField(null=True, description="错误信息")

    # 训练参数
    training_samples = fields.IntField(default=1, description="训练样本数")

    # 使用统计
    usage_count = fields.IntField(default=0, description="使用次数")

    class Meta:
        table = "llm_voice_clone"

    def __str__(self):
        return f"{self.clone_id}"
