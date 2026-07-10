import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.common.setting import TORTOISE_ORM, settings


BLUETOOTH_MODELS = [
    "base.plugins.mes.models.base_data",
    "base.plugins.mrp2.models.mrp_models",
    "base.plugins.quality.models.quality",
    "base.plugins.inventory.models.inventory_models",
    "base.plugins.purchase.models.supplier",
    "base.plugins.purchase.models.purchase",
    "base.plugins.product.models.product",
]


def get_custom_orm_config():
    config = TORTOISE_ORM.copy()
    existing_models = config["apps"]["models"]["models"]
    for model_path in BLUETOOTH_MODELS:
        if model_path not in existing_models:
            existing_models.append(model_path)
    return config


PRODUCTS_DATA = [
    {
        "name": "听音T100蓝牙耳机",
        "description": "高品质蓝牙5.3耳机，支持主动降噪(ANC)，IPX5防水等级，超长续航30小时",
        "price": Decimal("299.00"),
        "original_price": Decimal("399.00"),
        "stock": 0,
        "category": "蓝牙耳机",
        "tags": ["蓝牙5.3", "ANC降噪", "IPX5", "长续航"],
        "images": [],
        "is_active": True,
        "is_hot": True,
        "is_new": True,
        "is_stock_item": True,
        "uom_code": "副",
        "uom_name": "副",
        "product_type": "item",
        "price_mode": "fixed",
    },
    {
        "name": "听音T100充电盒",
        "description": "T100蓝牙耳机专用充电盒，Type-C接口，420mAh容量",
        "price": Decimal("99.00"),
        "original_price": Decimal("129.00"),
        "stock": 0,
        "category": "配件",
        "tags": ["充电盒", "Type-C"],
        "images": [],
        "is_active": True,
        "is_hot": False,
        "is_new": False,
        "is_stock_item": True,
        "uom_code": "个",
        "uom_name": "个",
        "product_type": "item",
        "price_mode": "fixed",
    },
]

PRODUCT_MATERIAL_MAP = {
    "听音T100蓝牙耳机": "FG-T100",
    "听音T100充电盒": "FG-T100-CASE",
}

MATERIALS_DATA = [
    {"material_code": "FG-T100", "material_name": "听音T100蓝牙耳机", "material_type": "finished", "unit": "副", "specification": "BT5.3/ANC/IPX5", "product_id": None},
    {"material_code": "FG-T100-CASE", "material_name": "T100充电盒", "material_type": "finished", "unit": "个", "specification": "Type-C/420mAh", "product_id": None},
    {"material_code": "SEMI-PCB", "material_name": "T100主板组件", "material_type": "semi_finished", "unit": "件", "specification": "BT5.3芯片", "product_id": None},
    {"material_code": "SEMI-SPEAKER", "material_name": "T100扬声器组件", "material_type": "semi_finished", "unit": "个", "specification": "10mm动圈", "product_id": None},
    {"material_code": "RM-PCB-BOARD", "material_name": "PCB电路板", "material_type": "raw", "unit": "片", "specification": "FR-4/2层", "product_id": None},
    {"material_code": "RM-BT-CHIP", "material_name": "蓝牙5.3芯片", "material_type": "raw", "unit": "颗", "specification": "QCC3084", "product_id": None},
    {"material_code": "RM-MIC", "material_name": "麦克风", "material_type": "raw", "unit": "个", "specification": "硅麦", "product_id": None},
    {"material_code": "RM-BATTERY", "material_name": "锂电池", "material_type": "raw", "unit": "个", "specification": "40mAh", "product_id": None},
    {"material_code": "RM-SPEAKER", "material_name": "扬声器单元", "material_type": "raw", "unit": "个", "specification": "10mm", "product_id": None},
    {"material_code": "RM-HOUSING", "material_name": "耳机壳体", "material_type": "raw", "unit": "个", "specification": "ABS+PC", "product_id": None},
    {"material_code": "RM-EAR-TIP", "material_name": "耳套", "material_type": "raw", "unit": "套", "specification": "S/M/L", "product_id": None},
    {"material_code": "RM-CHARGE-BOARD", "material_name": "充电盒主板", "material_type": "raw", "unit": "片", "specification": "-", "product_id": None},
    {"material_code": "RM-CHARGE-BATTERY", "material_name": "充电盒电池", "material_type": "raw", "unit": "个", "specification": "420mAh", "product_id": None},
    {"material_code": "RM-BOX", "material_name": "包装盒", "material_type": "raw", "unit": "个", "specification": "彩盒", "product_id": None},
    {"material_code": "RM-MANUAL", "material_name": "说明书", "material_type": "raw", "unit": "本", "specification": "-", "product_id": None},
]


