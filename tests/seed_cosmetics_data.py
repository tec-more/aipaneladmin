import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.common.setting import TORTOISE_ORM, settings


COSMETICS_MODELS = [
    "base.plugins.mes.models.base_data",
    "base.plugins.mrp2.models.mrp_models",
    "base.plugins.quality.models.quality",
    "base.plugins.inventory.models.inventory_models",
    "base.plugins.purchase.models.supplier",
    "base.plugins.purchase.models.purchase",
    "base.plugins.product.models.product",
    "base.plugins.sales.models.order",
]


def get_custom_orm_config():
    config = TORTOISE_ORM.copy()
    existing_models = config["apps"]["models"]["models"]
    for model_path in COSMETICS_MODELS:
        if model_path not in existing_models:
            existing_models.append(model_path)
    return config


PRODUCTS_DATA = [
    {
        "name": "花妍玫瑰精华液",
        "description": "50ml玫瑰精华液，深层补水，淡化细纹，适合干性和混合性肤质",
        "price": Decimal("398.00"),
        "original_price": Decimal("498.00"),
        "stock": 0,
        "category": "面部精华",
        "tags": ["玫瑰精华", "补水", "淡化细纹"],
        "images": [],
        "is_active": True,
        "is_hot": True,
        "is_new": True,
        "is_stock_item": True,
        "uom_code": "瓶",
        "uom_name": "瓶",
        "product_type": "item",
        "price_mode": "fixed",
    },
    {
        "name": "花妍丝绒口红",
        "description": "3.5g丝绒质地口红，显色持久，滋润不拔干",
        "price": Decimal("168.00"),
        "original_price": Decimal("198.00"),
        "stock": 0,
        "category": "口红",
        "tags": ["丝绒", "显色", "持久"],
        "images": [],
        "is_active": True,
        "is_hot": True,
        "is_new": True,
        "is_stock_item": True,
        "uom_code": "支",
        "uom_name": "支",
        "product_type": "item",
        "price_mode": "fixed",
    },
    {
        "name": "花妍保湿爽肤水",
        "description": "150ml保湿爽肤水，温和补水，调节肌肤水油平衡",
        "price": Decimal("188.00"),
        "original_price": Decimal("238.00"),
        "stock": 0,
        "category": "爽肤水",
        "tags": ["保湿", "补水", "温和"],
        "images": [],
        "is_active": True,
        "is_hot": False,
        "is_new": False,
        "is_stock_item": True,
        "uom_code": "瓶",
        "uom_name": "瓶",
        "product_type": "item",
        "price_mode": "fixed",
    },
    {
        "name": "花妍补水面膜",
        "description": "25ml/片补水面膜，密集补水，舒缓肌肤",
        "price": Decimal("128.00"),
        "original_price": Decimal("158.00"),
        "stock": 0,
        "category": "面膜",
        "tags": ["补水", "舒缓", "面膜"],
        "images": [],
        "is_active": True,
        "is_hot": False,
        "is_new": False,
        "is_stock_item": True,
        "uom_code": "片",
        "uom_name": "片",
        "product_type": "item",
        "price_mode": "fixed",
    },
]

PRODUCT_MATERIAL_MAP = {
    "花妍玫瑰精华液": "FG-ESS-001",
    "花妍丝绒口红": "FG-LIP-001",
    "花妍保湿爽肤水": "FG-TONER-001",
    "花妍补水面膜": "FG-MASK-001",
}

