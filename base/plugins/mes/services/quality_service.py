from typing import Optional, List, Tuple, Dict, Any
from decimal import Decimal
from tortoise.expressions import Q

try:
    from base.plugins.mes.models.quality import QualityInspection
    from base.plugins.mes.schemas.mes_schema import (
        QualityInspectionCreate, QualityInspectionUpdate,
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

    class QualityInspection(BaseModelMock):
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

    class QualityInspectionCreate:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class QualityInspectionUpdate(QualityInspectionCreate):
        def model_dump(self, exclude_none=False):
            return {k: v for k, v in self.__dict__.items() if v is not None}


class QualityInspectionService:
    @staticmethod
    async def get_by_id(inspection_id: int) -> Optional[QualityInspection]:
        return await QualityInspection.filter(id=inspection_id).first()

    @staticmethod
    async def get_by_code(inspection_code: str) -> Optional[QualityInspection]:
        return await QualityInspection.filter(inspection_code=inspection_code).first()

    @staticmethod
    async def create_inspection(data: QualityInspectionCreate) -> QualityInspection:
        if await QualityInspectionService.check_code_exists(data.inspection_code):
            raise ValueError("检验单号已存在")
        return await QualityInspection.create(**data.__dict__)

    @staticmethod
    async def update_inspection(inspection_id: int, data: QualityInspectionUpdate) -> Optional[QualityInspection]:
        inspection = await QualityInspection.filter(id=inspection_id).first()
        if not inspection:
            return None
        update_data = data.model_dump(exclude_none=True)
        await inspection.update_from_dict(update_data).save()
        return inspection

    @staticmethod
    async def delete_inspection(inspection_id: int) -> bool:
        deleted_count = await QualityInspection.filter(id=inspection_id).delete()
        return deleted_count > 0

    @staticmethod
    async def submit_inspection(
        inspection_id: int,
        qualified_quantity: int,
        unqualified_quantity: int,
        inspector: Optional[str] = None,
        inspection_items: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[QualityInspection]:
        inspection = await QualityInspection.filter(id=inspection_id).first()
        if not inspection:
            return None
        if inspection.inspection_result != "pending":
            raise ValueError(f"检验单当前状态为{inspection.inspection_result}，无法提交")

        inspection.qualified_quantity = qualified_quantity
        inspection.unqualified_quantity = unqualified_quantity
        inspection.inspector = inspector
        inspection.inspection_items = inspection_items

        if unqualified_quantity == 0:
            inspection.inspection_result = "qualified"
        else:
            inspection.inspection_result = "unqualified"

        await inspection.save()
        return inspection

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        inspection_code: Optional[str] = None,
        inspection_type: Optional[str] = None,
        material_code: Optional[str] = None,
        inspection_result: Optional[str] = None
    ) -> Tuple[List[QualityInspection], int]:
        query = QualityInspection.all()
        if inspection_code:
            query = query.filter(inspection_code__icontains=inspection_code)
        if inspection_type:
            query = query.filter(inspection_type=inspection_type)
        if material_code:
            query = query.filter(material_code__icontains=material_code)
        if inspection_result:
            query = query.filter(inspection_result=inspection_result)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        query = QualityInspection.filter(inspection_code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()