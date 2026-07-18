import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any
from decimal import Decimal


class MockBom:
    def __init__(self, product_code, item_code, item_name, quantity, unit, scrap_rate=0, level=1, parent_item_code=None, is_active=True):
        self.product_code = product_code
        self.product_name = self._get_product_name(product_code)
        self.item_code = item_code
        self.item_name = item_name
        self.quantity = Decimal(str(quantity))
        self.unit = unit
        self.scrap_rate = Decimal(str(scrap_rate))
        self.level = level
        self.parent_item_code = parent_item_code
        self.is_active = is_active
        
    def _get_product_name(self, product_code):
        names = {
            "LIPSTICK-001": "口红-烈焰红",
            "FOUNDATION-001": "粉底液-自然色",
            "SERUM-001": "精华液-修护",
            "LIP-002": "口红膏体",
        }
        return names.get(product_code, "")

    @staticmethod
    def filter(product_code=None, is_active=True):
        return MockBomQuerySet(product_code, is_active)


class MockBomQuerySet:
    def __init__(self, product_code, is_active):
        self.product_code = product_code
        self.is_active = is_active
        
    async def first(self):
        if self.product_code == "LIPSTICK-001":
            return MockBom("LIPSTICK-001", "LIP-001", "口红管", 1, "个", 0, 1)
        return None
        
    async def exists(self):
        return self.product_code in ["LIPSTICK-001", "FOUNDATION-001", "SERUM-001", "LIP-002"]
        
    def order_by(self, field):
        return self
        
    async def all(self):
        items = []
        if self.product_code == "LIPSTICK-001":
            items.append(MockBom("LIPSTICK-001", "LIP-001", "口红管", 1, "个", 0.02, 1))
            items.append(MockBom("LIPSTICK-001", "LIP-002", "口红膏体", 3, "克", 0.05, 1))
            items.append(MockBom("LIPSTICK-001", "LIP-003", "口红盖", 1, "个", 0, 1))
            items.append(MockBom("LIPSTICK-001", "LIP-004", "包装盒", 1, "个", 0, 1))
        elif self.product_code == "FOUNDATION-001":
            items.append(MockBom("FOUNDATION-001", "FD-001", "粉底瓶", 1, "个", 0, 1))
            items.append(MockBom("FOUNDATION-001", "FD-002", "粉底液", 30, "毫升", 0.03, 1))
            items.append(MockBom("FOUNDATION-001", "FD-003", "泵头", 1, "个", 0, 1))
        elif self.product_code == "SERUM-001":
            items.append(MockBom("SERUM-001", "SER-001", "精华瓶", 1, "个", 0, 1))
            items.append(MockBom("SERUM-001", "SER-002", "精华液", 30, "毫升", 0.02, 1))
        elif self.product_code == "LIP-002":
            items.append(MockBom("LIP-002", "RAW-001", "色粉", 0.5, "克", 0.1, 2, "LIP-002"))
            items.append(MockBom("LIP-002", "RAW-002", "油脂", 2, "克", 0, 2, "LIP-002"))
            items.append(MockBom("LIP-002", "RAW-003", "蜡质", 0.5, "克", 0, 2, "LIP-002"))
        return items


class MockStockQuant:
    def __init__(self, product_code, quantity, reserved_quantity, available_quantity):
        self.product_code = product_code
        self.quantity = Decimal(str(quantity))
        self.reserved_quantity = Decimal(str(reserved_quantity))
        self.available_quantity = Decimal(str(available_quantity))

    @staticmethod
    def filter(product_code=None):
        return MockStockQuantQuerySet(product_code)


class MockStockQuantQuerySet:
    def __init__(self, product_code):
        self.product_code = product_code
        
    async def all(self):
        stock_data = {
            "LIP-001": {"quantity": 100, "reserved": 20, "available": 80},
            "LIP-002": {"quantity": 500, "reserved": 100, "available": 400},
            "LIP-003": {"quantity": 50, "reserved": 0, "available": 50},
            "LIP-004": {"quantity": 200, "reserved": 50, "available": 150},
            "FD-001": {"quantity": 30, "reserved": 10, "available": 20},
            "FD-002": {"quantity": 1000, "reserved": 500, "available": 500},
            "FD-003": {"quantity": 25, "reserved": 5, "available": 20},
            "SER-001": {"quantity": 100, "reserved": 0, "available": 100},
            "SER-002": {"quantity": 500, "reserved": 0, "available": 500},
            "RAW-001": {"quantity": 100, "reserved": 20, "available": 80},
            "RAW-002": {"quantity": 200, "reserved": 50, "available": 150},
            "RAW-003": {"quantity": 50, "reserved": 0, "available": 50},
        }
        data = stock_data.get(self.product_code, {"quantity": 0, "reserved": 0, "available": 0})
        return [MockStockQuant(self.product_code, data["quantity"], data["reserved"], data["available"])]


class MockPurchaseOrder:
    def __init__(self, item_code, quantity, received_quantity, status):
        self.item_code = item_code
        self.quantity = Decimal(str(quantity))
        self.received_quantity = Decimal(str(received_quantity))
        self.status = status

    @staticmethod
    def filter(item_code=None, status=None):
        return MockPOQuerySet(item_code, status)


