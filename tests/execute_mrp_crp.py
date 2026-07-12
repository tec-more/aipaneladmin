import requests
import json
import asyncio
from base.common.setting import TORTOISE_ORM
from tortoise import Tortoise

BASE_URL = "http://127.0.0.1:9998/api/v1"

def login():
    print("登录系统...")
    data = {"username": "admin", "password": "admin123"}
    response = requests.post(f"{BASE_URL}/auth/login", json=data)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 登录成功")
        return result['data']['access_token']
    else:
        print(f"❌ 登录失败: {response.text}")
        return None

async def create_initial_stock():
    print("\n创建初始库存...")
    await Tortoise.init(config=TORTOISE_ORM)
    
    from base.plugins.inventory.models.inventory_models import StockQuant
    
    supplier_loc = await StockQuant.filter(location_code="WH-SUPPLIER", product_code="FG-T100").first()
    if supplier_loc:
        print(f"库存已存在，更新数量")
        supplier_loc.quantity = 200
        supplier_loc.available_quantity = 200
        await supplier_loc.save()
    else:
        print(f"创建新库存记录")
        import time
        quant_code = f"QUANT{int(time.time())}FG-T100"
        await StockQuant.create(
            quant_code=quant_code,
            product_code="FG-T100",
            product_name="听音T100蓝牙耳机",
            location_id=1,
            location_code="WH-SUPPLIER",
            location_name="供应商",
            quantity=200,
            available_quantity=200,
            uom_code="unit",
            uom_name="件"
        )
    
    print("初始库存创建完成")
    await Tortoise.close_connections()

def execute_mrp(token):
    print("\n" + "=" * 60)
    print("执行MRP计算")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n1. 查询MRP列表检查是否已存在")
    response = requests.get(f"{BASE_URL}/mrp2/mrp", headers=headers)
    result = response.json()
    if result['data']['total'] > 0:
        mrp = result['data']['items'][0]
        print(f"MRP已存在: {mrp['mrp_code']}, 状态: {mrp.get('status', '未知')}")
        if mrp.get('status') == 'complete':
            return mrp['id']
        else:
            print(f"MRP状态不是complete，需要重新计算")
    
    print("\n2. 查询MPS获取ID")
    response = requests.get(f"{BASE_URL}/mrp2/mps", headers=headers)
    result = response.json()
    mps_list = result['data']['items']
    if not mps_list:
        print("❌ 未找到MPS数据")
        return None
    
    mps = None
    for mp in mps_list:
        if mp.get('status') == 'released':
            mps = mp
            break
    if not mps:
        mps = mps_list[0]
    
    print(f"找到MPS: {mps['mps_code']} (id={mps['id']}, status={mps.get('status')})")
    
    print("\n3. 执行MRP计算")
    data = {
        "mps_id": mps['id'],
        "include_safety_stock": True,
        "include_wip": True
    }
    response = requests.post(f"{BASE_URL}/mrp2/mrp/calculate", json=data, headers=headers)
    print(f"响应状态: {response.status_code}")
    try:
        result = response.json()
        print(f"code={result.get('code')}, msg={result.get('msg')}")
        if result.get('data'):
            mrp_data = result['data']
            print(f"MRP编号: {mrp_data.get('mrp_code')}")
            print(f"MRP状态: {mrp_data.get('status')}")
            return mrp_data.get('id')
    except:
        print(f"响应内容: {response.text[:200]}")
    return None

def execute_crp(token, mrp_id):
    print("\n" + "=" * 60)
    print("执行CRP计算")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n1. 查询CRP列表检查是否已存在")
    response = requests.get(f"{BASE_URL}/mrp2/crp", headers=headers)
    result = response.json()
    if result['data']['total'] > 0:
        crp = result['data']['items'][0]
        print(f"CRP已存在: {crp['crp_code']}")
        return
    
    print("\n2. 检查MRP状态")
    response = requests.get(f"{BASE_URL}/mrp2/mrp/{mrp_id}", headers=headers)
    result = response.json()
    if result.get('data'):
        mrp_status = result['data'].get('status')
        print(f"MRP状态: {mrp_status}")
        if mrp_status != 'complete':
            print("❌ MRP状态不是complete，无法执行CRP计算")
            return
    
    print("\n3. 执行CRP计算")
    data = {
        "mrp_id": mrp_id
    }
    response = requests.post(f"{BASE_URL}/mrp2/crp/calculate", json=data, headers=headers)
    print(f"响应状态: {response.status_code}")
    try:
        result = response.json()
        print(f"code={result.get('code')}, msg={result.get('msg')}")
        if result.get('data'):
            crp_data = result['data']
            print(f"CRP编号: {crp_data.get('crp_code')}")
            print(f"CRP状态: {crp_data.get('status')}")
    except:
        print(f"响应内容: {response.text[:200]}")