MATERIALS_DATA = [
    {"material_code": "FG-ESS-001", "material_name": "花妍玫瑰精华液", "material_type": "finished", "unit": "瓶", "specification": "50ml/玫瑰精华", "product_id": None},
    {"material_code": "FG-LIP-001", "material_name": "花妍丝绒口红", "material_type": "finished", "unit": "支", "specification": "3.5g/丝绒质地", "product_id": None},
    {"material_code": "FG-TONER-001", "material_name": "花妍保湿爽肤水", "material_type": "finished", "unit": "瓶", "specification": "150ml/保湿", "product_id": None},
    {"material_code": "FG-MASK-001", "material_name": "花妍补水面膜", "material_type": "finished", "unit": "片", "specification": "25ml/片", "product_id": None},
    {"material_code": "SEMI-BASE-001", "material_name": "口红基底膏", "material_type": "semi_finished", "unit": "g", "specification": "混合原料", "product_id": None},
    {"material_code": "SEMI-ESS-BASE", "material_name": "精华液基底", "material_type": "semi_finished", "unit": "ml", "specification": "乳化基底", "product_id": None},
    {"material_code": "RM-ROSE-EXTR", "material_name": "玫瑰提取物", "material_type": "raw", "unit": "kg", "specification": "天然萃取", "product_id": None},
    {"material_code": "RM-VITAMIN-C", "material_name": "维生素C", "material_type": "raw", "unit": "kg", "specification": "纯度99%", "product_id": None},
    {"material_code": "RM-GLYCERIN", "material_name": "甘油", "material_type": "raw", "unit": "kg", "specification": "食品级", "product_id": None},
    {"material_code": "RM-WAX", "material_name": "蜂蜡", "material_type": "raw", "unit": "kg", "specification": "天然蜂蜡", "product_id": None},
    {"material_code": "RM-OIL", "material_name": "植物油", "material_type": "raw", "unit": "kg", "specification": "植物提取", "product_id": None},
    {"material_code": "RM-PIGMENT-RED", "material_name": "红色色素", "material_type": "raw", "unit": "g", "specification": "口红专用", "product_id": None},
    {"material_code": "RM-PIGMENT-PINK", "material_name": "粉色色素", "material_type": "raw", "unit": "g", "specification": "口红专用", "product_id": None},
    {"material_code": "RM-PIGMENT-ORANGE", "material_name": "橙色色素", "material_type": "raw", "unit": "g", "specification": "口红专用", "product_id": None},
    {"material_code": "RM-BOTTLE", "material_name": "精华液瓶", "material_type": "raw", "unit": "个", "specification": "50ml玻璃", "product_id": None},
    {"material_code": "RM-TUBE", "material_name": "口红管", "material_type": "raw", "unit": "个", "specification": "铝制", "product_id": None},
    {"material_code": "RM-BOX", "material_name": "包装盒", "material_type": "raw", "unit": "个", "specification": "彩盒", "product_id": None},
    {"material_code": "RM-MANUAL", "material_name": "说明书", "material_type": "raw", "unit": "本", "specification": "-", "product_id": None},
]


