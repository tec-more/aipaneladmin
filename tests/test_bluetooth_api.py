import requests
import json

BASE_URL = "http://127.0.0.1:9998/api/v1"

def login(username, password):
    url = f"{BASE_URL}/auth/login"
    data = {"username": username, "password": password}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        result = response.json()
        return result['data']['access_token']
    raise Exception(f"登录失败: {response.text}")

def test_category_crud(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=" * 60)
    print("TC-PROD-BT-001: 产品分类CRUD完整流程")
    print("=" * 60)
    
    categories = []
    
    print("\n1. 创建顶层分类 '消费电子'")
    data = {"name": "消费电子", "code": "CE", "sort_order": 1}
    response = requests.post(f"{BASE_URL}/product/categories", json=data, headers=headers)
    print(f"   响应: code={response.json().get('code')}, msg={response.json().get('msg')}")
    ce_category = response.json()['data']
    categories.append(ce_category)
    
    print("\n2. 创建子分类 '蓝牙耳机'")
    data = {"name": "蓝牙耳机", "code": "CE-BT", "sort_order": 1, "parent_id": ce_category['id']}
    response = requests.post(f"{BASE_URL}/product/categories", json=data, headers=headers)
    print(f"   响应: code={response.json().get('code')}, msg={response.json().get('msg')}")
    bt_category = response.json()['data']
    categories.append(bt_category)
    
    print("\n3. 创建三级分类 '真无线耳机'")
    data = {"name": "真无线耳机", "code": "CE-BT-TWS", "sort_order": 1, "parent_id": bt_category['id']}
    response = requests.post(f"{BASE_URL}/product/categories", json=data, headers=headers)
    print(f"   响应: code={response.json().get('code')}, msg={response.json().get('msg')}")
    tws_category = response.json()['data']
    categories.append(tws_category)
    
    print("\n4. 更新分类排序")
    data = {"sort_order": 2}
    response = requests.put(f"{BASE_URL}/product/categories/{tws_category['id']}", json=data, headers=headers)
    print(f"   响应: code={response.json().get('code')}, msg={response.json().get('msg')}")
    
    print("\n5. 搜索分类")
    response = requests.get(f"{BASE_URL}/product/categories?name=蓝牙", headers=headers)
    result = response.json()
    print(f"   搜索结果数量: {result['data']['total']}")
    
    print("\n6. 删除分类（需先删除子分类）")
    for cat in reversed(categories):
        response = requests.delete(f"{BASE_URL}/product/categories/{cat['id']}", headers=headers)
        print(f"   删除 {cat['name']}: code={response.json().get('code')}, msg={response.json().get('msg')}")
    
    print("\n✅ TC-PROD-BT-001 测试完成")

def test_attribute_management(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-PROD-BT-002: 产品属性管理")
    print("=" * 60)
    
    print("\n1. 创建属性 '蓝牙版本'")
    data = {"name": "蓝牙版本", "code": "bt_version", "category": "product", "sort_order": 1}
    response = requests.post(f"{BASE_URL}/product/attributes", json=data, headers=headers)
    print(f"   响应: code={response.json().get('code')}, msg={response.json().get('msg')}")
    attribute = response.json()['data']
    
    print("\n2. 添加属性值")
    values = ["5.0", "5.1", "5.2", "5.3", "5.4"]
    value_ids = []
    for v in values:
        data = {"attribute_id": attribute['id'], "value": v, "sort_order": values.index(v) + 1}
        response = requests.post(f"{BASE_URL}/product/attributes/values", json=data, headers=headers)
        value_ids.append(response.json()['data']['id'])
    print(f"   添加了 {len(values)} 个属性值")
    
    print("\n3. 更新属性排序")
    data = {"sort_order": 3}
    response = requests.put(f"{BASE_URL}/product/attributes/{attribute['id']}", json=data, headers=headers)
    print(f"   响应: code={response.json().get('code')}, msg={response.json().get('msg')}")
    
    print("\n4. 删除属性值 '5.0'")
    response = requests.delete(f"{BASE_URL}/product/attributes/values/{value_ids[0]}", headers=headers)
    print(f"   响应: code={response.json().get('code')}, msg={response.json().get('msg')}")
    
    print("\n5. 获取属性选项")
    response = requests.get(f"{BASE_URL}/product/attributes/options", headers=headers)
    result = response.json()
    print(f"   属性选项数量: {len(result['data'])}")
    
    print("\n6. 删除属性")
    response = requests.delete(f"{BASE_URL}/product/attributes/{attribute['id']}", headers=headers)
    print(f"   响应: code={response.json().get('code')}, msg={response.json().get('msg')}")
    
    print("\n✅ TC-PROD-BT-002 测试完成")

def test_product_variant(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-PROD-BT-003: 产品变体管理")
    print("=" * 60)
    
    print("\n1. 获取产品列表")
    response = requests.get(f"{BASE_URL}/product/list", headers=headers)
    products = response.json()['data']['items']
    t100_product = None
    for p in products:
        if '听音T100' in p['name']:
            t100_product = p
            break
    if not t100_product:
        print("   ⚠️ 未找到听音T100产品，跳过变体测试")
        return
    print(f"   找到产品: {t100_product['name']} (id={t100_product['id']})")
    
    print("\n2. 创建产品变体")
    data = {
        "product_id": t100_product['id'],
        "sku": "FG-T100-BK-M",
        "price": 299.00,
        "stock": 200,
        "attribute_values": []
    }
    response = requests.post(f"{BASE_URL}/product/variants", json=data, headers=headers)
    print(f"   响应: code={response.json().get('code')}, msg={response.json().get('msg')}")
    
    print("\n3. 创建更多变体")
    variants = [
        {"sku": "FG-T100-WH-M", "price": 299.00, "stock": 250, "attribute_values": []},
        {"sku": "FG-T100-BK-S", "price": 299.00, "stock": 100, "attribute_values": []}
    ]
    for v in variants:
        v['product_id'] = t100_product['id']
        response = requests.post(f"{BASE_URL}/product/variants", json=v, headers=headers)
        print(f"   创建 {v['sku']}: code={response.json().get('code')}")
    
    print("\n4. 查询变体列表")
    response = requests.get(f"{BASE_URL}/product/variants?product_id={t100_product['id']}", headers=headers)
    result = response.json()
    print(f"   变体数量: {result['data']['total']}")
    
    print("\n✅ TC-PROD-BT-003 测试完成")

def test_product_specification(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-PROD-BT-004: 产品规格关联")
    print("=" * 60)
    
    print("\n1. 获取产品列表")
    response = requests.get(f"{BASE_URL}/product/list", headers=headers)
    products = response.json()['data']['items']
    t100_product = None
    for p in products:
        if '听音T100' in p['name']:
            t100_product = p
            break
    if not t100_product:
        print("   ⚠️ 未找到听音T100产品")
        return
    print(f"   找到产品: {t100_product['name']}")
    
    print("\n2. 获取产品详情")
    response = requests.get(f"{BASE_URL}/product/item/{t100_product['id']}", headers=headers)
    result = response.json()
    print(f"   响应: code={result.get('code')}, 产品名称={result['data']['name']}")
    
    print("\n✅ TC-PROD-BT-004 测试完成")

def test_material_crud(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-BASE-BT-001: 蓝牙耳机物料CRUD")
    print("=" * 60)
    
    print("\n1. 创建物料")
    data = {
        "material_code": "TEST-FG-T100",
        "material_name": "测试听音T100蓝牙耳机",
        "material_type": "finished",
        "unit": "副",
        "specification": "BT5.3/ANC/IPX5"
    }
    response = requests.post(f"{BASE_URL}/mes/base-data/materials", json=data, headers=headers)
    print(f"   响应状态: {response.status_code}")
    try:
        result = response.json()
        print(f"   code={result.get('code')}, msg={result.get('msg')}")
    except:
        print(f"   响应内容: {response.text[:200]}")
    
    print("\n2. 搜索物料")
    response = requests.get(f"{BASE_URL}/mes/base-data/materials?material_name=T100", headers=headers)
    result = response.json()
    print(f"   搜索结果数量: {result['data']['total']}")
    
    print("\n✅ TC-BASE-BT-001 测试完成")

def test_mrp2_forecast(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-MRP2-BT-001: 蓝牙耳机销售预测")
    print("=" * 60)
    
    print("\n1. 查询销售预测列表")
    response = requests.get(f"{BASE_URL}/mrp2/forecast", headers=headers)
    print(f"   响应状态: {response.status_code}")
    try:
        result = response.json()
        print(f"   预测数量: {result['data']['total']}")
        if result['data']['total'] > 0:
            print(f"   预测列表: {[f['forecast_code'] for f in result['data']['items']]}")
    except Exception as e:
        print(f"   响应内容: {response.text[:200]}")
    
    print("\n✅ TC-MRP2-BT-001 测试完成")

def test_mrp2_mps(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-MRP2-BT-002: 蓝牙耳机MPS主生产计划")
    print("=" * 60)
    
    print("\n1. 查询MPS列表")
    response = requests.get(f"{BASE_URL}/mrp2/mps", headers=headers)
    result = response.json()
    print(f"   MPS数量: {result['data']['total']}")
    if result['data']['total'] > 0:
        print(f"   MPS列表: {[m['mps_code'] for m in result['data']['items']]}")
    
    print("\n✅ TC-MRP2-BT-002 测试完成")

def test_mrp2_mrp(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-MRP2-BT-003: 蓝牙耳机MRP物料需求计算")
    print("=" * 60)
    
    print("\n1. 查询MRP列表")
    response = requests.get(f"{BASE_URL}/mrp2/mrp", headers=headers)
    result = response.json()
    print(f"   MRP数量: {result['data']['total']}")
    
    print("\n✅ TC-MRP2-BT-003 测试完成")

def test_mrp2_crp(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-MRP2-BT-004: 蓝牙耳机CRP能力需求计算")
    print("=" * 60)
    
    print("\n1. 查询CRP列表")
    response = requests.get(f"{BASE_URL}/mrp2/crp", headers=headers)
    result = response.json()
    print(f"   CRP数量: {result['data']['total']}")
    
    print("\n✅ TC-MRP2-BT-004 测试完成")

def test_inventory_query(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-INV-BT-001: 蓝牙耳机库存查询")
    print("=" * 60)
    
    print("\n1. 查询库存列表")
    response = requests.get(f"{BASE_URL}/inventory/quants", headers=headers)
    print(f"   响应状态: {response.status_code}")
    try:
        result = response.json()
        print(f"   库存记录数量: {result['data']['total']}")
    except Exception as e:
        print(f"   响应内容: {response.text[:200]}")
    
    print("\n✅ TC-INV-BT-001 测试完成")

def test_purchase_supplier(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-PUR-BT-001: 蓝牙耳机原材料采购订单")
    print("=" * 60)
    
    print("\n1. 查询供应商列表")
    response = requests.get(f"{BASE_URL}/purchase/supplier", headers=headers)
    print(f"   响应状态: {response.status_code}")
    try:
        result = response.json()
        print(f"   供应商数量: {result['data']['total']}")
        if result['data']['total'] > 0:
            print(f"   供应商: {[s['supplier_name'] for s in result['data']['items']]}")
    except Exception as e:
        print(f"   响应内容: {response.text[:200]}")
    
    print("\n✅ TC-PUR-BT-001 测试完成")

def test_quality_inspection(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-QUALITY-BT-001: 功能测试记录")
    print("=" * 60)
    
    print("\n1. 查询检验标准列表")
    response = requests.get(f"{BASE_URL}/quality/standards", headers=headers)
    result = response.json()
    print(f"   检验标准数量: {result['data']['total']}")
    
    print("\n✅ TC-QUALITY-BT-001 测试完成")

def main():
    print("=" * 60)
    print("蓝牙耳机测试用例执行")
    print("=" * 60)
    
    try:
        token = login("admin", "admin123")
        print("✅ 登录成功")
        
        test_category_crud(token)
        test_attribute_management(token)
        test_product_variant(token)
        test_product_specification(token)
        test_material_crud(token)
        test_mrp2_forecast(token)
        test_mrp2_mps(token)
        test_mrp2_mrp(token)
        test_mrp2_crp(token)
        test_inventory_query(token)
        test_purchase_supplier(token)
        test_quality_inspection(token)
        
        print("\n" + "=" * 60)
        print("所有测试用例执行完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    main()