def execute_inventory_receipt(token):
    print("\n" + "=" * 60)
    print("执行库存入库")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n1. 查询调拨类型")
    response = requests.get(f"{BASE_URL}/inventory/picking-types", headers=headers)
    result = response.json()
    picking_types = result['data']['items']
    incoming_type = None
    for pt in picking_types:
        if pt.get('code') == 'incoming' or '入库' in pt.get('picking_type_name', ''):
            incoming_type = pt
            break
    if not incoming_type:
        print("❌ 未找到入库调拨类型")
        return None
    print(f"找到入库类型: {incoming_type['picking_type_name']} (id={incoming_type['id']}, code={incoming_type['code']})")
    
    print("\n2. 查询库位")
    response = requests.get(f"{BASE_URL}/inventory/locations", headers=headers)
    result = response.json()
    locations = result['data']['items']
    source_loc = None
    dest_loc = None
    for loc in locations:
        if '供应商' in loc.get('location_name', '') or loc.get('location_code') == 'WH-SUPPLIER':
            source_loc = loc
        elif '成品' in loc.get('location_name', '') or loc.get('location_code') == 'WH-FINISHED':
            dest_loc = loc
    if not source_loc and locations:
        source_loc = locations[0]
        print(f"未找到供应商库位，使用默认: {source_loc['location_name']}")
    if not dest_loc and locations:
        dest_loc = locations[-1]
        print(f"未找到成品库位，使用默认: {dest_loc['location_name']}")
    
    if not source_loc or not dest_loc:
        print("❌ 缺少必要的库位信息")
        return None
    
    print(f"源库位: {source_loc['location_name']} (id={source_loc['id']})")
    print(f"目标库位: {dest_loc['location_name']} (id={dest_loc['id']})")
    
    print("\n3. 查询物料获取ID")
    response = requests.get(f"{BASE_URL}/mes/base-data/materials?material_name=T100", headers=headers)
    result = response.json()
    materials = result['data']['items']
    fg_t100 = None
    for m in materials:
        if m['material_code'] == 'FG-T100':
            fg_t100 = m
            break
    if not fg_t100:
        print("❌ 未找到成品物料 FG-T100")
        return None
    print(f"找到物料: {fg_t100['material_name']} (id={fg_t100['id']}, code={fg_t100['material_code']})")
    
    print("\n4. 创建入库调拨单")
    data = {
        "picking_type_id": incoming_type['id'],
        "picking_type_code": incoming_type['picking_type_code'],
        "picking_type_name": incoming_type['picking_type_name'],
        "location_id": source_loc['id'],
        "location_code": source_loc['location_code'],
        "location_name": source_loc['location_name'],
        "location_dest_id": dest_loc['id'],
        "location_dest_code": dest_loc['location_code'],
        "location_dest_name": dest_loc['location_name'],
        "moves": [{
            "product_id": fg_t100['id'],
            "product_code": fg_t100['material_code'],
            "product_name": fg_t100['material_name'],
            "product_uom": fg_t100['unit'],
            "location_id": source_loc['id'],
            "location_code": source_loc['location_code'],
            "location_name": source_loc['location_name'],
            "location_dest_id": dest_loc['id'],
            "location_dest_code": dest_loc['location_code'],
            "location_dest_name": dest_loc['location_name'],
            "product_qty": 100,
            "product_uom_qty": 100,
            "state": "draft"
        }]
    }
    
    response = requests.post(f"{BASE_URL}/inventory/pickings", json=data, headers=headers)
    print(f"响应状态: {response.status_code}")
    try:
        result = response.json()
        print(f"code={result.get('code')}, msg={result.get('msg')}")
        if result.get('data'):
            picking = result['data']
            print(f"调拨单号: {picking.get('picking_code')}")
            return picking.get('id')
    except:
        print(f"响应内容: {response.text[:500]}")
    return None

def confirm_picking(token, picking_id):
    print("\n5. 确认入库")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(f"{BASE_URL}/inventory/pickings/{picking_id}/confirm", headers=headers)
    print(f"确认响应状态: {response.status_code}")
    try:
        result = response.json()
        print(f"code={result.get('code')}, msg={result.get('msg')}")
    except:
        print(f"确认响应内容: {response.text[:200]}")
    
    response = requests.post(f"{BASE_URL}/inventory/pickings/{picking_id}/do", headers=headers)
    print(f"执行响应状态: {response.status_code}")
    try:
        result = response.json()
        print(f"code={result.get('code')}, msg={result.get('msg')}")
    except:
        print(f"执行响应内容: {response.text[:200]}")

def verify_results(token):
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n1. 查询MRP列表")
    response = requests.get(f"{BASE_URL}/mrp2/mrp", headers=headers)
    result = response.json()
    print(f"MRP数量: {result['data']['total']}")
    if result['data']['total'] > 0:
        mrp = result['data']['items'][0]
        print(f"MRP编号: {mrp['mrp_code']}, 状态: {mrp.get('status')}")
    
    print("\n2. 查询CRP列表")
    response = requests.get(f"{BASE_URL}/mrp2/crp", headers=headers)
    result = response.json()
    print(f"CRP数量: {result['data']['total']}")
    if result['data']['total'] > 0:
        crp = result['data']['items'][0]
        print(f"CRP编号: {crp['crp_code']}, 状态: {crp.get('status')}")
    
    print("\n3. 查询库存")
    response = requests.get(f"{BASE_URL}/inventory/quants", headers=headers)
    result = response.json()
    print(f"库存记录数量: {result['data']['total']}")
    if result['data']['total'] > 0:
        for quant in result['data']['items'][:5]:
            print(f"  - {quant['product_code']} @ {quant['location_code']}: {quant['quantity']} {quant.get('uom_code', '')}")

if __name__ == "__main__":
    asyncio.run(create_initial_stock())
    
    token = login()
    if token:
        mrp_id = execute_mrp(token)
        if mrp_id:
            execute_crp(token, mrp_id)
        
        picking_id = execute_inventory_receipt(token)
        if picking_id:
            confirm_picking(token, picking_id)
        
        verify_results(token)
    
    print("\n" + "=" * 60)
    print("执行完成")
    print("=" * 60)
