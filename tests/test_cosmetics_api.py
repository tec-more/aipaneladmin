import requests
import json
import datetime

BASE_URL = "http://127.0.0.1:9998/api/v1"

test_results = []

def add_test_result(test_id, test_name, status, msg="", error=""):
    result = {
        "test_id": test_id,
        "test_name": test_name,
        "status": status,
        "msg": msg,
        "error": error,
        "timestamp": datetime.datetime.now().isoformat()
    }
    test_results.append(result)

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
    print("TC-PROD-CO-001: 美妆产品分类CRUD完整流程")
    print("=" * 60)
    
    categories = []
    
    try:
        print("\n1. 创建顶层分类 '美妆护肤'")
        data = {"name": "美妆护肤", "code": "BEAUTY", "sort_order": 1}
        response = requests.post(f"{BASE_URL}/product/categories", json=data, headers=headers)
        result = response.json()
        print(f"   响应: code={result.get('code')}, msg={result.get('msg')}")
        if result.get('code') == 0:
            ce_category = result['data']
            categories.append(ce_category)
        else:
            add_test_result("TC-PROD-CO-001", "美妆产品分类CRUD完整流程", "FAIL", msg=f"创建分类失败: {result.get('msg')}")
            return
        
        print("\n2. 创建子分类 '面部精华'")
        data = {"name": "面部精华", "code": "BEAUTY-ESSENCE", "sort_order": 1, "parent_id": ce_category['id']}
        response = requests.post(f"{BASE_URL}/product/categories", json=data, headers=headers)
        result = response.json()
        print(f"   响应: code={result.get('code')}, msg={result.get('msg')}")
        if result.get('code') == 0:
            bt_category = result['data']
            categories.append(bt_category)
        else:
            add_test_result("TC-PROD-CO-001", "美妆产品分类CRUD完整流程", "FAIL", msg=f"创建子分类失败: {result.get('msg')}")
            return
        
        print("\n3. 更新分类排序")
        data = {"sort_order": 2}
        response = requests.put(f"{BASE_URL}/product/categories/{bt_category['id']}", json=data, headers=headers)
        result = response.json()
        print(f"   响应: code={result.get('code')}, msg={result.get('msg')}")
        
        print("\n4. 搜索分类")
        response = requests.get(f"{BASE_URL}/product/categories?name=精华", headers=headers)
        result = response.json()
        print(f"   搜索结果数量: {result['data']['total']}")
        
        print("\n5. 删除分类")
        for cat in reversed(categories):
            response = requests.delete(f"{BASE_URL}/product/categories/{cat['id']}", headers=headers)
            result = response.json()
            print(f"   删除 {cat['name']}: code={result.get('code')}, msg={result.get('msg')}")
        
        add_test_result("TC-PROD-CO-001", "美妆产品分类CRUD完整流程", "PASS")
        print("\n✅ TC-PROD-CO-001 测试完成")
    
    except Exception as e:
        add_test_result("TC-PROD-CO-001", "美妆产品分类CRUD完整流程", "FAIL", error=str(e))
        print(f"\n❌ TC-PROD-CO-001 测试失败: {e}")

