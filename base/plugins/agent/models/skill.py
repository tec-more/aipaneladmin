"""
Skill model
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class Skill(BaseModel, TimestampMixin):
    """Skill model"""
    
    name = fields.CharField(max_length=100, description="Skill name")
    description = fields.TextField(null=True, description="Skill description")
    implementation = fields.TextField(null=True, description="Skill content (Markdown format)")
    status = fields.CharField(max_length=20, default="active", description="Status: active/inactive")
    category = fields.ForeignKeyField(
        "models.SkillCategory", 
        related_name="skills", 
        null=True, 
        on_delete=fields.SET_NULL,
        description="Skill category"
    )
    
    class Meta:
        table = "skill"
    
    def __str__(self):
        return self.name
