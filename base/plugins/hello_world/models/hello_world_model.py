"""
hello_world Data Models
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class HelloWorldModel(BaseModel, TimestampMixin):
    """Hello World Model Example"""

    name = fields.CharField(max_length=100, description="Name")
    description = fields.TextField(description="Description", null=True)
    is_active = fields.BooleanField(default=True, description="Is Active")

    class Meta:
        table = "hello_world_model"
        table_description = "Hello World Model"