class MockPOQuerySet:
    def __init__(self, item_code, status):
        self.item_code = item_code
        self.status = status
        
    async def all(self):
        po_data = {
            "LIP-001": [{"quantity": 50, "received": 0}],
            "LIP-003": [{"quantity": 100, "received": 30}],
            "FD-001": [{"quantity": 20, "received": 0}],
        }
        result = []
        for po in po_data.get(self.item_code, []):
            result.append(MockPurchaseOrder(self.item_code, po["quantity"], po["received"], "confirmed"))
        return result


class MockManufacturingOrder:
    def __init__(self, id, mo_code, product_code, product_name, quantity, status):
        self.id = id
        self.mo_code = mo_code
        self.product_code = product_code
        self.product_name = product_name
        self.quantity = quantity
        self.status = status

    @staticmethod
    def filter(id=None, mo_code=None):
        return MockMOQuerySet(id, mo_code)


class MockMOQuerySet:
    def __init__(self, id, mo_code):
        self.id = id
        self.mo_code = mo_code
        
    async def first(self):
        mo_data = {
            1: MockManufacturingOrder(1, "MO-20260718-001", "LIPSTICK-001", "口红-烈焰红", 50, "planned"),
            2: MockManufacturingOrder(2, "MO-20260718-002", "FOUNDATION-001", "粉底液-自然色", 30, "planned"),
        }
        if self.id is not None:
            return mo_data.get(self.id)
        if self.mo_code is not None:
            for mo in mo_data.values():
                if mo.mo_code == self.mo_code:
                    return mo
        return None


import base.plugins.mes.services.kit_check_service as kit_service

kit_service.Bom = MockBom
kit_service.StockQuant = MockStockQuant
kit_service.PurchaseOrder = MockPurchaseOrder
kit_service.ManufacturingOrder = MockManufacturingOrder
kit_service.BOM_AVAILABLE = True
kit_service.QUANT_AVAILABLE = True
kit_service.PO_AVAILABLE = True
kit_service.KIT_CHECK_AVAILABLE = True


async def test_kit_check_by_bom():
    print("=" * 60)
    print("测试1: 检查BOM齐套情况（口红，生产50支）")
    print("=" * 60)
    
    result = await kit_service.KitCheckService.check_kit_by_bom("LIPSTICK-001", 50)
    
    print(f"\n产品编码: {result['product_code']}")
    print(f"产品名称: {result['product_name']}")
    print(f"生产数量: {result['required_quantity']}")
    print(f"物料总数: {result['total_items']}")
    print(f"齐套状态: {result['kit_status']}")
    print(f"齐套率: {result['kit_rate']}%")
    print(f"缺料数量: {result['shortage_items']}")
    
    print("\n物料明细:")
    for item in result['items']:
        status = "✅" if not item['is_shortage'] else "❌"
        print(f"  {status} {item['item_name']}({item['item_code']}):")
        print(f"    需求: {item['required_quantity']:.2f}{item['unit']}")
        print(f"    库存: {item['total_stock']:.2f}{item['unit']}")
        print(f"    预留: {item['reserved_stock']:.2f}{item['unit']}")
        print(f"    可用: {item['available_stock']:.2f}{item['unit']}")
        print(f"    在途: {item['on_order_stock']:.2f}{item['unit']}")
        print(f"    净可用: {item['net_available']:.2f}{item['unit']}")
        if item['is_shortage']:
            print(f"    ⚠️ 缺料: {item['shortage']:.2f}{item['unit']}")
    
    if result['shortage_list']:
        print("\n缺料清单:")
        for item in result['shortage_list']:
            print(f"  ❌ {item['item_name']}({item['item_code']}): 需{item['required_quantity']:.2f}{item['unit']}, 可用{item['available_quantity']:.2f}{item['unit']}, 缺{item['shortage']:.2f}{item['unit']}")
    
    assert result['kit_status'] in ['full_kit', 'partial_kit', 'no_kit'], "齐套状态无效"
    assert result['kit_rate'] >= 0 and result['kit_rate'] <= 100, "齐套率超出范围"
    assert result['total_items'] == 6, "物料数量不正确（含展开原材料）"
    
    print("\n✅ 测试1通过")


async def test_kit_check_by_mo():
    print("\n" + "=" * 60)
    print("测试2: 检查制造订单齐套情况")
    print("=" * 60)
    
    result = await kit_service.KitCheckService.check_kit_by_mo(1)
    
    print(f"\n制造订单ID: {result['mo_id']}")
    print(f"制造订单编码: {result['mo_code']}")
    print(f"订单状态: {result['mo_status']}")
    print(f"产品编码: {result['product_code']}")
    print(f"产品名称: {result['product_name']}")
    print(f"生产数量: {result['required_quantity']}")
    print(f"齐套状态: {result['kit_status']}")
    print(f"齐套率: {result['kit_rate']}%")
    
    assert 'mo_id' in result, "缺少mo_id字段"
    assert 'mo_code' in result, "缺少mo_code字段"
    assert result['mo_code'] == "MO-20260718-001", "制造订单编码不正确"
    
    print("\n✅ 测试2通过")