BOM_DATA = [
    {"product_code": "FG-T100", "product_name": "听音T100蓝牙耳机", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "SEMI-PCB", "item_name": "T100主板组件", "quantity": Decimal("2"), "unit": "件", "scrap_rate": Decimal("0.02")},
    {"product_code": "FG-T100", "product_name": "听音T100蓝牙耳机", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "SEMI-SPEAKER", "item_name": "T100扬声器组件", "quantity": Decimal("2"), "unit": "个", "scrap_rate": Decimal("0.01")},
    {"product_code": "FG-T100", "product_name": "听音T100蓝牙耳机", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "RM-HOUSING", "item_name": "耳机壳体", "quantity": Decimal("2"), "unit": "个", "scrap_rate": Decimal("0")},
    {"product_code": "FG-T100", "product_name": "听音T100蓝牙耳机", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "RM-EAR-TIP", "item_name": "耳套", "quantity": Decimal("3"), "unit": "套", "scrap_rate": Decimal("0")},
    {"product_code": "FG-T100", "product_name": "听音T100蓝牙耳机", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "FG-T100-CASE", "item_name": "T100充电盒", "quantity": Decimal("1"), "unit": "个", "scrap_rate": Decimal("0")},
    {"product_code": "SEMI-PCB", "product_name": "T100主板组件", "version": "V1.0", "level": 2, "parent_item_code": "FG-T100",
     "item_code": "RM-PCB-BOARD", "item_name": "PCB电路板", "quantity": Decimal("1"), "unit": "片", "scrap_rate": Decimal("0.01")},
    {"product_code": "SEMI-PCB", "product_name": "T100主板组件", "version": "V1.0", "level": 2, "parent_item_code": "FG-T100",
     "item_code": "RM-BT-CHIP", "item_name": "蓝牙5.3芯片", "quantity": Decimal("1"), "unit": "颗", "scrap_rate": Decimal("0")},
    {"product_code": "SEMI-PCB", "product_name": "T100主板组件", "version": "V1.0", "level": 2, "parent_item_code": "FG-T100",
     "item_code": "RM-MIC", "item_name": "麦克风", "quantity": Decimal("2"), "unit": "个", "scrap_rate": Decimal("0.01")},
    {"product_code": "SEMI-PCB", "product_name": "T100主板组件", "version": "V1.0", "level": 2, "parent_item_code": "FG-T100",
     "item_code": "RM-BATTERY", "item_name": "锂电池", "quantity": Decimal("1"), "unit": "个", "scrap_rate": Decimal("0")},
    {"product_code": "SEMI-SPEAKER", "product_name": "T100扬声器组件", "version": "V1.0", "level": 2, "parent_item_code": "FG-T100",
     "item_code": "RM-SPEAKER", "item_name": "扬声器单元", "quantity": Decimal("1"), "unit": "个", "scrap_rate": Decimal("0.01")},
    {"product_code": "FG-T100-CASE", "product_name": "T100充电盒", "version": "V1.0", "level": 2, "parent_item_code": "FG-T100",
     "item_code": "RM-CHARGE-BOARD", "item_name": "充电盒主板", "quantity": Decimal("1"), "unit": "片", "scrap_rate": Decimal("0")},
    {"product_code": "FG-T100-CASE", "product_name": "T100充电盒", "version": "V1.0", "level": 2, "parent_item_code": "FG-T100",
     "item_code": "RM-CHARGE-BATTERY", "item_name": "充电盒电池", "quantity": Decimal("1"), "unit": "个", "scrap_rate": Decimal("0")},
    {"product_code": "FG-T100-CASE", "product_name": "T100充电盒", "version": "V1.0", "level": 2, "parent_item_code": "FG-T100",
     "item_code": "RM-HOUSING", "item_name": "充电盒壳体", "quantity": Decimal("1"), "unit": "个", "scrap_rate": Decimal("0")},
]


