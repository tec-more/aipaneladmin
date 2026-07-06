"""
审批规则 Service
"""
import ast
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from tortoise.expressions import Q
import fnmatch
from loguru import logger

from base.plugins.approval.models.approval_rule import ApprovalRule
from base.plugins.approval.models.approval_flow import ApprovalFlow
from base.plugins.approval.schemas.rule_schema import RuleCreate, RuleUpdate, RuleListQuery


# ---------------------------------------------------------------------------
# 插件扫描：业务模型（service）与 ORM 模型（中文名）元数据
# ---------------------------------------------------------------------------
_PLUGIN_SCAN_CACHE = None


def _snake(name: str) -> str:
    """CamelCase -> snake_case。"""
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _is_tortoise_model(node) -> bool:
    """粗略判断 AST 节点是否为 Tortoise 模型类。"""
    if not isinstance(node, ast.ClassDef):
        return False
    for stmt in node.body:
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Meta":
            return True
    for base in node.bases:
        bname = base.id if isinstance(base, ast.Name) else (base.attr if isinstance(base, ast.Attribute) else "")
        if bname in ("Model", "BaseModel", "TimestampMixin"):
            return True
    return False


def _scan_plugins():
    """扫描所有插件，返回 (services, model_meta)。
    services: [{"model", "plugin", "methods"}]
    model_meta: {plugin: [{"table","classname","verbose_name","table_description"}]}
    """
    global _PLUGIN_SCAN_CACHE
    if _PLUGIN_SCAN_CACHE is not None:
        return _PLUGIN_SCAN_CACHE

    plugins_dir = Path(__file__).resolve().parent.parent.parent
    services: List[Dict[str, Any]] = []
    model_meta: Dict[str, List[Dict[str, Any]]] = {}

    for plugin_dir in plugins_dir.iterdir():
        if not plugin_dir.is_dir():
            continue
        plugin = plugin_dir.name
        services_dir = plugin_dir / "services"
        models_dir = plugin_dir / "models"

        if services_dir.is_dir():
            for service_file in services_dir.rglob("*.py"):
                if service_file.name == "__init__.py":
                    continue
                try:
                    tree = ast.parse(service_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                for node in ast.walk(tree):
                    if not isinstance(node, ast.ClassDef):
                        continue
                    has_base = any(
                        (isinstance(b, ast.Name) and b.id == "BaseBusinessService")
                        or (isinstance(b, ast.Attribute) and b.attr == "BaseBusinessService")
                        for b in node.bases
                    )
                    if not has_base:
                        continue
                    model_val = None
                    for stmt in node.body:
                        if isinstance(stmt, ast.Assign):
                            for t in stmt.targets:
                                if isinstance(t, ast.Name) and t.id == "model":
                                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                                        model_val = stmt.value.value
                                    break
                    if not model_val:
                        continue
                    methods = {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
                    services.append({"model": model_val, "plugin": plugin, "methods": methods})

        if models_dir.is_dir():
            for model_file in models_dir.rglob("*.py"):
                if model_file.name in ("__init__.py", "base.py"):
                    continue
                try:
                    tree = ast.parse(model_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                for node in ast.walk(tree):
                    if not _is_tortoise_model(node):
                        continue
                    table = None
                    verbose_name = None
                    table_description = None
                    for stmt in node.body:
                        if isinstance(stmt, ast.Assign):
                            for t in stmt.targets:
                                if isinstance(t, ast.Name) and t.id == "verbose_name":
                                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                                        verbose_name = stmt.value.value
                        elif isinstance(stmt, ast.ClassDef) and stmt.name == "Meta":
                            for mstmt in stmt.body:
                                if isinstance(mstmt, ast.Assign):
                                    for mt in mstmt.targets:
                                        if isinstance(mt, ast.Name) and mt.id == "table":
                                            if isinstance(mstmt.value, ast.Constant) and isinstance(mstmt.value.value, str):
                                                table = mstmt.value.value
                                        if isinstance(mt, ast.Name) and mt.id == "table_description":
                                            if isinstance(mstmt.value, ast.Constant) and isinstance(mstmt.value.value, str):
                                                table_description = mstmt.value.value
                    model_meta.setdefault(plugin, []).append({
                        "table": table,
                        "classname": node.name,
                        "verbose_name": verbose_name,
                        "table_description": table_description,
                    })

    _PLUGIN_SCAN_CACHE = (services, model_meta)
    return _PLUGIN_SCAN_CACHE


class RuleService:
    """审批规则服务"""

    @staticmethod
    def get_available_models() -> List[Dict[str, str]]:
        """获取所有可用的业务模型（用于审批规则配置）。

        标识（model）取自各插件的 ``BaseBusinessService`` 子类（审批门禁实际使用的标识），
        中文名优先读取 ORM 模型类的 ``verbose_name``，其次 ``Meta.table_description``，
        再回退到 model 本身。展示格式：``中文(model)``。
        """
        services, model_meta = _scan_plugins()
        result: List[Dict[str, str]] = []
        for s in services:
            model = s["model"]
            plugin = s["plugin"]
            cn = None
            for m in model_meta.get(plugin, []):
                tbl = m["table"] or ""
                stripped = tbl[len(plugin) + 1:] if tbl.startswith(plugin + "_") else tbl
                match = (
                    tbl == model
                    or tbl == f"{plugin}_{model}"
                    or _snake(m["classname"]) == model
                    or stripped == model
                )
                if match:
                    cn = m["verbose_name"] or m["table_description"]
                    break
            label = f"{cn}({model})" if cn else model
            result.append({"model": model, "label": label})
        result.sort(key=lambda x: x["model"])
        return result

    @staticmethod
    def get_model_actions(model: str) -> List[Dict[str, str]]:
        """按 model 找到对应的 BaseBusinessService 子类，返回其可配置的执行动作。

        动作即 service 的公开写操作方法 create/update/delete（BaseBusinessService 均具备），
        与 ``gate_write`` 使用的 action 一致，可用于审批通过后的回调执行与规则匹配。
        """
        services, _ = _scan_plugins()
        for s in services:
            if s["model"] != model:
                continue
            return [
                {"value": "create", "label": "创建(create)"},
                {"value": "update", "label": "更新(update)"},
                {"value": "delete", "label": "删除(delete)"},
            ]
        return []

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
            action=data.action,
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
        根据业务模型和方法获取匹配的规则（按 model + methods + action 匹配，废弃 path_pattern）。
        """
        action = {"POST": "create", "PUT": "update", "DELETE": "delete"}.get(method)
        rules = await ApprovalRule.filter(is_active=True, model=model).order_by("-priority").all()
        for rule in rules:
            if method not in rule.methods:
                continue
            # 规则指定了 action 时，仅匹配该动作；未指定则匹配全部动作（向后兼容）
            if rule.action and action and rule.action != action:
                continue
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
