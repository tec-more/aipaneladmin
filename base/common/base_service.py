"""
基础业务 Service 基类 —— 内置审批门禁。

继承方式：:

    class PurchaseOrderService(BaseBusinessService):
        model = "purchase_order"  # 必填：与审批流程规则(approval_flow.model)对应

        # 可选：覆盖 _do_* 实现单号生成 / 级联写子表等定制逻辑。
        # 不覆盖时，基类提供通用默认实现（按 model 解析 ORM 直接落库）。
        @classmethod
        async def _do_create(cls, data: dict) -> Any:
            '''真正创建（不带门禁），审批通过后由执行器回调。'''
            ...

路由调用：:

    # 创建（自动门禁）
    order = await PurchaseOrderService.create(data.dict())
    # 更新（自动门禁）
    order = await PurchaseOrderService.update(order_id, data.dict())
    # 删除（自动门禁）
    success = await PurchaseOrderService.delete(order_id)

设计要点：
- ``model`` 决定查哪条审批流程规则(approval_flow)；命中则自动建审批实例并抛 NeedApprovalError。
- ``_do_create/_do_update/_do_delete`` 在基类提供通用默认实现（按 ``cls.model``
  解析 Tortoise ORM 模型直接 CRUD）；子类覆盖则优先使用子类版本。
- ``_do_*`` 在 ``__init_subclass__`` 时自动注册到执行器，审批通过后回调（不经过门禁）。
- 判定异常默认放行（不阻断业务）。
"""

import re

from typing import Any, Callable, Dict, Optional

from loguru import logger