WORK_CENTERS_DATA = [
    {"work_center_code": "WC-SMT", "work_center_name": "SMT贴片车间", "department": "生产部", "location": "A栋1楼", "capacity": 1000},
    {"work_center_code": "WC-ASSY", "work_center_name": "组装车间", "department": "生产部", "location": "A栋2楼", "capacity": 800},
    {"work_center_code": "WC-TEST", "work_center_name": "测试车间", "department": "品质部", "location": "B栋1楼", "capacity": 600},
    {"work_center_code": "WC-PKG", "work_center_name": "包装车间", "department": "生产部", "location": "B栋2楼", "capacity": 1200},
]


PROCESSES_DATA = [
    {"process_code": "PROC-SMT", "process_name": "SMT贴片", "process_type": "machining", "sequence": 10,
     "work_center_code": "WC-SMT", "work_center_name": "SMT贴片车间", "standard_time": Decimal("25")},
    {"process_code": "PROC-SOLDER", "process_name": "焊接加固", "process_type": "machining", "sequence": 20,
     "work_center_code": "WC-SMT", "work_center_name": "SMT贴片车间", "standard_time": Decimal("15")},
    {"process_code": "PROC-ASSY", "process_name": "壳体组装", "process_type": "assembly", "sequence": 30,
     "work_center_code": "WC-ASSY", "work_center_name": "组装车间", "standard_time": Decimal("40")},
    {"process_code": "PROC-TEST", "process_name": "功能测试", "process_type": "inspection", "sequence": 40,
     "work_center_code": "WC-TEST", "work_center_name": "测试车间", "standard_time": Decimal("30")},
    {"process_code": "PROC-AGING", "process_name": "老化测试", "process_type": "inspection", "sequence": 50,
     "work_center_code": "WC-TEST", "work_center_name": "测试车间", "standard_time": Decimal("120")},
    {"process_code": "PROC-PKG", "process_name": "成品包装", "process_type": "assembly", "sequence": 60,
     "work_center_code": "WC-PKG", "work_center_name": "包装车间", "standard_time": Decimal("10")},
]


ROUTE_PROCESSES_DATA = [
    {"route_code": "ROUTE-T100", "process_code": "PROC-SMT", "process_name": "SMT贴片", "sequence": 10,
     "work_center_code": "WC-SMT", "work_center_name": "SMT贴片车间"},
    {"route_code": "ROUTE-T100", "process_code": "PROC-SOLDER", "process_name": "焊接加固", "sequence": 20,
     "work_center_code": "WC-SMT", "work_center_name": "SMT贴片车间"},
    {"route_code": "ROUTE-T100", "process_code": "PROC-ASSY", "process_name": "壳体组装", "sequence": 30,
     "work_center_code": "WC-ASSY", "work_center_name": "组装车间"},
    {"route_code": "ROUTE-T100", "process_code": "PROC-TEST", "process_name": "功能测试", "sequence": 40,
     "work_center_code": "WC-TEST", "work_center_name": "测试车间"},
    {"route_code": "ROUTE-T100", "process_code": "PROC-AGING", "process_name": "老化测试", "sequence": 50,
     "work_center_code": "WC-TEST", "work_center_name": "测试车间"},
    {"route_code": "ROUTE-T100", "process_code": "PROC-PKG", "process_name": "成品包装", "sequence": 60,
     "work_center_code": "WC-PKG", "work_center_name": "包装车间"},
]


