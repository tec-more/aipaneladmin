"""
审批规则 Service
"""
import ast
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from tortoise.expressions import Q
import fnmatch
from loguru import logger

from base.plugins.approval.models.approval_rule import ApprovalRule
from base.plugins.approval.models.approval_flow import ApprovalFlow
from base.plugins.approval.schemas.rule_schema import RuleCreate, RuleUpdate, RuleListQuery


class RuleService:
    """审批规则服务"""

    @staticmethod
    def get_available_models() -> List[str]:
        """获取所有可用的业务模型。

        优先读取运行时注册表 APPROVAL_EXECUTORS；同时扫描所有插件 services/ 目录，
        通过 AST 解析继承自 BaseBusinessService 且声明了 model 类属性的 service 文件，
        把未在运行时注册的 model 也纳入列表，确保前端下拉框能看到全部模型。
        """
        from base.plugins.approval.services.approval_gate import APPROVAL_EXECUTORS

        models: Set[str] = {model for (model, _action) in APPROVAL_EXECUTORS.keys()}

        try:
            plugins_dir = Path(__file__).resolve().parent.parent.parent
            for services_dir in plugins_dir.glob("*/services"):
                if not services_dir.is_dir():
                    continue
                for service_file in services_dir.rglob("*.py"):
                    if service_file.name == "__init__.py":
                        continue
                    try:
                        source = service_file.read_text(encoding="utf-8")
                        tree = ast.parse(source)
                    except Exception:
                        continue
                    for node in ast.walk(tree):
                        if not isinstance(node, ast.ClassDef):
                            continue
                        # 判断是否继承 BaseBusinessService
                        has_base = any(
                            (isinstance(base, ast.Name) and base.id == "BaseBusinessService")
                            or (isinstance(base, ast.Attribute) and base.attr == "BaseBusinessService")
                            for base in node.bases
                        )
                        if not has_base:
                            continue
                        # 查找 model = "xxx" 的类属性
                        for stmt in node.body:
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if isinstance(target, ast.Name) and target.id == "model":
                                        value = stmt.value
                                        if isinstance(value, ast.Constant) and isinstance(value.value, str):
                                            models.add(value.value)
                                        elif isinstance(value, ast.Str):
                                            models.add(value.s)
                                        break
        except Exception as e:
            logger.warning(f"扫描业务模型失败: {e}")

        return sorted(models)

    @staticmethod
    async def create_rule(data: RuleCreate) -> ApprovalRule:
        """创建规则"""
        # 检查流程是否存在
        flow = await ApprovalFlow.get_or_none(id=data.flow_id)
        if not flow:
            raise ValueError("关联的审批流程不存在")

        rule = await ApprovalRule.create(
            business_type=data.business_type,
            model=data.model or data.business_type,
            path_pattern=data.path_pattern,
            methods=data.methods,
            flow_id=data.flow_id,
            is_active=data.is_active,
            priority=data.priority,
            description=data.description
        )
        return rule

    @staticmethod
    async def update_rule(rule_id: int, data: RuleUpdate) -> Optional[ApprovalRule]:
        """更新规则"""
        rule = await ApprovalRule.get_or_none(id=rule_id)
        if not rule:
            return None

        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(rule, key, value)

        await rule.save()
        return rule

    @staticmethod
    async def delete_rule(rule_id: int) -> bool:
        """删除规则"""
        rule = await ApprovalRule.get_or_none(id=rule_id)
        if not rule:
            return False
        await rule.delete()
        return True

    @staticmethod
    async def get_rule(rule_id: int) -> Optional[ApprovalRule]:
        """获取规则"""
        return await ApprovalRule.get_or_none(id=rule_id)

    @staticmethod
    async def get_rule_list(query: RuleListQuery) -> Dict[str, Any]:
        """获取规则列表"""
        q = Q()
        if query.business_type:
            q &= Q(business_type=query.business_type)
        if query.is_active is not None:
            q &= Q(is_active=query.is_active)

        total = await ApprovalRule.filter(q).count()
        rules = await ApprovalRule.filter(q).offset(
            (query.page - 1) * query.page_size
        ).limit(query.page_size)

        return {
            "total": total,
            "items": [await r.to_dict() for r in rules],
            "page": query.page,
            "page_size": query.page_size
        }

    @staticmethod
    async def toggle_rule_status(rule_id: int, is_active: bool) -> Optional[ApprovalRule]:
        """切换规则启用状态"""
        rule = await ApprovalRule.get_or_none(id=rule_id)
        if not rule:
            return None
        rule.is_active = is_active
        await rule.save()
        return rule

    @staticmethod
    async def get_matched_rule(path: str, method: str) -> Optional[ApprovalRule]:
        """
        根据路径和方法获取匹配的规则
        支持通配符匹配（如 /v1/purchase/orders*）
        """
        # 获取所有启用的规则，按优先级排序
        rules = await ApprovalRule.filter(is_active=True).order_by("-priority").all()

        for rule in rules:
            # 方法匹配
            if method not in rule.methods:
                continue

            # 路径匹配（支持通配符）
            if RuleService.match_path(rule.path_pattern, path):
                return rule

        return None

    @staticmethod
    def match_path(pattern: str, path: str) -> bool:
        """路径匹配（支持通配符 *）"""
        # 去除前缀 /api 和 /v1 进行匹配
        normalized_path = path
        if normalized_path.startswith("/api"):
            normalized_path = normalized_path[4:]
        if normalized_path.startswith("/v1"):
            normalized_path = normalized_path[3:]

        normalized_pattern = pattern
        if normalized_pattern.startswith("/api"):
            normalized_pattern = normalized_pattern[4:]
        if normalized_pattern.startswith("/v1"):
            normalized_pattern = normalized_pattern[3:]

        # 使用 fnmatch 进行通配符匹配
        if fnmatch.fnmatch(normalized_path, normalized_pattern):
            return True

        # 也支持精确匹配和前缀匹配
        if normalized_path == normalized_pattern:
            return True
        if normalized_pattern.endswith("*") and normalized_path.startswith(normalized_pattern[:-1]):
            return True

        return False

    @staticmethod
    async def check_approval_required(path: str, method: str) -> Dict[str, Any]:
        """
        检查指定路径和方法是否需要审批
        返回: {
            "require_approval": bool,
            "flow_id": int,
            "flow_name": str,
            "rule_id": int
        }
        """
        rule = await RuleService.get_matched_rule(path, method)

        if not rule:
            return {
                "require_approval": False,
                "flow_id": None,
                "flow_name": None,
                "rule_id": None
            }

        flow = await ApprovalFlow.get_or_none(id=rule.flow_id)
        if not flow or not flow.is_active:
            return {
                "require_approval": False,
                "flow_id": None,
                "flow_name": None,
                "rule_id": None
            }

        return {
            "require_approval": True,
            "flow_id": flow.id,
            "flow_name": flow.name,
            "rule_id": rule.id
        }

    @staticmethod
    async def get_matched_rule_by_model(model: str, method: str) -> Optional[ApprovalRule]:
        """
        根据业务模型和方法获取匹配的规则（按 model + methods 匹配，废弃 path_pattern）。
        """
        rules = await ApprovalRule.filter(is_active=True, model=model).order_by("-priority").all()
        for rule in rules:
            if method in rule.methods:
                return rule
        return None

    @staticmethod
    async def check_approval_required_by_model(model: str, method: str) -> Dict[str, Any]:
        """
        根据业务模型和方法检查是否需要审批（基于模型匹配的核心入口）。
        返回: {
            "require_approval": bool,
            "flow_id": int,
            "flow_name": str,
            "rule_id": int,
            "model": str
        }
        """
        rule = await RuleService.get_matched_rule_by_model(model, method)
        if not rule:
            return {
                "require_approval": False,
                "flow_id": None,
                "flow_name": None,
                "rule_id": None,
                "model": model
            }

        flow = await ApprovalFlow.get_or_none(id=rule.flow_id)
        if not flow or not flow.is_active:
            return {
                "require_approval": False,
                "flow_id": None,
                "flow_name": None,
                "rule_id": None,
                "model": model
            }

        return {
            "require_approval": True,
            "flow_id": flow.id,
            "flow_name": flow.name,
            "rule_id": rule.id,
            "model": model
        }