BOM_DATA = [
    {"product_code": "FG-LIP-001", "product_name": "花妍丝绒口红", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "SEMI-BASE-001", "item_name": "口红基底膏", "quantity": Decimal("3.5"), "unit": "g", "scrap_rate": Decimal("0.02")},
    {"product_code": "FG-LIP-001", "product_name": "花妍丝绒口红", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "RM-PIGMENT-RED", "item_name": "红色色素", "quantity": Decimal("0.2"), "unit": "g", "scrap_rate": Decimal("0")},
    {"product_code": "FG-LIP-001", "product_name": "花妍丝绒口红", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "RM-TUBE", "item_name": "口红管", "quantity": Decimal("1"), "unit": "个", "scrap_rate": Decimal("0")},
    {"product_code": "FG-LIP-001", "product_name": "花妍丝绒口红", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "RM-BOX", "item_name": "包装盒", "quantity": Decimal("1"), "unit": "个", "scrap_rate": Decimal("0")},
    {"product_code": "SEMI-BASE-001", "product_name": "口红基底膏", "version": "V1.0", "level": 2, "parent_item_code": "FG-LIP-001",
     "item_code": "RM-WAX", "item_name": "蜂蜡", "quantity": Decimal("0.5"), "unit": "g", "scrap_rate": Decimal("0.01")},
    {"product_code": "SEMI-BASE-001", "product_name": "口红基底膏", "version": "V1.0", "level": 2, "parent_item_code": "FG-LIP-001",
     "item_code": "RM-OIL", "item_name": "植物油", "quantity": Decimal("1.5"), "unit": "g", "scrap_rate": Decimal("0")},
    {"product_code": "SEMI-BASE-001", "product_name": "口红基底膏", "version": "V1.0", "level": 2, "parent_item_code": "FG-LIP-001",
     "item_code": "RM-GLYCERIN", "item_name": "甘油", "quantity": Decimal("0.5"), "unit": "g", "scrap_rate": Decimal("0")},
    {"product_code": "FG-ESS-001", "product_name": "花妍玫瑰精华液", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "SEMI-ESS-BASE", "item_name": "精华液基底", "quantity": Decimal("45"), "unit": "ml", "scrap_rate": Decimal("0.01")},
    {"product_code": "FG-ESS-001", "product_name": "花妍玫瑰精华液", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "RM-ROSE-EXTR", "item_name": "玫瑰提取物", "quantity": Decimal("3"), "unit": "ml", "scrap_rate": Decimal("0")},
    {"product_code": "FG-ESS-001", "product_name": "花妍玫瑰精华液", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "RM-VITAMIN-C", "item_name": "维生素C", "quantity": Decimal("1"), "unit": "g", "scrap_rate": Decimal("0")},
    {"product_code": "FG-ESS-001", "product_name": "花妍玫瑰精华液", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "RM-BOTTLE", "item_name": "精华液瓶", "quantity": Decimal("1"), "unit": "个", "scrap_rate": Decimal("0")},
    {"product_code": "FG-ESS-001", "product_name": "花妍玫瑰精华液", "version": "V1.0", "level": 1, "parent_item_code": None,
     "item_code": "RM-BOX", "item_name": "包装盒", "quantity": Decimal("1"), "unit": "个", "scrap_rate": Decimal("0")},
    {"product_code": "SEMI-ESS-BASE", "product_name": "精华液基底", "version": "V1.0", "level": 2, "parent_item_code": "FG-ESS-001",
     "item_code": "RM-GLYCERIN", "item_name": "甘油", "quantity": Decimal("5"), "unit": "ml", "scrap_rate": Decimal("0")},
    {"product_code": "SEMI-ESS-BASE", "product_name": "精华液基底", "version": "V1.0", "level": 2, "parent_item_code": "FG-ESS-001",
     "item_code": "RM-OIL", "item_name": "植物油", "quantity": Decimal("10"), "unit": "ml", "scrap_rate": Decimal("0")},
]


WORK_CENTERS_DATA = [
    {"work_center_code": "WC-MIX", "work_center_name": "原料混合车间", "department": "生产部", "location": "A栋1楼", "capacity": 500},
    {"work_center_code": "WC-MOLD", "work_center_name": "成型车间", "department": "生产部", "location": "A栋2楼", "capacity": 2000},
    {"work_center_code": "WC-EMUL", "work_center_name": "乳化车间", "department": "生产部", "location": "A栋3楼", "capacity": 3000},
    {"work_center_code": "WC-FILL", "work_center_name": "灌装车间", "department": "生产部", "location": "B栋1楼", "capacity": 2500},
    {"work_center_code": "WC-CAP", "work_center_name": "旋盖车间", "department": "生产部", "location": "B栋2楼", "capacity": 3000},
    {"work_center_code": "WC-COAT", "work_center_name": "涂层车间", "department": "生产部", "location": "B栋3楼", "capacity": 1500},
    {"work_center_code": "WC-PKG", "work_center_name": "包装车间", "department": "生产部", "location": "C栋1楼", "capacity": 3000},
    {"work_center_code": "WC-QC", "work_center_name": "质检车间", "department": "品质部", "location": "C栋2楼", "capacity": 2000},
]