SUPPLIERS_DATA = [
    {"supplier_code": "SUP-BT-001", "supplier_name": "深圳蓝牙科技有限公司", "supplier_type": "manufacturer",
     "contact_person": "王经理", "phone": "0755-11112222", "address": "深圳市南山区科技园"},
    {"supplier_code": "SUP-PCB-001", "supplier_name": "东莞电路板厂", "supplier_type": "manufacturer",
     "contact_person": "李总", "phone": "0769-33334444", "address": "东莞市长安镇"},
    {"supplier_code": "SUP-ELEC-001", "supplier_name": "惠州电子元件公司", "supplier_type": "manufacturer",
     "contact_person": "张经理", "phone": "0752-55556666", "address": "惠州市仲恺高新区"},
    {"supplier_code": "SUP-SPK-001", "supplier_name": "广州扬声器厂", "supplier_type": "manufacturer",
     "contact_person": "陈总", "phone": "020-77778888", "address": "广州市花都区"},
    {"supplier_code": "SUP-PLASTIC-001", "supplier_name": "佛山塑胶制品公司", "supplier_type": "manufacturer",
     "contact_person": "刘经理", "phone": "0757-99990000", "address": "佛山市顺德区"},
    {"supplier_code": "SUP-PACK-001", "supplier_name": "中山包装材料厂", "supplier_type": "manufacturer",
     "contact_person": "赵总", "phone": "0760-22223333", "address": "中山市小榄镇"},
]


WAREHOUSES_DATA = [
    {"warehouse_code": "WH-RAW", "warehouse_name": "原材料仓", "warehouse_type": "internal", "address": "A栋1楼"},
    {"warehouse_code": "WH-SEMI", "warehouse_name": "半成品仓", "warehouse_type": "internal", "address": "A栋2楼"},
    {"warehouse_code": "WH-FG", "warehouse_name": "成品仓", "warehouse_type": "internal", "address": "B栋1楼"},
    {"warehouse_code": "WH-PACK", "warehouse_name": "包装材料仓", "warehouse_type": "internal", "address": "B栋2楼"},
]


INSPECTION_STANDARDS_DATA = [
    {
        "standard_code": "STD-T100-FQC",
        "standard_name": "听音T100成品检验标准",
        "material_code": "FG-T100",
        "inspection_type": "FQC",
        "items": [
            {"name": "蓝牙连接测试", "method": "连接手机测试", "standard": "连接成功，无断连"},
            {"name": "音质测试", "method": "播放测试音频", "standard": "音质清晰，无杂音"},
            {"name": "ANC降噪测试", "method": "噪音环境测试", "standard": "降噪效果明显"},
            {"name": "充电测试", "method": "充电盒充电测试", "standard": "充电正常"},
            {"name": "外观检查", "method": "目视检查", "standard": "外观无划痕，壳体无变形"},
        ],
        "sampling_rule": "AQL 2.5，抽检比例10%"
    },
    {
        "standard_code": "STD-T100-IPQC",
        "standard_name": "听音T100过程检验标准",
        "material_code": "SEMI-PCB",
        "inspection_type": "IPQC",
        "items": [
            {"name": "SMT贴片检查", "method": "AOI检测", "standard": "无虚焊、连锡"},
            {"name": "元件极性检查", "method": "目视检查", "standard": "极性正确"},
            {"name": "焊点质量", "method": "放大镜检查", "standard": "焊点饱满"},
        ],
        "sampling_rule": "每批次抽检20%"
    },
]


async def seed_products():
    from base.plugins.product.models.product import Product
    print("Seeding products...")
    count = 0
    for data in PRODUCTS_DATA:
        existing = await Product.get_or_none(name=data["name"])
        if not existing:
            await Product.create(**data)
            count += 1
    print(f"Created {count} products")