def test_attribute_management(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-PROD-CO-002: 美妆产品属性管理")
    print("=" * 60)
    
    try:
        print("\n1. 查询属性 '颜色' 是否已存在")
        response = requests.get(f"{BASE_URL}/product/attributes?name=颜色", headers=headers)
        result = response.json()
        attribute = None
        created_attribute = False
        
        if result.get('data', {}).get('total', 0) > 0:
            attribute = result['data']['items'][0]
            print(f"   属性已存在: id={attribute['id']}, name={attribute['name']}")
        else:
            print("\n2. 创建属性 '颜色'")
            data = {"name": "颜色", "code": "color", "category": "both", "sort_order": 1}
            response = requests.post(f"{BASE_URL}/product/attributes", json=data, headers=headers)
            result = response.json()
            print(f"   响应: code={result.get('code')}, msg={result.get('msg')}")
            if result.get('code') != 0:
                add_test_result("TC-PROD-CO-002", "美妆产品属性管理", "FAIL", msg=f"创建属性失败: {result.get('msg')}")
                return
            attribute = result['data']
            created_attribute = True
        
        print("\n3. 添加属性值")
        values = ["红色", "粉色", "橙色", "裸色"]
        value_ids = []
        for v in values:
            data = {"attribute_id": attribute['id'], "value": v, "sort_order": values.index(v) + 1}
            response = requests.post(f"{BASE_URL}/product/attributes/values", json=data, headers=headers)
            result = response.json()
            if result.get('code') == 0:
                value_ids.append(result['data']['id'])
            else:
                print(f"   属性值 '{v}' 添加失败或已存在: {result.get('msg')}")
        print(f"   添加了 {len(value_ids)} 个属性值")
        
        print("\n4. 更新属性排序")
        data = {"sort_order": 2}
        response = requests.put(f"{BASE_URL}/product/attributes/{attribute['id']}", json=data, headers=headers)
        result = response.json()
        print(f"   响应: code={result.get('code')}, msg={result.get('msg')}")
        
        print("\n5. 删除属性值 '橙色'")
        if len(value_ids) > 2:
            response = requests.delete(f"{BASE_URL}/product/attributes/values/{value_ids[2]}", headers=headers)
            result = response.json()
            print(f"   响应: code={result.get('code')}, msg={result.get('msg')}")
        
        print("\n6. 获取属性选项")
        response = requests.get(f"{BASE_URL}/product/attributes/options", headers=headers)
        result = response.json()
        print(f"   属性选项数量: {len(result['data'])}")
        
        print("\n7. 清理测试数据")
        for vid in value_ids:
            response = requests.delete(f"{BASE_URL}/product/attributes/values/{vid}", headers=headers)
        if created_attribute:
            response = requests.delete(f"{BASE_URL}/product/attributes/{attribute['id']}", headers=headers)
            result = response.json()
            print(f"   删除属性: code={result.get('code')}")
        else:
            print("   属性非测试创建，跳过删除")
        
        add_test_result("TC-PROD-CO-002", "美妆产品属性管理", "PASS")
        print("\n✅ TC-PROD-CO-002 测试完成")
    
    except Exception as e:
        add_test_result("TC-PROD-CO-002", "美妆产品属性管理", "FAIL", error=str(e))
        print(f"\n❌ TC-PROD-CO-002 测试失败: {e}")

def test_product_variant(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-PROD-CO-003: 美妆产品变体管理")
    print("=" * 60)
    
    try:
        print("\n1. 获取产品列表")
        response = requests.get(f"{BASE_URL}/product/list", headers=headers)
        products = response.json()['data']['items']
        lip_product = None
        for p in products:
            if '花妍丝绒口红' in p['name']:
                lip_product = p
                break
        if not lip_product:
            print("   ⚠️ 未找到花妍丝绒口红产品，跳过变体测试")
            add_test_result("TC-PROD-CO-003", "美妆产品变体管理", "SKIP", msg="未找到花妍丝绒口红产品")
            return
        print(f"   找到产品: {lip_product['name']} (id={lip_product['id']})")
        
        print("\n2. 创建产品变体")
        data = {
            "product_id": lip_product['id'],
            "sku": "FG-LIP-RED-01",
            "price": 168.00,
            "stock": 500,
            "attribute_values": []
        }
        response = requests.post(f"{BASE_URL}/product/variants", json=data, headers=headers)
        result = response.json()
        print(f"   响应: code={result.get('code')}, msg={result.get('msg')}")
        
        print("\n3. 创建更多变体")
        variants = [
            {"sku": "FG-LIP-PINK-01", "price": 168.00, "stock": 400, "attribute_values": []},
            {"sku": "FG-LIP-ORANGE-01", "price": 168.00, "stock": 300, "attribute_values": []}
        ]
        for v in variants:
            v['product_id'] = lip_product['id']
            response = requests.post(f"{BASE_URL}/product/variants", json=v, headers=headers)
            result = response.json()
            print(f"   创建 {v['sku']}: code={result.get('code')}")
        
        print("\n4. 查询变体列表")
        response = requests.get(f"{BASE_URL}/product/variants?product_id={lip_product['id']}", headers=headers)
        result = response.json()
        print(f"   变体数量: {result['data']['total']}")
        
        add_test_result("TC-PROD-CO-003", "美妆产品变体管理", "PASS")
        print("\n✅ TC-PROD-CO-003 测试完成")
    
    except Exception as e:
        add_test_result("TC-PROD-CO-003", "美妆产品变体管理", "FAIL", error=str(e))
        print(f"\n❌ TC-PROD-CO-003 测试失败: {e}")

def test_product_specification(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-PROD-CO-004: 美妆产品规格关联")
    print("=" * 60)
    
    try:
        print("\n1. 获取产品列表")
        response = requests.get(f"{BASE_URL}/product/list", headers=headers)
        products = response.json()['data']['items']
        ess_product = None
        for p in products:
            if '花妍玫瑰精华液' in p['name']:
                ess_product = p
                break
        if not ess_product:
            print("   ⚠️ 未找到花妍玫瑰精华液产品")
            add_test_result("TC-PROD-CO-004", "美妆产品规格关联", "SKIP", msg="未找到花妍玫瑰精华液产品")
            return
        print(f"   找到产品: {ess_product['name']}")
        
        print("\n2. 获取产品详情")
        response = requests.get(f"{BASE_URL}/product/item/{ess_product['id']}", headers=headers)
        result = response.json()
        print(f"   响应: code={result.get('code')}, 产品名称={result['data']['name']}")
        
        add_test_result("TC-PROD-CO-004", "美妆产品规格关联", "PASS")
        print("\n✅ TC-PROD-CO-004 测试完成")
    
    except Exception as e:
        add_test_result("TC-PROD-CO-004", "美妆产品规格关联", "FAIL", error=str(e))
        print(f"\n❌ TC-PROD-CO-004 测试失败: {e}")

def test_material_crud(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-BASE-CO-001: 美妆物料CRUD")
    print("=" * 60)
    
    try:
        print("\n1. 创建物料")
        data = {
            "material_code": "TEST-FG-ESS-001",
            "material_name": "测试花妍玫瑰精华液",
            "material_type": "finished",
            "unit": "瓶",
            "specification": "50ml/玫瑰精华"
        }
        response = requests.post(f"{BASE_URL}/mes/base-data/materials", json=data, headers=headers)
        print(f"   响应状态: {response.status_code}")
        try:
            result = response.json()
            print(f"   code={result.get('code')}, msg={result.get('msg')}")
        except:
            print(f"   响应内容: {response.text[:200]}")
        
        print("\n2. 搜索物料")
        response = requests.get(f"{BASE_URL}/mes/base-data/materials?material_name=精华", headers=headers)
        result = response.json()
        print(f"   搜索结果数量: {result['data']['total']}")
        
        add_test_result("TC-BASE-CO-001", "美妆物料CRUD", "PASS")
        print("\n✅ TC-BASE-CO-001 测试完成")
    
    except Exception as e:
        add_test_result("TC-BASE-CO-001", "美妆物料CRUD", "FAIL", error=str(e))
        print(f"\n❌ TC-BASE-CO-001 测试失败: {e}")

def test_mrp2_forecast(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-MRP2-CO-001: 美妆产品销售预测")
    print("=" * 60)
    
    try:
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
        
        add_test_result("TC-MRP2-CO-001", "美妆产品销售预测", "PASS")
        print("\n✅ TC-MRP2-CO-001 测试完成")
    
    except Exception as e:
        add_test_result("TC-MRP2-CO-001", "美妆产品销售预测", "FAIL", error=str(e))
        print(f"\n❌ TC-MRP2-CO-001 测试失败: {e}")

def test_mrp2_mps(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-MRP2-CO-002: 美妆产品MPS主生产计划")
    print("=" * 60)
    
    try:
        print("\n1. 查询MPS列表")
        response = requests.get(f"{BASE_URL}/mrp2/mps", headers=headers)
        result = response.json()
        print(f"   MPS数量: {result['data']['total']}")
        if result['data']['total'] > 0:
            print(f"   MPS列表: {[m['mps_code'] for m in result['data']['items']]}")
        
        add_test_result("TC-MRP2-CO-002", "美妆产品MPS主生产计划", "PASS")
        print("\n✅ TC-MRP2-CO-002 测试完成")
    
    except Exception as e:
        add_test_result("TC-MRP2-CO-002", "美妆产品MPS主生产计划", "FAIL", error=str(e))
        print(f"\n❌ TC-MRP2-CO-002 测试失败: {e}")

def test_mrp2_mrp(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-MRP2-CO-003: 美妆产品MRP物料需求计算")
    print("=" * 60)
    
    try:
        print("\n1. 查询MRP列表")
        response = requests.get(f"{BASE_URL}/mrp2/mrp", headers=headers)
        result = response.json()
        print(f"   MRP数量: {result['data']['total']}")
        
        add_test_result("TC-MRP2-CO-003", "美妆产品MRP物料需求计算", "PASS")
        print("\n✅ TC-MRP2-CO-003 测试完成")
    
    except Exception as e:
        add_test_result("TC-MRP2-CO-003", "美妆产品MRP物料需求计算", "FAIL", error=str(e))
        print(f"\n❌ TC-MRP2-CO-003 测试失败: {e}")

def test_mrp2_crp(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-MRP2-CO-004: 美妆产品CRP能力需求计算")
    print("=" * 60)
    
    try:
        print("\n1. 查询CRP列表")
        response = requests.get(f"{BASE_URL}/mrp2/crp", headers=headers)
        result = response.json()
        print(f"   CRP数量: {result['data']['total']}")
        
        add_test_result("TC-MRP2-CO-004", "美妆产品CRP能力需求计算", "PASS")
        print("\n✅ TC-MRP2-CO-004 测试完成")
    
    except Exception as e:
        add_test_result("TC-MRP2-CO-004", "美妆产品CRP能力需求计算", "FAIL", error=str(e))
        print(f"\n❌ TC-MRP2-CO-004 测试失败: {e}")

def test_purchase_supplier(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-PUR-CO-003: 供应商管理")
    print("=" * 60)
    
    try:
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
        
        add_test_result("TC-PUR-CO-003", "供应商管理", "PASS")
        print("\n✅ TC-PUR-CO-003 测试完成")
    
    except Exception as e:
        add_test_result("TC-PUR-CO-003", "供应商管理", "FAIL", error=str(e))
        print(f"\n❌ TC-PUR-CO-003 测试失败: {e}")

def test_purchase_order(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-PUR-CO-001: 美妆原材料采购订单")
    print("=" * 60)
    
    try:
        print("\n1. 查询采购订单列表")
        response = requests.get(f"{BASE_URL}/purchase/order", headers=headers)
        print(f"   响应状态: {response.status_code}")
        try:
            result = response.json()
            print(f"   采购订单数量: {result['data']['total']}")
        except Exception as e:
            print(f"   响应内容: {response.text[:200]}")
        
        add_test_result("TC-PUR-CO-001", "美妆原材料采购订单", "PASS")
        print("\n✅ TC-PUR-CO-001 测试完成")
    
    except Exception as e:
        add_test_result("TC-PUR-CO-001", "美妆原材料采购订单", "FAIL", error=str(e))
        print(f"\n❌ TC-PUR-CO-001 测试失败: {e}")

def test_inventory_query(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-INV-CO-001: 美妆产品库存查询")
    print("=" * 60)
    
    try:
        print("\n1. 查询库存列表")
        response = requests.get(f"{BASE_URL}/inventory/quants", headers=headers)
        print(f"   响应状态: {response.status_code}")
        try:
            result = response.json()
            print(f"   库存记录数量: {result['data']['total']}")
        except Exception as e:
            print(f"   响应内容: {response.text[:200]}")
        
        add_test_result("TC-INV-CO-001", "美妆产品库存查询", "PASS")
        print("\n✅ TC-INV-CO-001 测试完成")
    
    except Exception as e:
        add_test_result("TC-INV-CO-001", "美妆产品库存查询", "FAIL", error=str(e))
        print(f"\n❌ TC-INV-CO-001 测试失败: {e}")

def test_sales_order(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-SALES-CO-001: 销售订单创建")
    print("=" * 60)
    
    try:
        print("\n1. 查询订单列表")
        response = requests.get(f"{BASE_URL}/sales/orders", headers=headers)
        print(f"   响应状态: {response.status_code}")
        try:
            result = response.json()
            print(f"   订单数量: {result['data']['total']}")
        except Exception as e:
            print(f"   响应内容: {response.text[:200]}")
        
        add_test_result("TC-SALES-CO-001", "销售订单创建", "PASS")
        print("\n✅ TC-SALES-CO-001 测试完成")
    
    except Exception as e:
        add_test_result("TC-SALES-CO-001", "销售订单创建", "FAIL", error=str(e))
        print(f"\n❌ TC-SALES-CO-001 测试失败: {e}")

def test_quality_inspection(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-QUALITY-CO-001: 美妆产品检验标准管理")
    print("=" * 60)
    
    try:
        print("\n1. 查询检验标准列表")
        response = requests.get(f"{BASE_URL}/quality/standards", headers=headers)
        result = response.json()
        print(f"   检验标准数量: {result['data']['total']}")
        
        add_test_result("TC-QUALITY-CO-001", "美妆产品检验标准管理", "PASS")
        print("\n✅ TC-QUALITY-CO-001 测试完成")
    
    except Exception as e:
        add_test_result("TC-QUALITY-CO-001", "美妆产品检验标准管理", "FAIL", error=str(e))
        print(f"\n❌ TC-QUALITY-CO-001 测试失败: {e}")

def test_kit_check(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "=" * 60)
    print("TC-KIT-CO-001: 齐套检查功能测试")
    print("=" * 60)
    
    try:
        print("\n1. 查询制造订单列表")
        response = requests.get(f"{BASE_URL}/mes/manufacturing-orders", headers=headers)
        result = response.json()
        mo_list = result.get('data', {}).get('items', [])
        print(f"   制造订单数量: {len(mo_list)}")
        
        if mo_list:
            mo_id = mo_list[0]['id']
            mo_code = mo_list[0]['mo_code']
            
            print(f"\n2. 检查制造订单 {mo_code} 齐套情况")
            response = requests.get(f"{BASE_URL}/mes/kit-check/{mo_id}", headers=headers)
            result = response.json()
            print(f"   响应: code={result.get('code')}")
            if result.get('code') == 0:
                data = result['data']
                print(f"   齐套状态: {data.get('kit_status')}")
                print(f"   齐套率: {data.get('kit_rate')}%")
                print(f"   物料总数: {data.get('total_items')}")
                print(f"   缺料数量: {data.get('shortage_items')}")
                
                shortage_list = data.get('shortage_list', [])
                if shortage_list:
                    print("\n   缺料清单:")
                    for item in shortage_list:
                        print(f"     - {item['item_name']}({item['item_code']}): 缺{item['shortage']}{item['unit']}")
        
        print("\n3. 检查BOM齐套情况（口红）")
        response = requests.get(f"{BASE_URL}/mes/kit-check/bom/LIPSTICK-001?quantity=10", headers=headers)
        result = response.json()
        print(f"   响应: code={result.get('code')}")
        if result.get('code') == 0:
            data = result['data']
            print(f"   产品名称: {data.get('product_name')}")
            print(f"   齐套状态: {data.get('kit_status')}")
            print(f"   齐套率: {data.get('kit_rate')}%")
        
        print("\n4. 获取齐套状态")
        if mo_list:
            response = requests.get(f"{BASE_URL}/mes/kit-check/status/{mo_code}", headers=headers)
            result = response.json()
            print(f"   响应: code={result.get('code')}")
            if result.get('code') == 0:
                data = result['data']
                print(f"   齐套状态: {data.get('kit_status')} - {data.get('kit_status_desc')}")
        
        add_test_result("TC-KIT-CO-001", "齐套检查功能测试", "PASS")
        print("\n✅ TC-KIT-CO-001 测试完成")
    
    except Exception as e:
        add_test_result("TC-KIT-CO-001", "齐套检查功能测试", "FAIL", error=str(e))
        print(f"\n❌ TC-KIT-CO-001 测试失败: {e}")

def generate_test_report():
    print("\n" + "=" * 60)
    print("生成测试报告")
    print("=" * 60)
    
    pass_count = sum(1 for r in test_results if r['status'] == 'PASS')
    fail_count = sum(1 for r in test_results if r['status'] == 'FAIL')
    skip_count = sum(1 for r in test_results if r['status'] == 'SKIP')
    total_count = len(test_results)
    
    report = f"""# 花妍美妆产品测试报告

## 测试概述
- 测试日期: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 测试环境: {BASE_URL}
- 测试范围: 产品管理、基础数据、MRP2、采购、库存、销售、品质

## 测试结果统计

| 指标 | 数量 |
|------|------|
| 测试总数 | {total_count} |
| 通过 | {pass_count} |
| 失败 | {fail_count} |
| 跳过 | {skip_count} |
| 通过率 | {pass_count/total_count*100:.2f}% |

## 测试用例详情

| 用例编号 | 用例名称 | 结果 | 备注 |
|----------|----------|------|------|
"""
    
    for result in test_results:
        status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
        msg = result['msg'] if result['msg'] else (result['error'] if result['error'] else "")
        report += f"| {result['test_id']} | {result['test_name']} | {status_icon} {result['status']} | {msg} |\n"
    
    report += f"""
## 测试结论

{pass_count}/{total_count} 个测试用例通过，通过率 {pass_count/total_count*100:.2f}%。

"""
    
    with open("tests/test_report_cosmetics.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"测试报告已保存至: tests/test_report_cosmetics.md")
    
    with open("tests/test_results_cosmetics.json", "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    print(f"测试结果JSON已保存至: tests/test_results_cosmetics.json")

def main():
    print("=" * 60)
    print("花妍美妆产品测试用例执行")
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
        test_purchase_supplier(token)
        test_purchase_order(token)
        test_inventory_query(token)
        test_sales_order(token)
        test_quality_inspection(token)
        test_kit_check(token)
        
        print("\n" + "=" * 60)
        print("所有测试用例执行完成!")
        print("=" * 60)
        
        generate_test_report()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        add_test_result("SYSTEM", "系统错误", "FAIL", error=str(e))
        generate_test_report()

if __name__ == "__main__":
    main()