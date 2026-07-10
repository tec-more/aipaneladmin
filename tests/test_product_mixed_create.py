"""
产品混合创建逻辑测试脚本
测试场景：
1. 获取可关联物料列表
2. 从物料创建库存商品
3. 直接创建虚拟商品
4. 异常场景校验
5. 列表过滤
"""
import requests
import json

BASE_URL = "http://127.0.0.1:9998"

def print_result(title, response, show_data=True):
    print(f"\n{'='*60}")
    print(f"测试: {title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    try:
        data = response.json()
        if show_data:
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2, default=str)[:2000]}")
        else:
            print(f"响应: {json.dumps(data, ensure_ascii=False)[:500]}")
    except:
        print(f"响应文本: {response.text[:500]}")
    print()
    return data


print("="*60)
print("产品混合创建逻辑测试")
print("="*60)

# ========== 测试1：获取可关联物料列表 ==========
print("\n>>> 测试1: 获取可关联物料列表")
resp = requests.get(f"{BASE_URL}/v1/product/materials/available")
data = print_result("获取可关联物料列表", resp)

available_materials = []
if data.get("data") and data["data"].get("items"):
    available_materials = data["data"]["items"]
    print(f"  可关联物料数量: {len(available_materials)}")
    for m in available_materials:
        print(f"  - ID:{m['id']} {m['material_code']} {m['material_name']} (product_id={m['product_id']})")
else:
    print("  ⚠ 没有可关联的物料，可能所有成品物料已关联产品")

# ========== 测试2：从物料创建库存商品 ==========
print("\n>>> 测试2: 从物料创建库存商品")

# 如果没有可关联的物料，先创建一个测试用成品物料
test_material_id = None
if not available_materials:
    print("  没有可关联的物料，先创建测试用成品物料...")
    test_material_data = {
        "material_code": "FG-TEST-001",
        "material_name": "测试用成品物料",
        "material_type": "finished",
        "unit": "个",
        "specification": "测试规格",
        "is_active": True
    }
    resp = requests.post(f"{BASE_URL}/v1/mes/base-data/materials", json=test_material_data)
    if resp.status_code in (200, 201):
        mat_resp_data = resp.json()
        test_material_id = mat_resp_data.get("data", {}).get("id")
        print(f"  ✅ 创建测试物料成功, ID: {test_material_id}")
    else:
        print(f"  ❌ 创建测试物料失败: {resp.text[:200]}")
else:
    test_material_id = available_materials[0]["id"]
    print(f"  使用已有物料 ID: {test_material_id}")

if test_material_id:
    # 获取物料详情
    resp = requests.get(f"{BASE_URL}/v1/mes/base-data/materials/{test_material_id}")
    mat_info = resp.json().get("data", {})
    print(f"  物料信息: {mat_info.get('material_code')} - {mat_info.get('material_name')}")
    print(f"  物料当前product_id: {mat_info.get('product_id')}")

    create_data = {
        "name": f"测试产品_{mat_info.get('material_name', '测试')}",
        "description": f"从物料{mat_info.get('material_code')}创建的测试产品",
        "price": "199.00",
        "original_price": "259.00",
        "stock": 100,
        "category": "蓝牙耳机",
        "is_stock_item": True,
        "material_id": test_material_id,
        "is_active": True,
        "is_hot": False,
        "is_new": True,
        "tags": ["新品", "测试"]
    }
    resp = requests.post(f"{BASE_URL}/v1/product/", json=create_data)
    data = print_result("从物料创建库存商品", resp)

    if data.get("success"):
        created_product_id = data["data"]["id"]
        print(f"  ✅ 产品创建成功, ID: {created_product_id}")
        print(f"  ✅ 产品名称: {data['data']['name']}")
        print(f"  ✅ is_stock_item: {data['data'].get('is_stock_item')}")

        # 验证物料是否已回写product_id
        print("\n  验证物料回写product_id...")
        resp2 = requests.get(f"{BASE_URL}/v1/mes/base-data/materials/{test_material_id}")
        if resp2.status_code == 200:
            mat_data = resp2.json()
            updated_pid = mat_data.get("data", {}).get("product_id")
            print(f"  物料product_id: {updated_pid}")
            if updated_pid == created_product_id:
                print("  ✅ 物料product_id回写成功!")
            else:
                print(f"  ❌ 物料product_id回写失败! 期望={created_product_id}, 实际={updated_pid}")

        # 测试4.3：尝试用已关联的物料再创建产品
        print("\n  4.3 尝试用已关联的物料再创建产品...")
        dup_data = {
            "name": "测试_重复关联产品",
            "price": "10.00",
            "is_stock_item": True,
            "material_id": test_material_id
        }
        resp_dup = requests.post(f"{BASE_URL}/v1/product/", json=dup_data)
        dup_data_resp = resp_dup.json()
        if "已关联" in str(dup_data_resp.get("msg", "")):
            print("  ✅ 正确拦截：该物料已关联其他产品")
        else:
            print(f"  ❌ 未正确拦截: {dup_data_resp.get('msg')}")

        # 清理：删除测试产品
        print("\n  清理测试数据...")
        requests.delete(f"{BASE_URL}/v1/product/{created_product_id}")
        print(f"  已删除测试产品 ID: {created_product_id}")

        # 如果是创建的测试物料，也删除
        if not available_materials and test_material_id:
            requests.delete(f"{BASE_URL}/v1/mes/base-data/materials/{test_material_id}")
            print(f"  已删除测试物料 ID: {test_material_id}")
    else:
        print(f"  ❌ 创建失败: {data.get('msg')}")

