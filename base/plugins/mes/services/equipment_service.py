from typing import Optional, List, Tuple, Dict, Any
from decimal import Decimal
from tortoise.expressions import Q

try:
    from base.plugins.mes.models.equipment import Equipment
    from base.plugins.mes.schemas.mes_schema import (
        EquipmentCreate, EquipmentUpdate,
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

    class Equipment(BaseModelMock):
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

    class EquipmentCreate:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class EquipmentUpdate(EquipmentCreate):
        def model_dump(self, exclude_none=False):
            return {k: v for k, v in self.__dict__.items() if v is not None}


class EquipmentService:
    @staticmethod
    async def get_by_id(equipment_id: int) -> Optional[Equipment]:
        return await Equipment.filter(id=equipment_id).first()

    @staticmethod
    async def get_by_code(equipment_code: str) -> Optional[Equipment]:
        return await Equipment.filter(equipment_code=equipment_code).first()

    @staticmethod
    async def create_equipment(data: EquipmentCreate) -> Equipment:
        if await EquipmentService.check_code_exists(data.equipment_code):
            raise ValueError("设备编码已存在")
        return await Equipment.create(**data.__dict__)

    @staticmethod
    async def update_equipment(equipment_id: int, data: EquipmentUpdate) -> Optional[Equipment]:
        equipment = await Equipment.filter(id=equipment_id).first()
        if not equipment:
            return None
        if data.equipment_code and data.equipment_code != equipment.equipment_code:
            if await EquipmentService.check_code_exists(data.equipment_code, exclude_id=equipment_id):
                raise ValueError("设备编码已被使用")
        update_data = data.model_dump(exclude_none=True)
        await equipment.update_from_dict(update_data).save()
        return equipment

    @staticmethod
    async def delete_equipment(equipment_id: int) -> bool:
        deleted_count = await Equipment.filter(id=equipment_id).delete()
        return deleted_count > 0

    @staticmethod
    async def change_status(equipment_id: int, status: str) -> Optional[Equipment]:
        equipment = await Equipment.filter(id=equipment_id).first()
        if not equipment:
            return None
        equipment.status = status
        await equipment.save()
        return equipment

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        equipment_code: Optional[str] = None,
        equipment_name: Optional[str] = None,
        equipment_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[Equipment], int]:
        query = Equipment.all()
        if equipment_code:
            query = query.filter(equipment_code__icontains=equipment_code)
        if equipment_name:
            query = query.filter(equipment_name__icontains=equipment_name)
        if equipment_type:
            query = query.filter(equipment_type=equipment_type)
        if status:
            query = query.filter(status=status)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        query = Equipment.filter(equipment_code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()