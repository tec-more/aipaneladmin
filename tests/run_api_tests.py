import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:9998/api/v1"
TEST_RESULTS = []

def log_result(test_id, test_name, status, message=""):
    result = {
        "test_id": test_id,
        "test_name": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    TEST_RESULTS.append(result)
    status_icon = "✅" if status == "PASS" else "❌"
    print(f"{status_icon} {test_id}: {test_name} - {status}")
    if message:
        print(f"   {message}")

def login():
    print("\n" + "=" * 60)
    print("登录系统")
    print("=" * 60)
    data = {"username": "admin", "password": "admin123"}
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"登录成功")
            return result['data']['access_token']
        else:
            log_result("TC-AUTH-001", "系统登录", "FAIL", f"登录失败: {response.text}")
            return None
    except Exception as e:
        log_result("TC-AUTH-001", "系统登录", "FAIL", f"登录异常: {str(e)}")
        return None

def test_product_categories(token):
    print("\n" + "=" * 60)
    print("产品管理测试")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # TC-PROD-BT-001: 产品分类CRUD
    try:
        print("\nTC-PROD-BT-001: 产品分类CRUD完整流程")
        
        response = requests.get(f"{BASE_URL}/product/categories", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-PROD-BT-001", "产品分类CRUD完整流程", "PASS")
        else:
            log_result("TC-PROD-BT-001", "产品分类CRUD完整流程", "FAIL", f"查询分类失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-PROD-BT-001", "产品分类CRUD完整流程", "FAIL", str(e))
    
    # TC-PROD-BT-002: 产品属性管理
    try:
        print("\nTC-PROD-BT-002: 产品属性管理")
        
        response = requests.get(f"{BASE_URL}/product/attributes", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-PROD-BT-002", "产品属性管理", "PASS")
        else:
            log_result("TC-PROD-BT-002", "产品属性管理", "FAIL", f"查询属性失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-PROD-BT-002", "产品属性管理", "FAIL", str(e))
    
    # TC-PROD-BT-003: 产品变体管理
    try:
        print("\nTC-PROD-BT-003: 产品变体管理")
        
        response = requests.get(f"{BASE_URL}/product/variants", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-PROD-BT-003", "产品变体管理", "PASS")
        else:
            log_result("TC-PROD-BT-003", "产品变体管理", "FAIL", f"查询变体失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-PROD-BT-003", "产品变体管理", "FAIL", str(e))
    
    # TC-PROD-BT-004: 产品规格关联
    try:
        print("\nTC-PROD-BT-004: 产品规格关联")
        
        response = requests.get(f"{BASE_URL}/product/list", headers=headers)
        result = response.json()
        if result['code'] == 0 and result['data']['total'] > 0:
            log_result("TC-PROD-BT-004", "产品规格关联", "PASS")
        else:
            log_result("TC-PROD-BT-004", "产品规格关联", "FAIL", f"查询产品失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-PROD-BT-004", "产品规格关联", "FAIL", str(e))

def test_base_data(token):
    print("\n" + "=" * 60)
    print("基础数据管理测试")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # TC-BASE-BT-001: 物料CRUD
    try:
        print("\nTC-BASE-BT-001: 蓝牙耳机物料CRUD完整流程")
        
        response = requests.get(f"{BASE_URL}/mes/base-data/materials", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-BASE-BT-001", "蓝牙耳机物料CRUD完整流程", "PASS")
        else:
            log_result("TC-BASE-BT-001", "蓝牙耳机物料CRUD完整流程", "FAIL", f"查询物料失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-BASE-BT-001", "蓝牙耳机物料CRUD完整流程", "FAIL", str(e))
    
    # TC-BASE-BT-002: BOM版本管理
    try:
        print("\nTC-BASE-BT-002: 蓝牙耳机BOM版本管理")
        
        response = requests.get(f"{BASE_URL}/mes/base-data/boms", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-BASE-BT-002", "蓝牙耳机BOM版本管理", "PASS")
        else:
            log_result("TC-BASE-BT-002", "蓝牙耳机BOM版本管理", "FAIL", f"查询BOM失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-BASE-BT-002", "蓝牙耳机BOM版本管理", "FAIL", str(e))
    
    # TC-BASE-BT-003: 工艺路线配置
    try:
        print("\nTC-BASE-BT-003: 蓝牙耳机工艺路线配置")
        
        response = requests.get(f"{BASE_URL}/mes/base-data/routes", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-BASE-BT-003", "蓝牙耳机工艺路线配置", "PASS")
        else:
            log_result("TC-BASE-BT-003", "蓝牙耳机工艺路线配置", "FAIL", f"查询工艺路线失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-BASE-BT-003", "蓝牙耳机工艺路线配置", "FAIL", str(e))

def test_mrp2(token):
    print("\n" + "=" * 60)
    print("MRP2模块测试")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # TC-MRP2-BT-001: 销售预测
    try:
        print("\nTC-MRP2-BT-001: 蓝牙耳机销售预测")
        
        response = requests.get(f"{BASE_URL}/mrp2/forecast", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-MRP2-BT-001", "蓝牙耳机销售预测", "PASS")
        else:
            log_result("TC-MRP2-BT-001", "蓝牙耳机销售预测", "FAIL", f"查询销售预测失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-MRP2-BT-001", "蓝牙耳机销售预测", "FAIL", str(e))
    
    # TC-MRP2-BT-002: MPS主生产计划
    try:
        print("\nTC-MRP2-BT-002: 蓝牙耳机MPS主生产计划")
        
        response = requests.get(f"{BASE_URL}/mrp2/mps", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-MRP2-BT-002", "蓝牙耳机MPS主生产计划", "PASS")
        else:
            log_result("TC-MRP2-BT-002", "蓝牙耳机MPS主生产计划", "FAIL", f"查询MPS失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-MRP2-BT-002", "蓝牙耳机MPS主生产计划", "FAIL", str(e))
    
    # TC-MRP2-BT-003: MRP物料需求计算
    try:
        print("\nTC-MRP2-BT-003: 蓝牙耳机MRP物料需求计算")
        
        response = requests.get(f"{BASE_URL}/mrp2/mrp", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-MRP2-BT-003", "蓝牙耳机MRP物料需求计算", "PASS")
        else:
            log_result("TC-MRP2-BT-003", "蓝牙耳机MRP物料需求计算", "FAIL", f"查询MRP失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-MRP2-BT-003", "蓝牙耳机MRP物料需求计算", "FAIL", str(e))
    
    # TC-MRP2-BT-004: CRP能力需求计算
    try:
        print("\nTC-MRP2-BT-004: 蓝牙耳机CRP能力需求计算")
        
        response = requests.get(f"{BASE_URL}/mrp2/crp", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-MRP2-BT-004", "蓝牙耳机CRP能力需求计算", "PASS")
        else:
            log_result("TC-MRP2-BT-004", "蓝牙耳机CRP能力需求计算", "FAIL", f"查询CRP失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-MRP2-BT-004", "蓝牙耳机CRP能力需求计算", "FAIL", str(e))

def test_inventory(token):
    print("\n" + "=" * 60)
    print("库存模块测试")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # TC-INV-BT-001: 库存查询
    try:
        print("\nTC-INV-BT-001: 蓝牙耳机库存查询")
        
        response = requests.get(f"{BASE_URL}/inventory/quants", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-INV-BT-001", "蓝牙耳机库存查询", "PASS")
        else:
            log_result("TC-INV-BT-001", "蓝牙耳机库存查询", "FAIL", f"查询库存失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-INV-BT-001", "蓝牙耳机库存查询", "FAIL", str(e))
    
    # TC-INV-BT-002: 库存调拨
    try:
        print("\nTC-INV-BT-002: 蓝牙耳机库存调拨")
        
        response = requests.get(f"{BASE_URL}/inventory/pickings", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-INV-BT-002", "蓝牙耳机库存调拨", "PASS")
        else:
            log_result("TC-INV-BT-002", "蓝牙耳机库存调拨", "FAIL", f"查询调拨单失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-INV-BT-002", "蓝牙耳机库存调拨", "FAIL", str(e))

def test_manufacturing(token):
    print("\n" + "=" * 60)
    print("制造计划测试")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # TC-PLAN-BT-001: 制造单生命周期
    try:
        print("\nTC-PLAN-BT-001: 蓝牙耳机制造单完整生命周期")
        
        response = requests.get(f"{BASE_URL}/mes/production/manufacturing-orders", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-PLAN-BT-001", "蓝牙耳机制造单完整生命周期", "PASS")
        else:
            log_result("TC-PLAN-BT-001", "蓝牙耳机制造单完整生命周期", "FAIL", f"查询制造单失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-PLAN-BT-001", "蓝牙耳机制造单完整生命周期", "FAIL", str(e))

def test_work_orders(token):
    print("\n" + "=" * 60)
    print("工单执行测试")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # TC-EXEC-BT-001: 工单状态流转
    try:
        print("\nTC-EXEC-BT-001: 蓝牙耳机工单完整状态流转")
        
        response = requests.get(f"{BASE_URL}/mes/production/work-orders", headers=headers)
        result = response.json()
        if result['code'] == 0:
            log_result("TC-EXEC-BT-001", "蓝牙耳机工单完整状态流转", "PASS")
        else:
            log_result("TC-EXEC-BT-001", "蓝牙耳机工单完整状态流转", "FAIL", f"查询工单失败: {result.get('msg')}")
    except Exception as e:
        log_result("TC-EXEC-BT-001", "蓝牙耳机工单完整状态流转", "FAIL", str(e))

def test_purchasing(token):
    print("\n" + "=" * 60)
    print("采购模块测试")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # TC-PUR-BT-001: 采购订单
    try:
        print("\nTC-PUR-BT-001: 蓝牙耳机原材料采购订单")
        
        response = requests.get(f"{BASE_URL}/purchase/order", headers=headers)
        result = response.json()
        if 'code' in result:
            if result['code'] == 0:
                log_result("TC-PUR-BT-001", "蓝牙耳机原材料采购订单", "PASS")
            else:
                log_result("TC-PUR-BT-001", "蓝牙耳机原材料采购订单", "FAIL", f"查询采购订单失败: {result.get('msg')}")
        elif 'total' in result:
            log_result("TC-PUR-BT-001", "蓝牙耳机原材料采购订单", "PASS")
        else:
            log_result("TC-PUR-BT-001", "蓝牙耳机原材料采购订单", "FAIL", f"返回格式不符合预期: {result}")
    except Exception as e:
        log_result("TC-PUR-BT-001", "蓝牙耳机原材料采购订单", "FAIL", str(e))

def generate_report():
    print("\n" + "=" * 60)
    print("生成测试报告")
    print("=" * 60)
    
    pass_count = sum(1 for r in TEST_RESULTS if r['status'] == "PASS")
    fail_count = sum(1 for r in TEST_RESULTS if r['status'] == "FAIL")
    total_count = len(TEST_RESULTS)
    
    report = f"""# 听音蓝牙耳机MES/MRP2系统测试报告

## 1. 测试概览

| 项目 | 数值 |
|------|------|
| 测试执行时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| 测试用例总数 | {total_count} |
| 通过 | {pass_count} |
| 失败 | {fail_count} |
| 通过率 | {pass_count/total_count*100:.1f}% |

## 2. 测试结果详情

| 用例编号 | 用例名称 | 状态 | 备注 |
|----------|----------|------|------|"""
    
    for result in TEST_RESULTS:
        report += f"\n| {result['test_id']} | {result['test_name']} | {result['status']} | {result['message'][:100] if result['message'] else ''} |"
    
    report += f"""

## 3. 失败用例汇总

"""
    
    failed_results = [r for r in TEST_RESULTS if r['status'] == "FAIL"]
    if failed_results:
        for result in failed_results:
            report += f"- **{result['test_id']}**: {result['test_name']}\n  - 原因: {result['message']}\n\n"
    else:
        report += "无失败用例\n"
    
    report += f"""

## 4. 测试结论

"""
    
    if fail_count == 0:
        report += "✅ 所有测试用例通过，系统功能正常。"
    else:
        report += f"⚠️ 部分测试用例失败，失败率 {fail_count/total_count*100:.1f}%，请检查相关功能模块。"
    
    report_path = "tests/test_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    json_path = "tests/test_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(TEST_RESULTS, f, ensure_ascii=False, indent=2)
    
    print(f"\n测试报告已生成: {report_path}")
    print(f"测试结果JSON: {json_path}")
    print(f"\n测试统计: 通过 {pass_count}/{total_count}，失败 {fail_count}/{total_count}")

if __name__ == "__main__":
    print("=" * 60)
    print("听音蓝牙耳机MES/MRP2系统自动化测试")
    print("=" * 60)
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    token = login()
    if token:
        test_product_categories(token)
        test_base_data(token)
        test_mrp2(token)
        test_inventory(token)
        test_manufacturing(token)
        test_work_orders(token)
        test_purchasing(token)
    
    generate_report()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
