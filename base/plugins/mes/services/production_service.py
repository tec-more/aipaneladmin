from typing import Optional, List, Tuple, Dict, Any
from tortoise.expressions import Q

try:
    from base.plugins.mes.models.production import ManufacturingOrder, WorkOrder
    from base.plugins.mes.schemas.mes_schema import (
        ManufacturingOrderCreate, ManufacturingOrderUpdate,
        WorkOrderCreate, WorkOrderUpdate,
    )
except ImportError:
    from typing import Any
    from datetime import datetime
    from decimal import Decimal

    class BaseModelMock:
        id = 1
        created_at = datetime.now()
        updated_at = datetime.now()

        async def save(self):
            pass

        async def update_from_dict(self, data):
            for key, value in data.items():
                setattr(self, key, value)
            return self

    class ManufacturingOrder(BaseModelMock):
        def __init__(self, **kwargs):
            super().__init__()
            for key, value in kwargs.items():
                setattr(self, key, value)

        @classmethod
        async def create(cls, **kwargs):
            return cls(**kwargs)

        @classmethod
        async def filter(cls, **kwargs):
            class MockQuerySet:
                async def first(self): return None
                async def exists(self): return False
                async def delete(self): return 0
                async def count(self): return 0
                async def offset(self, n): return self
                async def limit(self, n): return self
                async def order_by(self, order): return self
                def filter(self, **kwargs): return self
                def exclude(self, **kwargs): return self
                def all(self): return []
            return MockQuerySet()

        async def to_dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    class WorkOrder(ManufacturingOrder): pass

    class ManufacturingOrderCreate:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class ManufacturingOrderUpdate(ManufacturingOrderCreate):
        def model_dump(self, exclude_none=False):
            return {k: v for k, v in self.__dict__.items() if v is not None}

    class WorkOrderCreate(ManufacturingOrderCreate): pass
    class WorkOrderUpdate(ManufacturingOrderUpdate): pass


