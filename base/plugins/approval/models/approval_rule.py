"""
审批规则配置模型
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class ApprovalRule(BaseModel, TimestampMixin):
    """审批规则配置（中间件拦截依据）"""
    # 业务类型标识
    business_type = fields.CharField(max_length=50, description="业务类型", index=True)
    # 路径匹配模式（支持通配符 *，如 /v1/purchase/orders*）
    path_pattern = fields.CharField(max_length=255, description="路径匹配模式", index=True)
    # 需要拦截的HTTP方法列表
    methods = fields.JSONField(default=["POST", "PUT", "DELETE"], description="拦截方法列表")
    # 关联的审批流程ID
    flow_id = fields.IntField(description="关联审批流程ID", index=True)
    # 是否启用
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)
    # 优先级（数字越大优先级越高）
    priority = fields.IntField(default=0, description="优先级", index=True)
    # 规则说明
    description = fields.TextField(null=True, description="规则说明")

    class Meta:
        table = "approval_rule"
        ordering = ["-priority", "-created_at"]

    async def to_dict(self):
        """转换为字典"""
        flow = await ApprovalFlow.get_or_none(id=self.flow_id)
        return {
            "id": self.id,
            "business_type": self.business_type,
            "path_pattern": self.path_pattern,
            "methods": self.methods,
            "flow_id": self.flow_id,
            "flow_name": flow.name if flow else None,
            "is_active": self.is_active,
            "priority": self.priority,
            "description": self.description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }


# 延迟导入避免循环引用
from base.plugins.approval.models.approval_flow import ApprovalFlow
