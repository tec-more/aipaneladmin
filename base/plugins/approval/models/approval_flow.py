"""
审批流程定义模型
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class ApprovalFlow(BaseModel, TimestampMixin):
    """审批流程定义"""
    name = fields.CharField(max_length=100, description="流程名称", index=True)
    code = fields.CharField(max_length=100, unique=True, description="流程编码", index=True)
    description = fields.TextField(null=True, description="流程描述")
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)
    # 表单配置（JSON格式，定义审批表单字段）
    form_config = fields.JSONField(default=list, description="表单配置")
    # 流程配置（JSON格式，定义节点、连线、条件等）
    flow_config = fields.JSONField(default=dict, description="流程配置")
    # 业务类型标识（如：purchase_order、expense、leave 等）
    business_type = fields.CharField(max_length=50, null=True, description="业务类型", index=True)
    # 是否为系统预设流程（预设流程不可删除）
    is_system = fields.BooleanField(default=False, description="是否系统预设")

    class Meta:
        table = "approval_flow"
        ordering = ["-created_at"]

    async def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "is_active": self.is_active,
            "form_config": self.form_config,
            "flow_config": self.flow_config,
            "business_type": self.business_type,
            "is_system": self.is_system,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
