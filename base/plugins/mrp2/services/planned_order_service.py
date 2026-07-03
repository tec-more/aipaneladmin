from typing import Optional, List, Tuple
from datetime import datetime

try:
    from base.plugins.mrp2.models.mrp_models import PlannedOrder
    from base.plugins.mrp2.schemas.planned_order_schema import PlannedOrderConfirmRequest
    try:
        from base.plugins.mes.models.production import ManufacturingOrder
        MES_AVAILABLE = True
    except ImportError:
        ManufacturingOrder = None
        MES_AVAILABLE = False
except ImportError:
    PlannedOrder = None
    MES_AVAILABLE = False


class PlannedOrderService:
    @staticmethod
    async def get_by_id(order_id: int) -> Optional[PlannedOrder]:
        return await PlannedOrder.filter(id=order_id).first()

    @staticmethod
    async def get_by_code(order_code: str) -> Optional[PlannedOrder]:
        return await PlannedOrder.filter(order_code=order_code).first()

    @staticmethod
    async def get_list(
        page: int = 1, page_size: int = 10,
        mrp_id: Optional[int] = None,
        order_type: Optional[str] = None,
        material_code: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[PlannedOrder], int]:
        query = PlannedOrder.all()
        if mrp_id:
            query = query.filter(mrp_id=mrp_id)
        if order_type:
            query = query.filter(order_type=order_type)
        if material_code:
            query = query.filter(material_code__icontains=material_code)
        if status:
            query = query.filter(status=status)
        total = await query.count()
        offset = (page - 1) * page_size
        items = await query.offset(offset).limit(page_size).order_by('-created_at')
        return items, total

    @staticmethod
    async def confirm_order(order_id: int, data: PlannedOrderConfirmRequest = None) -> Optional[PlannedOrder]:
        order = await PlannedOrder.filter(id=order_id).first()
        if not order:
            return None
        if order.status != "planned":
            raise ValueError("只能确认计划状态的订单")
        if order.order_type == "manufacture" and MES_AVAILABLE and ManufacturingOrder is not None:
            mo_code = f"MO{datetime.now().strftime('%Y%m%d%H%M%S')}"
            mo = await ManufacturingOrder.create(
                mo_code=mo_code,
                product_code=order.material_code,
                product_name=order.material_name,
                quantity=int(order.plan_quantity),
                status="planned",
                priority="normal",
                source_mps_id=order.source_mps_id,
                source_planned_order_code=order.order_code,
                remark=data.remark if data else None
            )
            order.converted_mo_code = mo_code

        order.status = "confirmed"
        await order.save()
        return order

    @staticmethod
    async def cancel_order(order_id: int) -> Optional[PlannedOrder]:
        order = await PlannedOrder.filter(id=order_id).first()
        if not order:
            return None
        if order.status != "planned":
            raise ValueError("只能取消计划状态的订单")
        order.status = "canceled"
        await order.save()
        return order