PROCESSES_DATA = [
    {"process_code": "PROC-MIX", "process_name": "原料混合", "process_type": "mixing", "sequence": 10,
     "work_center_code": "WC-MIX", "work_center_name": "原料混合车间", "standard_time": Decimal("60")},
    {"process_code": "PROC-MOLD", "process_name": "口红成型", "process_type": "molding", "sequence": 20,
     "work_center_code": "WC-MOLD", "work_center_name": "成型车间", "standard_time": Decimal("30")},
    {"process_code": "PROC-EMUL", "process_name": "乳化处理", "process_type": "emulsifying", "sequence": 20,
     "work_center_code": "WC-EMUL", "work_center_name": "乳化车间", "standard_time": Decimal("60")},
    {"process_code": "PROC-FILL", "process_name": "灌装", "process_type": "filling", "sequence": 30,
     "work_center_code": "WC-FILL", "work_center_name": "灌装车间", "standard_time": Decimal("30")},
    {"process_code": "PROC-CAP", "process_name": "旋盖封口", "process_type": "capping", "sequence": 40,
     "work_center_code": "WC-CAP", "work_center_name": "旋盖车间", "standard_time": Decimal("15")},
    {"process_code": "PROC-COAT", "process_name": "表面涂层", "process_type": "coating", "sequence": 30,
     "work_center_code": "WC-COAT", "work_center_name": "涂层车间", "standard_time": Decimal("45")},
    {"process_code": "PROC-PKG", "process_name": "成品包装", "process_type": "packaging", "sequence": 50,
     "work_center_code": "WC-PKG", "work_center_name": "包装车间", "standard_time": Decimal("15")},
    {"process_code": "PROC-INSPECT", "process_name": "质量检验", "process_type": "inspection", "sequence": 60,
     "work_center_code": "WC-QC", "work_center_name": "质检车间", "standard_time": Decimal("20")},
]


ROUTE_PROCESSES_LIP_DATA = [
    {"route_code": "ROUTE-LIP-001", "process_code": "PROC-MIX", "process_name": "原料混合", "sequence": 10,
     "work_center_code": "WC-MIX", "work_center_name": "原料混合车间"},
    {"route_code": "ROUTE-LIP-001", "process_code": "PROC-MOLD", "process_name": "口红成型", "sequence": 20,
     "work_center_code": "WC-MOLD", "work_center_name": "成型车间"},
    {"route_code": "ROUTE-LIP-001", "process_code": "PROC-COAT", "process_name": "表面涂层", "sequence": 30,
     "work_center_code": "WC-COAT", "work_center_name": "涂层车间"},
    {"route_code": "ROUTE-LIP-001", "process_code": "PROC-PKG", "process_name": "成品包装", "sequence": 50,
     "work_center_code": "WC-PKG", "work_center_name": "包装车间"},
    {"route_code": "ROUTE-LIP-001", "process_code": "PROC-INSPECT", "process_name": "质量检验", "sequence": 60,
     "work_center_code": "WC-QC", "work_center_name": "质检车间"},
]


ROUTE_PROCESSES_ESS_DATA = [
    {"route_code": "ROUTE-ESS-001", "process_code": "PROC-MIX", "process_name": "原料混合", "sequence": 10,
     "work_center_code": "WC-MIX", "work_center_name": "原料混合车间"},
    {"route_code": "ROUTE-ESS-001", "process_code": "PROC-EMUL", "process_name": "乳化处理", "sequence": 20,
     "work_center_code": "WC-EMUL", "work_center_name": "乳化车间"},
    {"route_code": "ROUTE-ESS-001", "process_code": "PROC-FILL", "process_name": "灌装", "sequence": 30,
     "work_center_code": "WC-FILL", "work_center_name": "灌装车间"},
    {"route_code": "ROUTE-ESS-001", "process_code": "PROC-CAP", "process_name": "旋盖封口", "sequence": 40,
     "work_center_code": "WC-CAP", "work_center_name": "旋盖车间"},
    {"route_code": "ROUTE-ESS-001", "process_code": "PROC-PKG", "process_name": "成品包装", "sequence": 50,
     "work_center_code": "WC-PKG", "work_center_name": "包装车间"},
    {"route_code": "ROUTE-ESS-001", "process_code": "PROC-INSPECT", "process_name": "质量检验", "sequence": 60,
     "work_center_code": "WC-QC", "work_center_name": "质检车间"},
]


