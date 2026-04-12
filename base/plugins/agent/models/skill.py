"""
Skill model
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class Skill(BaseModel, TimestampMixin):
    """Skill model"""
    
    name = fields.CharField(max_length=100, description="Skill name")
    description = fields.TextField(null=True, description="Skill description")
    type = fields.CharField(max_length=50, description="Skill type")
    parameters = fields.JSONField(null=True, description="Skill parameters")
    implementation = fields.TextField(null=True, description="Skill implementation code")
    status = fields.CharField(max_length=20, default="active", description="Status: active/inactive")
    
    class Meta:
        table = "skill"
    
    def __str__(self):
        return self.name