async def seed_materials():
    from base.plugins.mes.models.base_data import Material
    from base.plugins.product.models.product import Product
    print("Seeding materials...")
    
    product_material_code_map = {v: k for k, v in PRODUCT_MATERIAL_MAP.items()}
    
    count = 0
    for data in MATERIALS_DATA.copy():
        data_copy = data.copy()
        material_code = data_copy["material_code"]
        
        if material_code in product_material_code_map:
            product_name = product_material_code_map[material_code]
            product = await Product.get_or_none(name=product_name)
            if product:
                data_copy["product_id"] = product.id
        
        existing = await Material.get_or_none(material_code=material_code)
        if not existing:
            await Material.create(**data_copy)
            count += 1
        else:
            if data_copy.get("product_id"):
                existing.product_id = data_copy["product_id"]
                await existing.save()
    print(f"Created {count} materials")


async def seed_bom():
    from base.plugins.mes.models.base_data import BomVersion, Bom
    print("Seeding BOM...")
    await BomVersion.get_or_create(product_code="FG-T100", version="V1.0", defaults={
        "product_name": "听音T100蓝牙耳机", "status": "active"
    })
    await BomVersion.get_or_create(product_code="SEMI-PCB", version="V1.0", defaults={
        "product_name": "T100主板组件", "status": "active"
    })
    await BomVersion.get_or_create(product_code="SEMI-SPEAKER", version="V1.0", defaults={
        "product_name": "T100扬声器组件", "status": "active"
    })
    await BomVersion.get_or_create(product_code="FG-T100-CASE", version="V1.0", defaults={
        "product_name": "T100充电盒", "status": "active"
    })
    
    count = 0
    for data in BOM_DATA:
        existing = await Bom.get_or_none(product_code=data["product_code"], item_code=data["item_code"], version=data["version"])
        if not existing:
            await Bom.create(**data)
            count += 1
    print(f"Created {count} BOM items")


async def seed_work_centers():
    from base.plugins.mes.models.base_data import WorkCenter
    print("Seeding work centers...")
    count = 0
    for data in WORK_CENTERS_DATA:
        existing = await WorkCenter.get_or_none(work_center_code=data["work_center_code"])
        if not existing:
            await WorkCenter.create(**data)
            count += 1
    print(f"Created {count} work centers")


async def seed_processes():
    from base.plugins.mes.models.base_data import Process
    print("Seeding processes...")
    count = 0
    for data in PROCESSES_DATA:
        existing = await Process.get_or_none(process_code=data["process_code"])
        if not existing:
            await Process.create(**data)
            count += 1
    print(f"Created {count} processes")


async def seed_route():
    from base.plugins.mes.models.base_data import Route, RouteProcess
    print("Seeding route...")
    await Route.get_or_create(route_code="ROUTE-T100", defaults={
        "route_name": "听音T100工艺路线",
        "product_code": "FG-T100",
        "product_name": "听音T100蓝牙耳机",
        "bom_code": "FG-T100",
        "bom_version": "V1.0",
        "version": "V1.0"
    })
    
    count = 0
    for data in ROUTE_PROCESSES_DATA:
        existing = await RouteProcess.get_or_none(route_code=data["route_code"], process_code=data["process_code"])
        if not existing:
            await RouteProcess.create(**data)
            count += 1
    print(f"Created {count} route processes")


async def seed_suppliers():
    from base.plugins.purchase.models.supplier import Supplier
    print("Seeding suppliers...")
    count = 0
    for data in SUPPLIERS_DATA:
        existing = await Supplier.get_or_none(supplier_code=data["supplier_code"])
        if not existing:
            await Supplier.create(**data)
            count += 1
    print(f"Created {count} suppliers")


async def seed_warehouses():
    from base.plugins.inventory.models.inventory_models import StockWarehouse
    print("Seeding warehouses...")
    count = 0
    for data in WAREHOUSES_DATA:
        existing = await StockWarehouse.get_or_none(warehouse_code=data["warehouse_code"])
        if not existing:
            await StockWarehouse.create(**data)
            count += 1
    print(f"Created {count} warehouses")