SUPPLIERS_DATA = [
    {"supplier_code": "SUP-ROSE-001", "supplier_name": "云南玫瑰种植基地", "supplier_type": "manufacturer",
     "contact_person": "张经理", "phone": "0871-11112222", "address": "云南省昆明市"},
    {"supplier_code": "SUP-CHEM-001", "supplier_name": "上海化工原料公司", "supplier_type": "manufacturer",
     "contact_person": "李总", "phone": "021-33334444", "address": "上海市浦东新区"},
    {"supplier_code": "SUP-WAX-001", "supplier_name": "浙江蜂蜡制品厂", "supplier_type": "manufacturer",
     "contact_person": "王经理", "phone": "0571-55556666", "address": "浙江省杭州市"},
    {"supplier_code": "SUP-PIGMENT-001", "supplier_name": "广州色素公司", "supplier_type": "manufacturer",
     "contact_person": "陈总", "phone": "020-77778888", "address": "广州市白云区"},
    {"supplier_code": "SUP-PACK-001", "supplier_name": "深圳包装材料厂", "supplier_type": "manufacturer",
     "contact_person": "刘经理", "phone": "0755-99990000", "address": "深圳市宝安区"},
]


WAREHOUSES_DATA = [
    {"warehouse_code": "WH-RAW", "warehouse_name": "原材料仓", "warehouse_type": "internal", "address": "A栋1楼"},
    {"warehouse_code": "WH-SEMI", "warehouse_name": "半成品仓", "warehouse_type": "internal", "address": "A栋2楼"},
    {"warehouse_code": "WH-FG", "warehouse_name": "成品仓", "warehouse_type": "internal", "address": "B栋1楼"},
    {"warehouse_code": "WH-PACK", "warehouse_name": "包装材料仓", "warehouse_type": "internal", "address": "B栋2楼"},
]


