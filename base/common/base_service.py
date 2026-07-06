"""
基础业务 Service 基类 —— 内置审批门禁。

继承方式：:

    class PurchaseOrderService(BaseBusinessService):
        model = "purchase_order"  # 必填：与 approval_rule.model 对应

        @classmethod
        async def _do_create(cls, data: dict) -> Any:
            '''真正创建（不带门禁），审批通过后由执行器回调。'''
            ...

        @classmethod
        async def _do_update(cls, obj_id: int, data: dict) -> Any:
            '''真正更新（不带门禁）。'''
            ...

        @classmethod
        async def _do_delete(cls, obj_id: int) -> bool:
            '''真正删除（不带门禁）。'''
            ...

        # 以下读操作保持不变（不经过门禁）
        @staticmethod
        async def get_by_id(id): ...

路由调用：:

    # 创建（自动门禁）
    order = await PurchaseOrderService.create(data.dict())
    # 更新（自动门禁）
    order = await PurchaseOrderService.update(order_id, data.dict())
    # 删除（自动门禁）
    success = await PurchaseOrderService.delete(order_id)

设计要点：
- ``model`` 决定查哪条 approval_rule；命中则自动建审批实例并抛 NeedApprovalError。
- ``_do_*`` 方法在 ``__init_subclass__`` 时自动注册到执行器，审批通过后回调（不经过门禁）。
- 判定异常默认放行（不阻断业务）。
"""

from typing import Any, Callable, Dict, Optional

from loguru import logger


class BaseBusinessService:
    """业务 Service 基类 —— 声明 model 即可自动接入审批门禁与执行器。"""

    model: Optional[str] = None
    """业务模型标识，对应 approval_rule.model，子类必须重写。"""

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
                raw_method = cls.__dict__.get(method_name)
                if raw_method is not None:
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
    # 子类可覆盖的操作
    # ------------------------------------------------------------------
    # _do_create / _do_update / _do_delete 是子类的真实实现（不带门禁）。
    # 如果子类未覆盖，说明该操作不支持，调用 create/update/delete 时会
    # 抛出 NotImplementedError。

    # ------------------------------------------------------------------
    # 公开门禁方法（路由层调用）
    # ------------------------------------------------------------------

    @classmethod
    async def create(cls, data: Dict[str, Any]) -> Any:
        """
        创建（带审批门禁）。

        命中规则：自动建审批实例并抛 NeedApprovalError（40001）。
        未命中：直接执行 ``_do_create(data)``。
        未定义 ``_do_create``：抛出 NotImplementedError。
        """
        await cls._gate("create", payload=data)
        method = cls.__dict__.get("_do_create")
        if method is None:
            raise NotImplementedError(
                f"{cls.__name__} 未实现 _do_create，无法执行 create()"
            )
        return await method(cls, data)

    @classmethod
    async def update(cls, obj_id: int, data: Dict[str, Any]) -> Any:
        """
        更新（带审批门禁）。

        命中规则：自动建审批实例并抛 NeedApprovalError（40001）。
        未命中：直接执行 ``_do_update(obj_id, data)``。
        未定义 ``_do_update``：抛出 NotImplementedError。
        """
        await cls._gate("update", payload=data, business_id=obj_id)
        method = cls.__dict__.get("_do_update")
        if method is None:
            raise NotImplementedError(
                f"{cls.__name__} 未实现 _do_update，无法执行 update()"
            )
        return await method(cls, obj_id, data)

    @classmethod
    async def delete(cls, obj_id: int) -> bool:
        """
        删除（带审批门禁）。

        命中规则：自动建审批实例并抛 NeedApprovalError（40001）。
        未命中：直接执行 ``_do_delete(obj_id)``。
        未定义 ``_do_delete``：抛出 NotImplementedError。
        """
        await cls._gate("delete", business_id=obj_id)
        method = cls.__dict__.get("_do_delete")
        if method is None:
            raise NotImplementedError(
                f"{cls.__name__} 未实现 _do_delete，无法执行 delete()"
            )
        return await method(cls, obj_id)

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
