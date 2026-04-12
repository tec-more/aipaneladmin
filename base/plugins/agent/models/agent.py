"""
Agent model
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class Agent(BaseModel, TimestampMixin):
    """Agent model"""
    
    name = fields.CharField(max_length=100, description="Agent name")
    description = fields.TextField(null=True, description="Agent description")
    status = fields.CharField(max_length=20, default="active", description="Status: active/inactive")
    config = fields.JSONField(null=True, description="Agent configuration")
    memory_capacity = fields.IntField(default=100, description="Memory capacity")
    skills = fields.ManyToManyField("models.Skill", related_name="agents", description="Associated skills")
    
    class Meta:
        table = "agent"
    
    def __str__(self):
        return self.name