INSPECTION_STANDARDS_DATA = [
    {
        "standard_code": "STD-LIP-001",
        "standard_name": "花妍丝绒口红检验标准",
        "material_code": "FG-LIP-001",
        "inspection_type": "FQC",
        "items": [
            {"name": "外观检查", "method": "目视检查", "standard": "外观无划痕，壳体无变形"},
            {"name": "质地检查", "method": "涂抹测试", "standard": "质地顺滑，无结块"},
            {"name": "色牢度测试", "method": "纸巾擦拭", "standard": "无明显掉色"},
            {"name": "重金属检测", "method": "仪器检测", "standard": "符合国家标准"},
        ],
        "sampling_rule": "AQL 2.5，抽检比例10%"
    },
    {
        "standard_code": "STD-ESS-001",
        "standard_name": "花妍玫瑰精华液检验标准",
        "material_code": "FG-ESS-001",
        "inspection_type": "FQC",
        "items": [
            {"name": "外观检查", "method": "目视检查", "standard": "瓶身无破损，标签完整"},
            {"name": "成分检测", "method": "仪器分析", "standard": "成分含量达标"},
            {"name": "PH值测试", "method": "PH试纸", "standard": "PH值5.5-6.5"},
            {"name": "微生物检测", "method": "培养检测", "standard": "符合卫生标准"},
        ],
        "sampling_rule": "AQL 2.5，抽检比例10%"
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
    await BomVersion.get_or_create(product_code="FG-LIP-001", version="V1.0", defaults={
        "product_name": "花妍丝绒口红", "status": "active"
    })
    await BomVersion.get_or_create(product_code="SEMI-BASE-001", version="V1.0", defaults={
        "product_name": "口红基底膏", "status": "active"
    })
    await BomVersion.get_or_create(product_code="FG-ESS-001", version="V1.0", defaults={
        "product_name": "花妍玫瑰精华液", "status": "active"
    })
    await BomVersion.get_or_create(product_code="SEMI-ESS-BASE", version="V1.0", defaults={
        "product_name": "精华液基底", "status": "active"
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
    print("Seeding routes...")
    await Route.get_or_create(route_code="ROUTE-LIP-001", defaults={
        "route_name": "花妍丝绒口红工艺路线",
        "product_code": "FG-LIP-001",
        "product_name": "花妍丝绒口红",
        "bom_code": "FG-LIP-001",
        "bom_version": "V1.0",
        "version": "V1.0"
    })
    
    await Route.get_or_create(route_code="ROUTE-ESS-001", defaults={
        "route_name": "花妍玫瑰精华液工艺路线",
        "product_code": "FG-ESS-001",
        "product_name": "花妍玫瑰精华液",
        "bom_code": "FG-ESS-001",
        "bom_version": "V1.0",
        "version": "V1.0"
    })
    
    count = 0
    for data in ROUTE_PROCESSES_LIP_DATA:
        existing = await RouteProcess.get_or_none(route_code=data["route_code"], process_code=data["process_code"])
        if not existing:
            await RouteProcess.create(**data)
            count += 1
    
    for data in ROUTE_PROCESSES_ESS_DATA:
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
    
    forecast, created = await SalesForecast.get_or_create(forecast_code="FC-CO-Q3", defaults={
        "forecast_name": "花妍美妆Q3销售预测",
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
            forecast_code="FC-CO-Q3",
            product_code="FG-LIP-001",
            product_name="花妍丝绒口红",
            period_type="month",
            period_start=date(today.year, 7, 1),
            period_end=date(today.year, 9, 30),
            forecast_quantity=Decimal("5000"),
            unit="支",
            confidence=Decimal("90")
        )
        await SalesForecastDetail.create(
            forecast_id=forecast.id,
            forecast_code="FC-CO-Q3",
            product_code="FG-ESS-001",
            product_name="花妍玫瑰精华液",
            period_type="month",
            period_start=date(today.year, 7, 1),
            period_end=date(today.year, 9, 30),
            forecast_quantity=Decimal("3000"),
            unit="瓶",
            confidence=Decimal("85")
        )
        print("Created sales forecast FC-CO-Q3")
    else:
        print("Sales forecast FC-CO-Q3 already exists")


async def seed_mps():
    from base.plugins.mrp2.models.mrp_models import MasterProductionSchedule, MPSPlanLine
    print("Seeding MPS...")
    today = date.today()
    q3_start = date(today.year, 7, 1)
    q3_end = date(today.year, 9, 30)
    
    mps, created = await MasterProductionSchedule.get_or_create(mps_code="MPS-CO-Q3", defaults={
        "mps_name": "花妍美妆Q3主生产计划",
        "start_date": q3_start,
        "end_date": q3_end,
        "period_type": "week",
        "status": "approved",
        "forecast_code": "FC-CO-Q3",
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
            mps_code="MPS-CO-Q3",
            line_no=1,
            product_code="FG-LIP-001",
            product_name="花妍丝绒口红",
            plan_quantity=Decimal("5000"),
            plan_start_date=date(today.year, 7, 15),
            plan_end_date=date(today.year, 9, 30),
            priority=5,
            bom_code="FG-LIP-001",
            route_code="ROUTE-LIP-001",
            capacity_check_result="pass"
        )
        await MPSPlanLine.create(
            mps_id=mps.id,
            mps_code="MPS-CO-Q3",
            line_no=2,
            product_code="FG-ESS-001",
            product_name="花妍玫瑰精华液",
            plan_quantity=Decimal("3000"),
            plan_start_date=date(today.year, 7, 15),
            plan_end_date=date(today.year, 9, 30),
            priority=5,
            bom_code="FG-ESS-001",
            route_code="ROUTE-ESS-001",
            capacity_check_result="pass"
        )
        print("Created MPS MPS-CO-Q3")
    else:
        print("MPS MPS-CO-Q3 already exists")


async def main():
    print("=" * 60)
    print("Seed Cosmetics Test Data")
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