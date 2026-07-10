"""测试产品编码从物料表自动填充"""
import requests
import json

BASE_URL = "http://127.0.0.1:9998"

print("=" * 60)
print("测试：从物料创建产品，自动填充产品编码和名称")
print("=" * 60)

# 1. 创建测试成品物料
print("\n1. 创建测试成品物料...")
test_material = {
    "material_code": "FG-TEST-CODE-001",
    "material_name": "测试编码成品物料",
    "material_type": "finished",
    "unit": "台",
    "specification": "测试规格-A1",
    "is_active": True
}
resp = requests.post(f"{BASE_URL}/v1/mes/base-data/materials", json=test_material)
mat_data = resp.json()
mat_id = mat_data.get("data", {}).get("id")
print(f"   物料ID: {mat_id}")
print(f"   物料编码: {mat_data.get('data', {}).get('material_code')}")
print(f"   物料名称: {mat_data.get('data', {}).get('material_name')}")

# 2. 从物料创建产品
print("\n2. 从物料创建产品（传material_id + 价格等销售信息）...")
create_data = {
    "name": "这个名称会被覆盖吗？",
    "product_code": "这个编码会被覆盖吗？",
    "description": "测试描述",
    "price": "299.00",
    "original_price": "399.00",
    "stock": 50,
    "category": "蓝牙耳机",
    "is_stock_item": True,
    "material_id": mat_id,
    "is_active": True,
    "is_hot": False,
    "is_new": True,
    "tags": ["测试"]
}
resp = requests.post(f"{BASE_URL}/v1/product/", json=create_data)
prod_data = resp.json()
print(f"   状态码: {resp.status_code}")
print(f"   成功: {prod_data.get('success')}")
print(f"   消息: {prod_data.get('msg')}")

if prod_data.get("success"):
    prod = prod_data["data"]
    prod_id = prod["id"]
    print(f"\n   返回的产品信息:")
    print(f"   - product_code: {prod.get('product_code')}")
    print(f"   - name: {prod.get('name')}")
    print(f"   - is_stock_item: {prod.get('is_stock_item')}")
    print(f"   - price: {prod.get('price')}")
    print(f"   - category: {prod.get('category')}")

    # 3. 验证物料回写
    print("\n3. 验证物料product_id回写...")
    resp2 = requests.get(f"{BASE_URL}/v1/mes/base-data/materials/{mat_id}")
    mat_updated = resp2.json()
    mat_pid = mat_updated.get("data", {}).get("product_id")
    print(f"   物料product_id: {mat_pid}")
    print(f"   匹配: {'✅' if mat_pid == prod_id else '❌'}")

    # 4. 验证产品列表返回product_code
    print("\n4. 验证产品列表返回product_code...")
    resp3 = requests.get(f"{BASE_URL}/v1/product/list?is_stock_item=true&page_size=10")
    list_data = resp3.json()
    items = list_data.get("data", {}).get("items", [])
    has_code = all("product_code" in item for item in items)
    print(f"   所有产品都有product_code字段: {'✅' if has_code else '❌'}")
    for item in items[:3]:
        print(f"   - {item.get('product_code', 'N/A')} | {item.get('name')}")

    # 清理
    print("\n5. 清理测试数据...")
    requests.delete(f"{BASE_URL}/v1/product/{prod_id}")
    requests.delete(f"{BASE_URL}/v1/mes/base-data/materials/{mat_id}")
    print("   清理完成")
else:
    # 清理物料
    requests.delete(f"{BASE_URL}/v1/mes/base-data/materials/{mat_id}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
