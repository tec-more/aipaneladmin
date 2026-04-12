"""
Memory model
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class Memory(BaseModel, TimestampMixin):
    """Memory model"""
    
    agent = fields.ForeignKeyField("models.Agent", related_name="memories", description="Associated agent")
    content = fields.TextField(description="Memory content")
    type = fields.CharField(max_length=50, default="short_term", description="Memory type: short_term/long_term")
    importance = fields.FloatField(default=0.5, description="Memory importance (0-1)")
    recall_count = fields.IntField(default=0, description="Recall count")
    last_recalled_at = fields.DatetimeField(null=True, description="Last recalled time")
    
    class Meta:
        table = "memory"
    
    def __str__(self):
        return f"Memory for {self.agent.name}"