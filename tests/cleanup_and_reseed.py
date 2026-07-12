import asyncio
from base.common.setting import TORTOISE_ORM
from tortoise import Tortoise

async def cleanup_mrp_data():
    print("清理MRP相关数据...")
    
    from base.plugins.mrp2.models.mrp_models import (
        MRPCalculation, MRPResultDetail, PlannedOrder,
        CapacityRequirementPlan, CRPDetail, MRPExceptionAlert
    )
    
    await MRPExceptionAlert.all().delete()
    print("  删除MRP异常告警")
    
    await CRPDetail.all().delete()
    print("  删除CRP结果明细")
    
    await CapacityRequirementPlan.all().delete()
    print("  删除CRP计算")
    
    await PlannedOrder.all().delete()
    print("  删除计划订单")
    
    await MRPResultDetail.all().delete()
    print("  删除MRP结果明细")
    
    await MRPCalculation.all().delete()
    print("  删除MRP计算")
    
    print("MRP数据清理完成")

async def check_and_create_locations():
    print("\n检查库位数据...")
    
    from base.plugins.inventory.models.inventory_models import StockLocation
    
    locations = await StockLocation.all().count()
    print(f"现有库位数量: {locations}")
    
    if locations == 0:
        print("创建默认库位...")
        await StockLocation.create(
            location_code="WH-SUPPLIER",
            location_name="供应商",
            location_type="supplier",
            is_active=True
        )
        await StockLocation.create(
            location_code="WH-RAW",
            location_name="原材料仓库",
            location_type="internal",
            is_active=True
        )
        await StockLocation.create(
            location_code="WH-WIP",
            location_name="在制品仓库",
            location_type="internal",
            is_active=True
        )
        await StockLocation.create(
            location_code="WH-FINISHED",
            location_name="成品仓库",
            location_type="internal",
            is_active=True
        )
        await StockLocation.create(
            location_code="WH-CUSTOMER",
            location_name="客户",
            location_type="customer",
            is_active=True
        )
        print("默认库位创建完成")

async def cleanup_inventory_data():
    print("\n清理库存相关数据...")
    
    from base.plugins.inventory.models.inventory_models import (
        StockPicking, StockMove, StockMoveLine, StockQuant
    )
    
    await StockMoveLine.all().delete()
    print("  删除移动明细行")
    
    await StockMove.all().delete()
    print("  删除移动明细")
    
    await StockPicking.all().delete()
    print("  删除调拨单")
    
    print("库存数据清理完成")

async def check_and_create_picking_types():
    print("\n检查调拨类型数据...")
    
    from base.plugins.inventory.models.inventory_models import StockPickingType
    
    picking_types = await StockPickingType.all().count()
    print(f"现有调拨类型数量: {picking_types}")
    
    if picking_types == 0:
        print("创建默认调拨类型...")
        await StockPickingType.create(
            picking_type_code="PT-IN",
            picking_type_name="采购入库",
            code="incoming",
            sequence_code="IN/{year}/{month}",
            is_active=True
        )
        await StockPickingType.create(
            picking_type_code="PT-OUT",
            picking_type_name="销售出库",
            code="outgoing",
            sequence_code="OUT/{year}/{month}",
            is_active=True
        )
        await StockPickingType.create(
            picking_type_code="PT-INT",
            picking_type_name="内部调拨",
            code="internal",
            sequence_code="INT/{year}/{month}",
            is_active=True
        )
        print("默认调拨类型创建完成")

async def main():
    await Tortoise.init(config=TORTOISE_ORM)
    
    await cleanup_mrp_data()
    await cleanup_inventory_data()
    await check_and_create_locations()
    await check_and_create_picking_types()
    
    await Tortoise.close_connections()
    print("\n清理和初始化完成！")

if __name__ == "__main__":
    asyncio.run(main())