# ========== 测试3：直接创建虚拟商品 ==========
print("\n>>> 测试3: 直接创建虚拟商品")
virtual_data = {
    "name": "测试_月度会员套餐",
    "description": "月度会员，享受所有高级功能",
    "price": "49.90",
    "original_price": "99.00",
    "stock": 0,
    "category": "会员套餐",
    "is_stock_item": False,
    "recharge_hours": 720,
    "bonus_hours": 24,
    "is_active": True,
    "is_hot": True,
    "is_new": False,
    "tags": ["限时8折"],
    "discount_description": "限时8折"
}
resp = requests.post(f"{BASE_URL}/v1/product/", json=virtual_data)
data = print_result("直接创建虚拟商品", resp)

if data.get("success"):
    virtual_product_id = data["data"]["id"]
    print(f"  ✅ 虚拟商品创建成功, ID: {virtual_product_id}")
    print(f"  ✅ is_stock_item: {data['data'].get('is_stock_item')}")
    print(f"  ✅ recharge_hours: {data['data'].get('recharge_hours')}")
    print(f"  ✅ bonus_hours: {data['data'].get('bonus_hours')}")
    
    # 清理
    requests.delete(f"{BASE_URL}/v1/product/{virtual_product_id}")
    print(f"  已删除测试虚拟商品 ID: {virtual_product_id}")
else:
    print(f"  ❌ 创建失败: {data.get('msg')}")

# ========== 测试4：异常场景校验 ==========
print("\n>>> 测试4: 异常场景校验")

# 4.1 关联不存在的物料
print("\n  4.1 关联不存在的物料 (material_id=99999)")
bad_data = {
    "name": "测试_异常产品1",
    "price": "10.00",
    "is_stock_item": True,
    "material_id": 99999
}
resp = requests.post(f"{BASE_URL}/v1/product/", json=bad_data)
data = print_result("关联不存在的物料", resp, show_data=False)
if "物料不存在" in str(data.get("msg", "")):
    print("  ✅ 正确拦截：物料不存在")
else:
    print(f"  ❌ 未正确拦截: {data.get('msg')}")

# 4.2 关联非成品类型物料（原材料）
print("\n  4.2 关联原材料类型物料")
# 先查询一个原材料
resp_mat = requests.get(f"{BASE_URL}/v1/mes/base-data/materials?material_type=raw&page_size=1")
raw_material_id = None
if resp_mat.status_code == 200:
    mat_data = resp_mat.json()
    items = mat_data.get("data", {}).get("items", [])
    if items:
        raw_material_id = items[0].get("id")
        print(f"  使用原材料: ID={raw_material_id}, {items[0].get('material_name')}")

if raw_material_id:
    bad_data2 = {
        "name": "测试_异常产品2",
        "price": "10.00",
        "is_stock_item": True,
        "material_id": raw_material_id
    }
    resp = requests.post(f"{BASE_URL}/v1/product/", json=bad_data2)
    data = print_result("关联原材料物料", resp, show_data=False)
    if "成品类型" in str(data.get("msg", "")):
        print("  ✅ 正确拦截：只能关联成品类型的物料")
    else:
        print(f"  ❌ 未正确拦截: {data.get('msg')}")

# ========== 测试5：列表过滤 ==========
print("\n>>> 测试5: 列表过滤 (is_stock_item)")

# 获取库存商品
resp = requests.get(f"{BASE_URL}/v1/product/list?is_stock_item=true&page_size=5")
data = print_result("查询库存商品列表", resp, show_data=False)
stock_count = data.get("data", {}).get("total", 0)
print(f"  库存商品数量: {stock_count}")

# 获取虚拟商品
resp = requests.get(f"{BASE_URL}/v1/product/list?is_stock_item=false&page_size=5")
data = print_result("查询虚拟商品列表", resp, show_data=False)
virtual_count = data.get("data", {}).get("total", 0)
print(f"  虚拟商品数量: {virtual_count}")

# 验证过滤是否正确
resp = requests.get(f"{BASE_URL}/v1/product/list?is_stock_item=true&page_size=100")
data = resp.json()
items = data.get("data", {}).get("items", [])
all_stock = all(item.get("is_stock_item") == True for item in items)
print(f"  库存商品过滤验证: {'✅ 通过' if all_stock else '❌ 失败'}")

print("\n" + "="*60)
print("测试完成!")
print("="*60)