def _snake(name: str) -> str:
    """CamelCase -> snake_case。"""
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class BaseBusinessService:
    """业务 Service 基类 —— 声明 model 即可自动接入审批门禁与执行器。"""

    model: Optional[str] = None
    """业务模型标识，对应审批流程规则(approval_flow.model)，子类必须重写。"""

    # ------------------------------------------------------------------
    # 自动注册执行器（__init_subclass__）
    # ------------------------------------------------------------------
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.model is None:
            return
        try:
            from base.plugins.approval.services.approval_gate import register_executor

            for action, method_name in (("create", "_do_create"),
                                        ("update", "_do_update"),
                                        ("delete", "_do_delete")):
                # 始终注册：_do_* 由基类提供通用默认实现，子类覆盖则优先使用子类版本
                register_executor(cls.model, action, cls, method_name)
                logger.debug(
                    f"[BaseService] 注册执行器: {cls.model}/{action} → "
                    f"{cls.__name__}.{method_name}"
                )
        except Exception as e:
            logger.warning(
                f"[BaseService] {cls.__name__} 执行器注册失败（审批插件未就绪？）: {e}"
            )

    # ------------------------------------------------------------------
    # 子类可覆盖的操作（通用默认实现，按 cls.model 自动解析 ORM 落库）
    # ------------------------------------------------------------------
    @classmethod
    def _resolve_orm_model(cls):
        """按 ``cls.model`` 解析对应的 Tortoise ORM 模型类；找不到返回 None。

        遍历已注册的 Tortoise 模型，按 ``_snake(类名) == cls.model`` 或
        ``_meta.db_table == cls.model`` 匹配。
        """
        if not cls.model:
            return None
        try:
            from tortoise import Tortoise
        except ImportError:
            return None
        target = cls.model
        for _app_label, models in Tortoise.apps.items():
            for name, m in models.items():
                meta = getattr(m, "_meta", None)
                db_table = getattr(meta, "db_table", None) if meta else None
                if _snake(name) == target or db_table == target:
                    return m
        return None

    @classmethod
    async def _do_create(cls, data: Dict[str, Any]) -> Any:
        """通用默认创建（不带门禁）：按 cls.model 解析 ORM 模型直接落库。

        子类可覆盖以实现单号生成、级联写子表等定制逻辑。``getattr`` 会优先
        使用子类覆盖版本。
        """
        model_cls = cls._resolve_orm_model()
        if model_cls is None:
            raise NotImplementedError(
                f"{cls.__name__} 无法解析业务模型 {cls.model!r}，未实现 _do_create"
            )
        db_fields = set(model_cls._meta.db_fields)
        clean = {k: v for k, v in (data or {}).items()
                 if k in db_fields and k != "id"}
        return await model_cls.create(**clean)

    @classmethod
    async def _do_update(cls, obj_id: int, data: Dict[str, Any]) -> Any:
        """通用默认更新（不带门禁）：按 id 取对象并写入合法字段。"""
        model_cls = cls._resolve_orm_model()
        if model_cls is None:
            raise NotImplementedError(
                f"{cls.__name__} 无法解析业务模型 {cls.model!r}，未实现 _do_update"
            )
        obj = await model_cls.get_or_none(id=obj_id)
        if obj is None:
            return None
        db_fields = set(model_cls._meta.db_fields)
        for k, v in (data or {}).items():
            if k in db_fields and k != "id" and v is not None:
                setattr(obj, k, v)
        await obj.save()
        return obj

    @classmethod
    async def _do_delete(cls, obj_id: int) -> bool:
        """通用默认删除（不带门禁）：按 id 删除对象。"""
        model_cls = cls._resolve_orm_model()
        if model_cls is None:
            raise NotImplementedError(
                f"{cls.__name__} 无法解析业务模型 {cls.model!r}，未实现 _do_delete"
            )
        obj = await model_cls.get_or_none(id=obj_id)
        if obj is None:
            return False
        await obj.delete()
        return True

    # ------------------------------------------------------------------
    # 公开门禁方法（路由层调用）
    # ------------------------------------------------------------------

    @classmethod
    async def create(cls, data: Dict[str, Any]) -> Any:
        """
        创建（带审批门禁）。

        命中规则：自动建审批实例并抛 NeedApprovalError（40001）。
        未命中：直接执行 ``_do_create(data)``（通用默认或子类覆盖版本）。
        """
        await cls._gate("create", payload=data)
        fn = getattr(cls, "_do_create", None)
        if fn is None:
            raise NotImplementedError(
                f"{cls.__name__} 未实现 _do_create，无法执行 create()"
            )
        return await fn(data)

    @classmethod
    async def update(cls, obj_id: int, data: Dict[str, Any]) -> Any:
        """
        更新（带审批门禁）。

        命中规则：自动建审批实例并抛 NeedApprovalError（40001）。
        未命中：直接执行 ``_do_update(obj_id, data)``。
        """
        await cls._gate("update", payload=data, business_id=obj_id)
        fn = getattr(cls, "_do_update", None)
        if fn is None:
            raise NotImplementedError(
                f"{cls.__name__} 未实现 _do_update，无法执行 update()"
            )
        return await fn(obj_id, data)

    @classmethod
    async def delete(cls, obj_id: int) -> bool:
        """
        删除（带审批门禁）。

        命中规则：自动建审批实例并抛 NeedApprovalError（40001）。
        未命中：直接执行 ``_do_delete(obj_id)``。
        """
        await cls._gate("delete", business_id=obj_id)
        fn = getattr(cls, "_do_delete", None)
        if fn is None:
            raise NotImplementedError(
                f"{cls.__name__} 未实现 _do_delete，无法执行 delete()"
            )
        return await fn(obj_id)

    # ------------------------------------------------------------------
    # 内部：门禁调用
    # ------------------------------------------------------------------

    @classmethod
    async def _gate(
        cls,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        business_id: Optional[int] = None,
    ) -> None:
        """调用 gate_write，命中规则则抛异常；否则静默返回。"""
        try:
            from base.plugins.approval.services.approval_gate import gate_write

            await gate_write(
                model=cls.model,
                action=action,
                payload=payload,
                business_id=business_id,
            )
        except Exception:
            # gate_write 内部已处理 NeedApprovalError（上抛）和判定异常（放行），
            # 这里只兜底意外情况，均放行。
            logger.exception(f"[BaseService] {cls.model}/{action} 门禁异常，放行")