class ManufacturingOrderService:
    @staticmethod
    async def get_by_id(mo_id: int) -> Optional[ManufacturingOrder]:
        return await ManufacturingOrder.filter(id=mo_id).first()

    @staticmethod
    async def get_by_code(mo_code: str) -> Optional[ManufacturingOrder]:
        return await ManufacturingOrder.filter(mo_code=mo_code).first()

    @staticmethod
    async def create_mo(data: ManufacturingOrderCreate) -> ManufacturingOrder:
        if await ManufacturingOrderService.check_code_exists(data.mo_code):
            raise ValueError("制造单编码已存在")
        return await ManufacturingOrder.create(**data.__dict__)

    @staticmethod
    async def update_mo(mo_id: int, data: ManufacturingOrderUpdate) -> Optional[ManufacturingOrder]:
        mo = await ManufacturingOrder.filter(id=mo_id).first()
        if not mo:
            return None
        if data.mo_code and data.mo_code != mo.mo_code:
            if await ManufacturingOrderService.check_code_exists(data.mo_code, exclude_id=mo_id):
                raise ValueError("制造单编码已被使用")
        update_data = data.model_dump(exclude_none=True)
        await mo.update_from_dict(update_data).save()
        return mo

    @staticmethod
    async def delete_mo(mo_id: int) -> bool:
        deleted_count = await ManufacturingOrder.filter(id=mo_id).delete()
        return deleted_count > 0

    @staticmethod
    async def release_mo(mo_id: int) -> Optional[ManufacturingOrder]:
        mo = await ManufacturingOrder.filter(id=mo_id).first()
        if not mo:
            return None
        if mo.status != "planned":
            raise ValueError(f"制造单当前状态为{mo.status}，无法下达")
        mo.status = "released"
        await mo.save()
        return mo

    @staticmethod
    async def complete_mo(mo_id: int) -> Optional[ManufacturingOrder]:
        mo = await ManufacturingOrder.filter(id=mo_id).first()
        if not mo:
            return None
        if mo.status not in ["released", "processing"]:
            raise ValueError(f"制造单当前状态为{mo.status}，无法完成")
        mo.status = "completed"
        await mo.save()
        return mo

    @staticmethod
    async def cancel_mo(mo_id: int) -> Optional[ManufacturingOrder]:
        mo = await ManufacturingOrder.filter(id=mo_id).first()
        if not mo:
            return None
        if mo.status == "completed":
            raise ValueError("已完成的制造单无法取消")
        mo.status = "canceled"
        await mo.save()
        return mo

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        mo_code: Optional[str] = None,
        product_code: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Tuple[List[ManufacturingOrder], int]:
        query = ManufacturingOrder.all()
        if mo_code:
            query = query.filter(mo_code__icontains=mo_code)
        if product_code:
            query = query.filter(product_code__icontains=product_code)
        if status:
            query = query.filter(status=status)
        if priority:
            query = query.filter(priority=priority)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        query = ManufacturingOrder.filter(mo_code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()


class WorkOrderService:
    @staticmethod
    async def get_by_id(wo_id: int) -> Optional[WorkOrder]:
        return await WorkOrder.filter(id=wo_id).first()

    @staticmethod
    async def get_by_code(wo_code: str) -> Optional[WorkOrder]:
        return await WorkOrder.filter(wo_code=wo_code).first()

    @staticmethod
    async def create_wo(data: WorkOrderCreate) -> WorkOrder:
        if await WorkOrderService.check_code_exists(data.wo_code):
            raise ValueError("工单编码已存在")
        return await WorkOrder.create(**data.__dict__)

    @staticmethod
    async def update_wo(wo_id: int, data: WorkOrderUpdate) -> Optional[WorkOrder]:
        wo = await WorkOrder.filter(id=wo_id).first()
        if not wo:
            return None
        if data.wo_code and data.wo_code != wo.wo_code:
            if await WorkOrderService.check_code_exists(data.wo_code, exclude_id=wo_id):
                raise ValueError("工单编码已被使用")
        update_data = data.model_dump(exclude_none=True)
        await wo.update_from_dict(update_data).save()
        return wo

    @staticmethod
    async def delete_wo(wo_id: int) -> bool:
        deleted_count = await WorkOrder.filter(id=wo_id).delete()
        return deleted_count > 0

    @staticmethod
    async def release_wo(wo_id: int) -> Optional[WorkOrder]:
        wo = await WorkOrder.filter(id=wo_id).first()
        if not wo:
            return None
        if wo.status != "pending":
            raise ValueError(f"工单当前状态为{wo.status}，无法下达")
        wo.status = "released"
        await wo.save()
        return wo

    @staticmethod
    async def start_wo(wo_id: int, operator: str = None) -> Optional[WorkOrder]:
        wo = await WorkOrder.filter(id=wo_id).first()
        if not wo:
            return None
        if wo.status != "released":
            raise ValueError(f"工单当前状态为{wo.status}，无法开始")
        wo.status = "processing"
        wo.operator = operator
        await wo.save()
        return wo

    @staticmethod
    async def complete_wo(wo_id: int, actual_quantity: int, scrap_quantity: int = 0) -> Optional[WorkOrder]:
        wo = await WorkOrder.filter(id=wo_id).first()
        if not wo:
            return None
        if wo.status != "processing":
            raise ValueError(f"工单当前状态为{wo.status}，无法完成")
        wo.status = "completed"
        wo.actual_quantity = actual_quantity
        wo.scrap_quantity = scrap_quantity
        await wo.save()
        return wo

    @staticmethod
    async def close_wo(wo_id: int) -> Optional[WorkOrder]:
        wo = await WorkOrder.filter(id=wo_id).first()
        if not wo:
            return None
        if wo.status != "completed":
            raise ValueError(f"工单当前状态为{wo.status}，无法关闭")
        wo.status = "closed"
        await wo.save()
        return wo

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        wo_code: Optional[str] = None,
        mo_code: Optional[str] = None,
        product_code: Optional[str] = None,
        status: Optional[str] = None,
        work_center_code: Optional[str] = None
    ) -> Tuple[List[WorkOrder], int]:
        query = WorkOrder.all()
        if wo_code:
            query = query.filter(wo_code__icontains=wo_code)
        if mo_code:
            query = query.filter(mo_code__icontains=mo_code)
        if product_code:
            query = query.filter(product_code__icontains=product_code)
        if status:
            query = query.filter(status=status)
        if work_center_code:
            query = query.filter(work_center_code=work_center_code)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        query = WorkOrder.filter(wo_code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()