async def test_shortage_list():
    print("\n" + "=" * 60)
    print("测试3: 获取缺料清单")
    print("=" * 60)
    
    shortage_list = await kit_service.KitCheckService.get_shortage_list(1)
    
    print(f"\n缺料数量: {len(shortage_list)}")
    for item in shortage_list:
        print(f"  ❌ {item['item_name']}({item['item_code']}): 缺{item['shortage']:.2f}{item['unit']}")
    
    print("\n✅ 测试3通过")


async def test_kit_status_by_mo():
    print("\n" + "=" * 60)
    print("测试4: 获取齐套状态")
    print("=" * 60)
    
    status = await kit_service.KitCheckService.get_kit_status_by_mo("MO-20260718-001")
    
    print(f"\n齐套状态: {status}")
    assert status in ['full_kit', 'partial_kit', 'no_kit', 'unknown'], "齐套状态无效"
    
    print("\n✅ 测试4通过")


async def test_full_kit_scenario():
    print("\n" + "=" * 60)
    print("测试5: 完全齐套场景（精华液，生产10瓶）")
    print("=" * 60)
    
    result = await kit_service.KitCheckService.check_kit_by_bom("SERUM-001", 10)
    
    print(f"\n产品编码: {result['product_code']}")
    print(f"齐套状态: {result['kit_status']}")
    print(f"齐套率: {result['kit_rate']}%")
    
    assert result['kit_status'] == 'full_kit', "应该是完全齐套"
    assert result['kit_rate'] == 100.0, "齐套率应该是100%"
    assert result['shortage_items'] == 0, "不应该有缺料"
    
    print("\n✅ 测试5通过")


async def test_partial_kit_scenario():
    print("\n" + "=" * 60)
    print("测试6: 部分齐套场景（粉底液，生产30瓶）")
    print("=" * 60)
    
    result = await kit_service.KitCheckService.check_kit_by_bom("FOUNDATION-001", 30)
    
    print(f"\n产品编码: {result['product_code']}")
    print(f"齐套状态: {result['kit_status']}")
    print(f"齐套率: {result['kit_rate']}%")
    print(f"缺料数量: {result['shortage_items']}")
    
    assert result['kit_status'] == 'partial_kit', "应该是部分齐套"
    assert result['shortage_items'] > 0, "应该有缺料"
    
    print("\n✅ 测试6通过")


async def test_no_kit_scenario():
    print("\n" + "=" * 60)
    print("测试7: 不齐套场景（不存在的产品）")
    print("=" * 60)
    
    result = await kit_service.KitCheckService.check_kit_by_bom("NONEXISTENT-001", 10)
    
    print(f"\n产品编码: {result['product_code']}")
    print(f"齐套状态: {result['kit_status']}")
    print(f"消息: {result.get('msg', '')}")
    
    assert result['kit_status'] == 'no_kit', "应该是不齐套"
    assert 'msg' in result and result['msg'], "应该有错误消息"
    
    print("\n✅ 测试7通过")


async def test_batch_check():
    print("\n" + "=" * 60)
    print("测试8: 批量齐套检查")
    print("=" * 60)
    
    results = await kit_service.KitCheckService.batch_check_kit([1, 2])
    
    print(f"\n检查订单数量: {len(results)}")
    for result in results:
        print(f"  订单 {result['mo_code']}: {result['kit_status']} ({result['kit_rate']}%)")
    
    assert len(results) == 2, "应该返回2个订单的结果"
    
    print("\n✅ 测试8通过")


async def test_bom_recursion():
    print("\n" + "=" * 60)
    print("测试9: 多级BOM递归展开")
    print("=" * 60)
    
    result = await kit_service.KitCheckService.check_kit_by_bom("LIPSTICK-001", 10)
    
    print(f"\n产品编码: {result['product_code']}")
    print(f"物料总数: {result['total_items']}")
    
    raw_materials = [item for item in result['items'] if item['item_code'].startswith('RAW-')]
    print(f"原材料数量(展开后): {len(raw_materials)}")
    
    for item in raw_materials:
        print(f"  {item['item_name']}({item['item_code']}): {item['required_quantity']:.2f}{item['unit']}")
    
    assert len(raw_materials) == 3, "应该展开3种原材料"
    
    print("\n✅ 测试9通过")


async def main():
    print("=" * 60)
    print("齐套检查服务单元测试")
    print("=" * 60)
    
    import asyncio
    tests = [
        test_kit_check_by_bom,
        test_kit_check_by_mo,
        test_shortage_list,
        test_kit_status_by_mo,
        test_full_kit_scenario,
        test_partial_kit_scenario,
        test_no_kit_scenario,
        test_batch_check,
        test_bom_recursion,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"\n❌ {test.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{len(tests)} 通过, {failed}/{len(tests)} 失败")
    print("=" * 60)
    
    if failed > 0:
        exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())