async def seed_inspection_standards():
    from base.plugins.quality.models.quality import InspectionStandard
    print("Seeding inspection standards...")
    count = 0
    for data in INSPECTION_STANDARDS_DATA:
        existing = await InspectionStandard.get_or_none(standard_code=data["standard_code"])
        if not existing:
            await InspectionStandard.create(**data)
            count += 1
    print(f"Created {count} inspection standards")


async def seed_sales_forecast():
    from base.plugins.mrp2.models.mrp_models import SalesForecast, SalesForecastDetail
    print("Seeding sales forecast...")
    today = date.today()
    q3_start = date(today.year, 7, 1)
    q3_end = date(today.year, 9, 30)
    
    forecast, created = await SalesForecast.get_or_create(forecast_code="FC-T100-Q3", defaults={
        "forecast_name": "听音T100 Q3销售预测",
        "forecast_type": "quarterly",
        "forecast_date": today,
        "start_date": q3_start,
        "end_date": q3_end,
        "status": "approved",
        "source": "manual",
        "created_by": "admin"
    })
    
    if created:
        await SalesForecastDetail.create(
            forecast_id=forecast.id,
            forecast_code="FC-T100-Q3",
            product_code="FG-T100",
            product_name="听音T100蓝牙耳机",
            period_type="month",
            period_start=date(today.year, 7, 1),
            period_end=date(today.year, 9, 30),
            forecast_quantity=Decimal("10000"),
            unit="副",
            confidence=Decimal("85")
        )
        print("Created sales forecast FC-T100-Q3")
    else:
        print("Sales forecast FC-T100-Q3 already exists")


async def seed_mps():
    from base.plugins.mrp2.models.mrp_models import MasterProductionSchedule, MPSPlanLine
    print("Seeding MPS...")
    today = date.today()
    q3_start = date(today.year, 7, 1)
    q3_end = date(today.year, 9, 30)
    
    mps, created = await MasterProductionSchedule.get_or_create(mps_code="MPS-T100-Q3", defaults={
        "mps_name": "听音T100 Q3主生产计划",
        "start_date": q3_start,
        "end_date": q3_end,
        "period_type": "week",
        "status": "approved",
        "forecast_code": "FC-T100-Q3",
        "plan_name": "Q3 Production Plan",
        "approved_by": "admin",
        "approved_at": datetime.now(),
        "demand_time_fence": 7,
        "planning_time_fence": 14,
        "created_by": "admin"
    })
    
    if created:
        await MPSPlanLine.create(
            mps_id=mps.id,
            mps_code="MPS-T100-Q3",
            line_no=1,
            product_code="FG-T100",
            product_name="听音T100蓝牙耳机",
            plan_quantity=Decimal("10000"),
            plan_start_date=date(today.year, 7, 15),
            plan_end_date=date(today.year, 9, 30),
            priority=5,
            bom_code="FG-T100",
            route_code="ROUTE-T100",
            capacity_check_result="pass"
        )
        print("Created MPS MPS-T100-Q3")
    else:
        print("MPS MPS-T100-Q3 already exists")


async def main():
    print("=" * 60)
    print("Seed Bluetooth Headset Test Data")
    print("=" * 60)
    
    print(f"DB Config: {settings.db_host}:{settings.db_port}/{settings.db_name}")
    
    from tortoise import Tortoise
    
    custom_orm_config = get_custom_orm_config()
    
    print("Initializing Tortoise ORM...")
    await Tortoise.init(config=custom_orm_config)
    print("Tortoise ORM initialized")
    
    print("Generating schemas...")
    await Tortoise.generate_schemas(safe=True)
    print("Schemas generated")
    
    await seed_products()
    await seed_materials()
    await seed_work_centers()
    await seed_processes()
    await seed_route()
    await seed_bom()
    await seed_suppliers()
    await seed_warehouses()
    await seed_inspection_standards()
    await seed_sales_forecast()
    await seed_mps()
    
    await Tortoise.close_connections()
    
    print("=" * 60)
    print("Seed data completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())