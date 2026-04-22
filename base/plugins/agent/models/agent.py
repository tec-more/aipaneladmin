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
    graph_definition = fields.JSONField(null=True, description="Agent graph definition (nodes and edges)")
    memory_capacity = fields.IntField(default=100, description="Memory capacity")
    system_prompt = fields.TextField(null=True, description="System prompt")
    reasoning_strategy = fields.CharField(
        max_length=20,
        default="function_call",
        description="Reasoning strategy: function_call/react"
    )
    
    class Meta:
        table = "agent"
    
    def __str__(self):
        return self.name