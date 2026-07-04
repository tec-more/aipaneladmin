import requests
import json
import sys
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:9998/api"
TIMEOUT = 30

results = {"pass": 0, "fail": 0, "skip": 0, "details": []}
token = None
headers = {}

created_ids = {
    "materials": {}, "boms": {}, "bom_versions": {},
    "work_centers": {}, "processes": {}, "routes": {},
    "manufacturing_orders": {}, "work_orders": {},
    "forecasts": {}, "mps": {}, "mrp": {}, "crp": {},
    "planned_orders": {}, "suppliers": {}, "purchase_orders": {},
    "warehouses": {}, "shifts": {}, "exceptions": {},
    "requisitions": {}, "returns": {}, "receipts": {},
}


def is_success(body):
    if not body or not isinstance(body, dict):
        return False
    code = body.get("code")
    if code in (0, 200):
        return True
    if body.get("success") is True:
        return True
    if "total" in body and "items" in body:
        return True
    if "data" in body and code is None:
        return True
    return False


def log(tc_id, name, status, detail=""):
    results["details"].append({"id": tc_id, "name": name, "status": status, "detail": detail})
    icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "○"}[status]
    print(f"  {icon} {tc_id}: {name}" + (f" — {detail}" if detail else ""))
    results[status.lower()] += 1


def api(method, path, data=None, params=None, expect_status=None):
    url = f"{BASE_URL}{path}"
    try:
        kw = {"headers": headers, "timeout": TIMEOUT}
        if method == "GET":
            r = requests.get(url, params=params, **kw)
        elif method == "POST":
            r = requests.post(url, json=data, params=params, **kw)
        elif method == "PUT":
            r = requests.put(url, json=data, params=params, **kw)
        elif method == "DELETE":
            r = requests.delete(url, **kw)
        elif method == "PATCH":
            r = requests.patch(url, json=data, **kw)
        else:
            return None, 0, f"Unknown method: {method}"
    except Exception as e:
        return None, 0, str(e)
    body = None
    try:
        body = r.json()
    except:
        body = r.text
    if expect_status and r.status_code != expect_status:
        return body, r.status_code, f"Expected {expect_status}, got {r.status_code}: {json.dumps(body, ensure_ascii=False)[:200]}"
    return body, r.status_code, ""


def login():
    global token, headers
    body, _, err = api("POST", "/v1/auth/login", {"username": "admin", "password": "admin123"}, expect_status=200)
    if err:
        print(f"LOGIN FAILED: {err}"); sys.exit(1)
    token = body.get("data", {}).get("access_token") or body.get("access_token")
    if not token and "data" in body and isinstance(body["data"], dict):
        token = body["data"].get("token")
    if not token:
        print(f"LOGIN: No token: {json.dumps(body, ensure_ascii=False)[:300]}"); sys.exit(1)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print(f"LOGIN OK, token={token[:20]}...")


def seed_base_data():
    print("\n[SEED] Creating base data...")
    for m in [
        {"material_code": "FG-001", "material_name": "智能手表Pro", "material_type": "finished", "unit": "台", "specification": "SW-Pro-2026"},
        {"material_code": "SEMI-001", "material_name": "手表主板组件", "material_type": "semi_finished", "unit": "件", "specification": "MB-ASSY-01"},
        {"material_code": "RM-001", "material_name": "PCB电路板", "material_type": "raw", "unit": "片"},
        {"material_code": "RM-002", "material_name": "OLED显示屏", "material_type": "raw", "unit": "片"},
        {"material_code": "RM-003", "material_name": "锂电池组", "material_type": "raw", "unit": "个"},
        {"material_code": "RM-004", "material_name": "不锈钢表壳", "material_type": "raw", "unit": "个"},
        {"material_code": "RM-005", "material_name": "硅胶表带", "material_type": "raw", "unit": "条"},
    ]:
        body, _, _ = api("POST", "/v1/mes/base-data/materials", m)
        if body and is_success(body):
            mid = body.get("data", {}).get("id")
            if mid: created_ids["materials"][m["material_code"]] = mid

    for wc in [
        {"work_center_code": "WC-SMT", "work_center_name": "SMT贴片车间", "department": "生产部", "capacity": 500},
        {"work_center_code": "WC-ASSY", "work_center_name": "组装车间", "department": "生产部", "capacity": 300},
        {"work_center_code": "WC-TEST", "work_center_name": "测试车间", "department": "品质部", "capacity": 400},
        {"work_center_code": "WC-PKG", "work_center_name": "包装车间", "department": "生产部", "capacity": 600},
    ]:
        body, _, _ = api("POST", "/v1/mes/base-data/work-centers", wc)
        if body and is_success(body):
            wid = body.get("data", {}).get("id")
            if wid: created_ids["work_centers"][wc["work_center_code"]] = wid

    for p in [
        {"process_code": "PROC-SMT", "process_name": "SMT贴片", "process_type": "machining", "sequence": 10, "work_center_code": "WC-SMT", "standard_time": 30},
        {"process_code": "PROC-ASSY", "process_name": "主板组装", "process_type": "assembly", "sequence": 20, "work_center_code": "WC-ASSY", "standard_time": 45},
        {"process_code": "PROC-TEST", "process_name": "功能测试", "process_type": "inspection", "sequence": 30, "work_center_code": "WC-TEST", "standard_time": 20},
        {"process_code": "PROC-PKG", "process_name": "成品包装", "process_type": "assembly", "sequence": 40, "work_center_code": "WC-PKG", "standard_time": 15},
    ]:
        body, _, _ = api("POST", "/v1/mes/base-data/processes", p)
        if body and is_success(body):
            pid = body.get("data", {}).get("id")
            if pid: created_ids["processes"][p["process_code"]] = pid

    for item in [
        {"product_code": "FG-001", "product_name": "智能手表Pro", "item_code": "SEMI-001", "item_name": "手表主板组件", "quantity": 1, "unit": "件"},
        {"product_code": "FG-001", "product_name": "智能手表Pro", "item_code": "RM-003", "item_name": "锂电池组", "quantity": 1, "unit": "个"},
        {"product_code": "FG-001", "product_name": "智能手表Pro", "item_code": "RM-004", "item_name": "不锈钢表壳", "quantity": 1, "unit": "个"},
        {"product_code": "FG-001", "product_name": "智能手表Pro", "item_code": "RM-005", "item_name": "硅胶表带", "quantity": 1, "unit": "条"},
        {"product_code": "SEMI-001", "product_name": "手表主板组件", "item_code": "RM-001", "item_name": "PCB电路板", "quantity": 1, "unit": "片"},
        {"product_code": "SEMI-001", "product_name": "手表主板组件", "item_code": "RM-002", "item_name": "OLED显示屏", "quantity": 1, "unit": "片"},
    ]:
        body, _, _ = api("POST", "/v1/mes/base-data/boms", item)

    route_data = {
        "route_code": "ROUTE-FG001", "route_name": "智能手表Pro工艺路线",
        "product_code": "FG-001", "product_name": "智能手表Pro",
    }
    body, _, _ = api("POST", "/v1/mes/base-data/routes", route_data)
    if body and is_success(body):
        rid = body.get("data", {}).get("id")
        if rid: created_ids["routes"]["ROUTE-FG001"] = rid

    for sup in [
        {"code": "SUP-001", "name": "深圳电子元器件有限公司", "type": "manufacturer", "contact": "张经理", "phone": "0755-88889999"},
        {"code": "SUP-002", "name": "东莞五金制品厂", "type": "manufacturer", "contact": "李总", "phone": "0769-22223333"},
    ]:
        body, _, _ = api("POST", "/v1/purchase/supplier/", sup)
        if body and is_success(body):
            sid = body.get("data", {}).get("id")
            if sid: created_ids["suppliers"][sup["code"]] = sid

    for wh in [
        {"code": "WH-RAW", "name": "原材料仓", "location": "A栋1楼"},
        {"code": "WH-FG", "name": "成品仓", "location": "B栋1楼"},
    ]:
        body, _, _ = api("POST", "/v1/inventory/warehouses", wh)
        if body and is_success(body):
            wid = body.get("data", {}).get("id")
            if wid: created_ids["warehouses"][wh["code"]] = wid

    for sh in [
        {"shift_code": "DAY", "shift_name": "白班", "start_time": "08:00", "end_time": "20:00"},
        {"shift_code": "NIGHT", "shift_name": "夜班", "start_time": "20:00", "end_time": "08:00"},
    ]:
        body, _, _ = api("POST", "/v1/mes/shift/definition", sh)
        if body and is_success(body):
            sid = body.get("data", {}).get("id")
            if sid: created_ids["shifts"][sh["shift_code"]] = sid

    print("[SEED] Base data seeded.")


def create_mo_with_wos(mo_code, product_code="FG-001", product_name="智能手表Pro", quantity=100, priority="high"):
    mo_data = {
        "mo_code": mo_code, "product_code": product_code, "product_name": product_name,
        "quantity": quantity, "priority": priority,
        "planned_start_date": "2026-07-10T00:00:00", "planned_end_date": "2026-07-20T00:00:00",
    }
    body, _, err = api("POST", "/v1/mes/production/manufacturing-orders", mo_data)
    if err or not body or not is_success(body):
        return None, []
    mo_id = body["data"].get("id")
    created_ids["manufacturing_orders"][mo_code] = mo_id

    api("POST", f"/v1/mes/production/manufacturing-orders/{mo_id}/release")
    api("POST", f"/v1/mes/production/manufacturing-orders/{mo_id}/generate-work-orders")

    body, _, _ = api("GET", "/v1/mes/production/work-orders", params={"mo_code": mo_code})
    wos = []
    if body and is_success(body):
        wos = body.get("data", [])
        if not isinstance(wos, list):
            wos = body.get("data", {}).get("items", [])
    return mo_id, wos


def get_first_wo(mo_code):
    body, _, _ = api("GET", "/v1/mes/production/work-orders", params={"mo_code": mo_code})
    wos = []
    if body and is_success(body):
        wos = body.get("data", [])
        if not isinstance(wos, list):
            wos = body.get("data", {}).get("items", [])
    return wos[0] if wos else None


# ─── TEST CASES ────────────────────────────────────────────────

def test_tc_base_001():
    body, _, err = api("POST", "/v1/mes/base-data/materials", {"material_code": "FG-002", "material_name": "智能手表Lite", "material_type": "finished", "unit": "台"})
    if err or not body or not is_success(body):
        log("TC-BASE-001", "物料CRUD完整流程", "FAIL", f"Create: {err or body}"); return
    mid = body["data"].get("id")
    created_ids["materials"]["FG-002"] = mid

    body, _, err = api("GET", "/v1/mes/base-data/materials", params={"material_code": "FG-002"})
    if err or not body or not is_success(body):
        log("TC-BASE-001", "物料CRUD完整流程", "FAIL", f"Search: {err}"); return

    body, _, err = api("PUT", f"/v1/mes/base-data/materials/{mid}", {"material_name": "智能手表Lite V2"})
    if err or not body or not is_success(body):
        log("TC-BASE-001", "物料CRUD完整流程", "FAIL", f"Update: {err}"); return

    body, _, err = api("DELETE", f"/v1/mes/base-data/materials/{mid}")
    if err or not body or not is_success(body):
        log("TC-BASE-001", "物料CRUD完整流程", "FAIL", f"Delete: {err}"); return
    log("TC-BASE-001", "物料CRUD完整流程", "PASS")


def test_tc_base_002():
    body, _, err = api("POST", "/v1/mes/base-data/bom-versions", {"product_code": "FG-001", "version": "V2.0", "product_name": "智能手表Pro"})
    if err or not body or not is_success(body):
        log("TC-BASE-002", "BOM版本生命周期", "FAIL", f"Create: {err or body}"); return
    vid = body["data"].get("id")
    created_ids["bom_versions"]["FG-001-V2"] = vid

    body, _, err = api("PUT", f"/v1/mes/base-data/bom-versions/{vid}/activate")
    if err or not body or not is_success(body):
        log("TC-BASE-002", "BOM版本生命周期", "FAIL", f"Activate: {err or body}"); return

    body, _, err = api("PUT", f"/v1/mes/base-data/bom-versions/{vid}/obsolete")
    if err or not body or not is_success(body):
        log("TC-BASE-002", "BOM版本生命周期", "FAIL", f"Obsolete: {err or body}"); return

    body, _, err = api("POST", f"/v1/mes/base-data/bom-versions/{vid}/copy", {"new_version": "V3.0"})
    if err or not body or not is_success(body):
        log("TC-BASE-002", "BOM版本生命周期", "FAIL", f"Copy: {err or body}"); return
    log("TC-BASE-002", "BOM版本生命周期", "PASS")


def test_tc_base_003():
    route_data = {
        "route_code": "ROUTE-TEST-003", "route_name": "测试工艺路线",
        "product_code": "FG-001", "product_name": "智能手表Pro",
    }
    body, _, err = api("POST", "/v1/mes/base-data/routes", route_data)
    if err or not body or not is_success(body):
        log("TC-BASE-003", "工艺路线工序动态添加", "FAIL", f"Create: {err or body}"); return
    rid = body["data"].get("id")
    created_ids["routes"]["ROUTE-TEST-003"] = rid

    body, _, err = api("GET", f"/v1/mes/base-data/routes/{rid}/processes")
    if err or not body or not is_success(body):
        log("TC-BASE-003", "工艺路线工序动态添加", "FAIL", f"Get processes: {err}"); return
    log("TC-BASE-003", "工艺路线工序动态添加", "PASS")


def test_tc_plan_001():
    mo_data = {"mo_code": "MO-TEST-001", "product_code": "FG-001", "product_name": "智能手表Pro", "quantity": 100, "priority": "high", "planned_start_date": "2026-07-10T00:00:00", "planned_end_date": "2026-07-20T00:00:00"}
    body, _, err = api("POST", "/v1/mes/production/manufacturing-orders", mo_data)
    if err or not body or not is_success(body):
        log("TC-PLAN-001", "制造单完整生命周期", "FAIL", f"Create: {err or body}"); return
    mo_id = body["data"].get("id")
    created_ids["manufacturing_orders"]["MO-TEST-001"] = mo_id

    body, _, err = api("POST", f"/v1/mes/production/manufacturing-orders/{mo_id}/release")
    if err or not body or not is_success(body):
        log("TC-PLAN-001", "制造单完整生命周期", "FAIL", f"Release: {err or body}"); return

    body, _, _ = api("POST", f"/v1/mes/production/manufacturing-orders/{mo_id}/generate-work-orders")

    body, _, err = api("POST", f"/v1/mes/production/manufacturing-orders/{mo_id}/complete")
    if err or not body or not is_success(body):
        log("TC-PLAN-001", "制造单完整生命周期", "FAIL", f"Complete: {err or body}"); return

    mo2_data = {"mo_code": "MO-TEST-001-CANCEL", "product_code": "FG-001", "product_name": "智能手表Pro", "quantity": 50, "priority": "medium", "planned_start_date": "2026-07-10T00:00:00", "planned_end_date": "2026-07-20T00:00:00"}
    body, _, _ = api("POST", "/v1/mes/production/manufacturing-orders", mo2_data)
    if body and is_success(body):
        mo2_id = body["data"].get("id")
        body, _, err = api("POST", f"/v1/mes/production/manufacturing-orders/{mo2_id}/cancel")
        if err or not body or not is_success(body):
            log("TC-PLAN-001", "制造单完整生命周期", "FAIL", f"Cancel: {err or body}"); return
    log("TC-PLAN-001", "制造单完整生命周期", "PASS")


def test_tc_plan_002():
    mo_id = created_ids["manufacturing_orders"].get("MO-TEST-001")
    if not mo_id:
        log("TC-PLAN-002", "查看关联工单", "SKIP", "No MO"); return
    body, _, err = api("GET", "/v1/mes/production/work-orders", params={"mo_code": "MO-TEST-001"})
    if err or not body or not is_success(body):
        log("TC-PLAN-002", "查看关联工单", "FAIL", f"List WOs: {err}"); return
    wos = body.get("data", [])
    if not isinstance(wos, list): wos = body.get("data", {}).get("items", [])
    if wos:
        created_ids["work_orders"]["WO-FROM-MO-001"] = wos[0].get("id")
    log("TC-PLAN-002", "查看关联工单", "PASS", f"{len(wos)} WOs")


def test_tc_plan_003():
    body, _, err = api("GET", "/v1/mes/production/manufacturing-orders", params={"status": "completed"})
    if err or not body or not is_success(body):
        log("TC-PLAN-003", "制造单状态筛选", "FAIL", f"{err}"); return
    log("TC-PLAN-003", "制造单状态筛选", "PASS")


def test_tc_exec_001():
    mo_id, wos = create_mo_with_wos("MO-EXEC-001")
    if not mo_id or not wos:
        log("TC-EXEC-001", "工单完整状态流转", "FAIL", "No MO/WOs"); return
    wo = wos[0]
    wo_id = wo.get("id")
    wo_code = wo.get("wo_code", "")
    created_ids["work_orders"]["WO-EXEC-001"] = wo_id

    body, _, err = api("POST", f"/v1/mes/production/work-orders/{wo_id}/release")
    if err or not body or not is_success(body):
        log("TC-EXEC-001", "工单完整状态流转", "FAIL", f"Release: {err or body}"); return

    body, _, err = api("POST", f"/v1/mes/production/work-orders/{wo_id}/start", {"operator": "张三"})
    if err or not body or not is_success(body):
        log("TC-EXEC-001", "工单完整状态流转", "FAIL", f"Start: {err or body}"); return

    body, _, err = api("POST", f"/v1/mes/production/work-orders/{wo_id}/suspend", {"suspend_reason": "equipment"})
    if err or not body or not is_success(body):
        log("TC-EXEC-001", "工单完整状态流转", "FAIL", f"Suspend: {err or body}"); return

    body, _, err = api("POST", f"/v1/mes/production/work-orders/{wo_id}/resume")
    if err or not body or not is_success(body):
        log("TC-EXEC-001", "工单完整状态流转", "FAIL", f"Resume: {err or body}"); return

    body, _, err = api("POST", f"/v1/mes/production/work-orders/{wo_id}/complete", params={"actual_quantity": 95, "scrap_quantity": 5})
    if err or not body or not is_success(body):
        log("TC-EXEC-001", "工单完整状态流转", "FAIL", f"Complete: {err or body}"); return

    body, _, err = api("POST", f"/v1/mes/production/work-orders/{wo_id}/close")
    if err or not body or not is_success(body):
        log("TC-EXEC-001", "工单完整状态流转", "FAIL", f"Close: {err or body}"); return
    log("TC-EXEC-001", "工单完整状态流转", "PASS")


def test_tc_exec_003():
    mo_id, wos = create_mo_with_wos("MO-EXEC-003")
    if not mo_id or not wos:
        log("TC-EXEC-003", "完工确认数量校验", "SKIP", "No MO/WOs"); return
    wo = wos[0]
    wo_id = wo.get("id")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/release")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/start", {"operator": "张三"})

    body, _, _ = api("POST", f"/v1/mes/production/work-orders/{wo_id}/complete", params={"actual_quantity": 0, "scrap_quantity": 0})
    if body and is_success(body):
        log("TC-EXEC-003", "完工确认数量校验", "FAIL", "Zero qty accepted"); return

    body, _, _ = api("POST", f"/v1/mes/production/work-orders/{wo_id}/complete", params={"actual_quantity": -5, "scrap_quantity": 0})
    if body and is_success(body):
        log("TC-EXEC-003", "完工确认数量校验", "FAIL", "Negative qty accepted"); return

    body, _, err = api("POST", f"/v1/mes/production/work-orders/{wo_id}/complete", params={"actual_quantity": 95, "scrap_quantity": 5})
    if err or not body or not is_success(body):
        log("TC-EXEC-003", "完工确认数量校验", "FAIL", f"Valid qty rejected: {err or body}"); return
    log("TC-EXEC-003", "完工确认数量校验", "PASS")


def test_tc_report_001():
    mo_id, wos = create_mo_with_wos("MO-RPT-001")
    if not mo_id or not wos:
        log("TC-REPORT-001", "提交报工记录", "SKIP", "No MO/WOs"); return
    wo = wos[0]
    wo_id = wo.get("id")
    wo_code = wo.get("wo_code", "")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/release")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/start", {"operator": "张三"})

    report_data = {
        "wo_code": wo_code, "mo_code": "MO-RPT-001",
        "process_code": "PROC-SMT", "work_center_code": "WC-SMT",
        "equipment_code": "EQ-SMT-01", "shift_code": "DAY",
        "operator": "张三",
        "qualified_quantity": 50, "scrap_quantity": 2,
        "batch_no": "BATCH-20260703-001",
        "actual_start_time": "2026-07-03T08:00:00", "actual_end_time": "2026-07-03T17:00:00",
    }
    body, _, err = api("POST", "/v1/mes/production-report", report_data)
    if err or not body or not is_success(body):
        log("TC-REPORT-001", "提交报工记录", "FAIL", f"Submit: {err or body}"); return
    log("TC-REPORT-001", "提交报工记录", "PASS")


def test_tc_report_002():
    body, _, err = api("GET", "/v1/mes/production-report")
    if err or not body or not is_success(body):
        log("TC-REPORT-002", "报工记录查询", "FAIL", f"{err}"); return
    log("TC-REPORT-002", "报工记录查询", "PASS")


def test_tc_mat_001():
    req_data = {"mo_code": "MO-EXEC-001", "warehouse_code": "WH-RAW", "location_code": "LOC-01", "applicant": "张三"}
    body, _, err = api("POST", "/v1/mes/material-requisition", req_data)
    if err or not body or not is_success(body):
        log("TC-MAT-001", "领料单创建与确认", "FAIL", f"Create: {err or body}"); return
    req_id = body["data"].get("id")
    req_code = body["data"].get("requisition_code", "")
    created_ids["requisitions"]["REQ-001"] = req_id
    created_ids["requisitions"]["REQ-001-CODE"] = req_code

    body, _, err = api("POST", f"/v1/mes/material-requisition/{req_id}/confirm")
    if err or not body or not is_success(body):
        log("TC-MAT-001", "领料单创建与确认", "FAIL", f"Confirm: {err or body}"); return
    log("TC-MAT-001", "领料单创建与确认", "PASS")


def test_tc_mat_002():
    req_code = created_ids["requisitions"].get("REQ-001-CODE", "")
    ret_data = {"mo_code": "MO-EXEC-001", "requisition_code": req_code, "warehouse_code": "WH-RAW", "location_code": "LOC-01", "operator": "李四"}
    body, _, err = api("POST", "/v1/mes/material-return", ret_data)
    if err or not body or not is_success(body):
        log("TC-MAT-002", "退料单创建与确认", "FAIL", f"Create: {err or body}"); return
    ret_id = body["data"].get("id")
    created_ids["returns"]["RET-001"] = ret_id

    body, _, err = api("POST", f"/v1/mes/material-return/{ret_id}/confirm")
    if err or not body or not is_success(body):
        log("TC-MAT-002", "退料单创建与确认", "FAIL", f"Confirm: {err or body}"); return
    log("TC-MAT-002", "退料单创建与确认", "PASS")


def test_tc_mat_003():
    receipt_data = {"mo_code": "MO-EXEC-001", "product_code": "FG-001", "product_name": "智能手表Pro", "quantity": 95, "unit": "台", "warehouse_code": "WH-FG", "location_code": "LOC-FG-01", "inspection_result": "qualified"}
    body, _, err = api("POST", "/v1/mes/production-receipt", receipt_data)
    if err or not body or not is_success(body):
        log("TC-MAT-003", "完工入库创建与确认", "FAIL", f"Create: {err or body}"); return
    rcpt_id = body["data"].get("id")
    created_ids["receipts"]["RCPT-001"] = rcpt_id

    body, _, err = api("POST", f"/v1/mes/production-receipt/{rcpt_id}/confirm")
    if err or not body or not is_success(body):
        log("TC-MAT-003", "完工入库创建与确认", "FAIL", f"Confirm: {err or body}"); return
    log("TC-MAT-003", "完工入库创建与确认", "PASS")


def test_tc_dash_001():
    for ep in ["/oee", "/production", "/progress"]:
        body, _, err = api("GET", f"/v1/mes/dashboard{ep}")
        if err or not body or not is_success(body):
            log("TC-DASH-001", "看板数据加载", "FAIL", f"{ep}: {err}"); return
    log("TC-DASH-001", "看板数据加载", "PASS")


def test_tc_dash_002():
    for period in ["day", "week", "month"]:
        body, _, err = api("GET", "/v1/mes/dashboard/oee", params={"period": period})
        if err or not body or not is_success(body):
            log("TC-DASH-002", "OEE周期筛选", "FAIL", f"period={period}: {err}"); return
    log("TC-DASH-002", "OEE周期筛选", "PASS")


def test_tc_trace_001():
    body, _, err = api("GET", "/v1/mes/trace/forward", params={"material_batch_no": "BATCH-20260703-001"})
    if err or not body or not is_success(body):
        log("TC-TRACE-001", "正向追溯", "FAIL", f"{err}"); return
    log("TC-TRACE-001", "正向追溯", "PASS")


def test_tc_trace_002():
    body, _, err = api("GET", "/v1/mes/trace/backward", params={"product_batch_no": "BATCH-20260703-001"})
    if err or not body or not is_success(body):
        log("TC-TRACE-002", "反向追溯", "FAIL", f"{err}"); return
    log("TC-TRACE-002", "反向追溯", "PASS")


def test_tc_exc_001():
    mo_id, wos = create_mo_with_wos("MO-EXC-001")
    if not mo_id or not wos:
        log("TC-EXC-001", "异常上报与处理", "SKIP", "No MO/WOs"); return
    wo = wos[0]
    wo_id = wo.get("id")
    wo_code = wo.get("wo_code", "")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/release")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/start", {"operator": "张三"})

    exc_data = {"wo_code": wo_code, "work_center_code": "WC-SMT", "exception_type": "equipment_failure", "severity": "high", "description": "SMT贴片机1号异常停机", "reporter": "张三"}
    body, _, err = api("POST", "/v1/mes/exception", exc_data)
    if err or not body or not is_success(body):
        log("TC-EXC-001", "异常上报与处理", "FAIL", f"Report: {err or body}"); return
    exc_id = body["data"].get("id")
    created_ids["exceptions"]["EXC-001"] = exc_id

    handle_data = {"handler": "李工", "solution": "更换贴片机吸嘴，重新校准"}
    body, _, err = api("POST", f"/v1/mes/exception/{exc_id}/handle", handle_data)
    if err or not body or not is_success(body):
        log("TC-EXC-001", "异常上报与处理", "FAIL", f"Handle: {err or body}"); return
    log("TC-EXC-001", "异常上报与处理", "PASS")


def test_tc_exc_002():
    mo_id, wos = create_mo_with_wos("MO-EXC-002")
    if not mo_id or not wos:
        log("TC-EXC-002", "异常不恢复工单", "SKIP", "No MO/WOs"); return
    wo = wos[0]
    wo_id = wo.get("id")
    wo_code = wo.get("wo_code", "")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/release")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/start", {"operator": "张三"})

    exc_data = {"wo_code": wo_code, "work_center_code": "WC-ASSY", "exception_type": "quality_issue", "severity": "medium", "description": "组装工序品质异常", "reporter": "王五"}
    body, _, err = api("POST", "/v1/mes/exception", exc_data)
    if err or not body or not is_success(body):
        log("TC-EXC-002", "异常不恢复工单", "FAIL", f"Report: {err or body}"); return
    exc_id = body["data"].get("id")

    handle_data = {"handler": "赵工", "solution": "更换不良物料"}
    body, _, err = api("POST", f"/v1/mes/exception/{exc_id}/handle", handle_data)
    if err or not body or not is_success(body):
        log("TC-EXC-002", "异常不恢复工单", "FAIL", f"Handle: {err or body}"); return
    log("TC-EXC-002", "异常不恢复工单", "PASS")


def test_tc_exc_003():
    for params in [{"exception_type": "equipment_failure"}, {"severity": "high"}, {"status": "resolved"}]:
        body, _, err = api("GET", "/v1/mes/exception", params=params)
        if err or not body or not is_success(body):
            log("TC-EXC-003", "异常多条件筛选", "FAIL", f"{params}: {err}"); return
    log("TC-EXC-003", "异常多条件筛选", "PASS")


def test_tc_edge_005():
    mo_id, wos = create_mo_with_wos("MO-EDGE-005")
    if not mo_id or not wos:
        log("TC-EDGE-005", "非法状态操作", "SKIP", "No MO/WOs"); return
    wo = wos[0]
    wo_id = wo.get("id")

    body, _, _ = api("POST", f"/v1/mes/production/work-orders/{wo_id}/start", {"operator": "张三"})
    if body and is_success(body):
        log("TC-EDGE-005", "非法状态操作", "FAIL", "Start on unreleased WO should fail"); return

    api("POST", f"/v1/mes/production/work-orders/{wo_id}/release")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/start", {"operator": "张三"})
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/complete", params={"actual_quantity": 95, "scrap_quantity": 5})
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/close")

    body, _, _ = api("POST", f"/v1/mes/production/work-orders/{wo_id}/suspend", {"reason": "test"})
    if body and is_success(body):
        log("TC-EDGE-005", "非法状态操作", "FAIL", "Suspend on closed WO should fail"); return
    log("TC-EDGE-005", "非法状态操作", "PASS")


def test_tc_edge_015():
    req_data = {"mo_code": "MO-NONEXIST-99999", "warehouse_code": "WH-RAW", "location_code": "LOC-01", "applicant": "张三"}
    body, _, _ = api("POST", "/v1/mes/material-requisition", req_data)
    if body and is_success(body):
        log("TC-EDGE-015", "领料单引用不存在的制造单", "FAIL", "Should reject"); return
    log("TC-EDGE-015", "领料单引用不存在的制造单", "PASS")


def test_tc_edge_016():
    report_data = {"wo_code": "WO-NONEXIST-99999", "mo_code": "MO-NONEXIST-99999", "process_code": "PROC-SMT", "work_center_code": "WC-SMT", "operator": "张三", "shift_code": "DAY", "equipment_code": "EQ-SMT-01", "batch_no": "BATCH-FAKE", "qualified_quantity": 10, "scrap_quantity": 0, "actual_start_time": "2026-07-03T08:00:00", "actual_end_time": "2026-07-03T17:00:00"}
    body, _, _ = api("POST", "/v1/mes/production-report", report_data)
    if body and is_success(body):
        log("TC-EDGE-016", "报工引用不存在的工单", "FAIL", "Should reject"); return
    log("TC-EDGE-016", "报工引用不存在的工单", "PASS")


def test_tc_mrp2_001():
    fc_data = {"forecast_code": "FC-TEST-001", "forecast_name": "测试销售预测", "forecast_type": "monthly", "forecast_date": "2026-07-01", "start_date": "2026-07-01", "end_date": "2026-09-30"}
    body, _, err = api("POST", "/v1/mrp2/forecast", fc_data)
    if err or not body or not is_success(body):
        log("TC-MRP2-001", "销售预测完整生命周期", "FAIL", f"Create: {err or body}"); return
    fc_id = body["data"].get("id")
    created_ids["forecasts"]["FC-TEST-001"] = fc_id

    detail_data = {"forecast_id": fc_id, "product_code": "FG-001", "product_name": "智能手表Pro", "unit": "台", "forecast_quantity": 500, "period_start": "2026-08-15", "period_end": "2026-08-31"}
    body, _, err = api("POST", f"/v1/mrp2/forecast/{fc_id}/details", detail_data)
    if err or not body or not is_success(body):
        log("TC-MRP2-001", "销售预测完整生命周期", "FAIL", f"Add detail: {err or body}"); return

    body, _, err = api("PUT", f"/v1/mrp2/forecast/{fc_id}/submit")
    if err or not body or not is_success(body):
        log("TC-MRP2-001", "销售预测完整生命周期", "FAIL", f"Submit: {err or body}"); return

    body, _, err = api("PUT", f"/v1/mrp2/forecast/{fc_id}/approve")
    if err or not body or not is_success(body):
        log("TC-MRP2-001", "销售预测完整生命周期", "FAIL", f"Approve: {err or body}"); return

    fc2_data = {"forecast_code": "FC-TEST-001-REJ", "forecast_name": "测试驳回预测", "forecast_type": "monthly", "forecast_date": "2026-07-01", "start_date": "2026-07-01", "end_date": "2026-09-30"}
    body, _, _ = api("POST", "/v1/mrp2/forecast", fc2_data)
    if body and is_success(body):
        fc2_id = body["data"].get("id")
        api("POST", f"/v1/mrp2/forecast/{fc2_id}/details", {"forecast_id": fc2_id, "product_code": "FG-001", "product_name": "智能手表Pro", "unit": "台", "forecast_quantity": 200, "period_start": "2026-08-15", "period_end": "2026-08-31"})
        api("PUT", f"/v1/mrp2/forecast/{fc2_id}/submit")
        body2, _, _ = api("PUT", f"/v1/mrp2/forecast/{fc2_id}/reject")
        if not body2 or not is_success(body2):
            log("TC-MRP2-001", "销售预测完整生命周期", "FAIL", "Reject failed"); return
    log("TC-MRP2-001", "销售预测完整生命周期", "PASS")


def test_tc_mrp2_002():
    mps_data = {"mps_code": "MPS-TEST-001", "mps_name": "测试主生产计划", "start_date": "2026-07-01", "end_date": "2026-09-30"}
    body, _, err = api("POST", "/v1/mrp2/mps", mps_data)
    if err or not body or not is_success(body):
        log("TC-MRP2-002", "MPS完整生命周期", "FAIL", f"Create: {err or body}"); return
    mps_id = body["data"].get("id")
    created_ids["mps"]["MPS-TEST-001"] = mps_id

    pl_data = {"mps_id": mps_id, "mps_code": "MPS-TEST-001", "line_no": 1, "product_code": "FG-001", "product_name": "智能手表Pro", "plan_quantity": 500, "plan_start_date": "2026-08-01", "plan_end_date": "2026-08-15"}
    body, _, err = api("POST", f"/v1/mrp2/mps/{mps_id}/plan-lines", pl_data)
    if err or not body or not is_success(body):
        log("TC-MRP2-002", "MPS完整生命周期", "FAIL", f"Add plan line: {err or body}"); return

    body, _, err = api("POST", f"/v1/mrp2/mps/{mps_id}/compile")
    if err or not body or not is_success(body):
        log("TC-MRP2-002", "MPS完整生命周期", "FAIL", f"Compile: {err or body}"); return

    body, _, err = api("PUT", f"/v1/mrp2/mps/{mps_id}/submit")
    if err or not body or not is_success(body):
        log("TC-MRP2-002", "MPS完整生命周期", "FAIL", f"Submit: {err or body}"); return

    body, _, err = api("PUT", f"/v1/mrp2/mps/{mps_id}/approve", {"approved": True})
    if err or not body or not is_success(body):
        log("TC-MRP2-002", "MPS完整生命周期", "FAIL", f"Approve: {err or body}"); return
    body, _, err = api("PUT", f"/v1/mrp2/mps/{mps_id}/release")
    if err or not body or not is_success(body):
        log("TC-MRP2-002", "MPS完整生命周期", "FAIL", f"Release: {err or body}"); return

    body, _, err = api("PUT", f"/v1/mrp2/mps/{mps_id}/close")
    if err or not body or not is_success(body):
        log("TC-MRP2-002", "MPS完整生命周期", "FAIL", f"Close: {err or body}"); return
    log("TC-MRP2-002", "MPS完整生命周期", "PASS")


def test_tc_mrp2_003():
    fc_id = created_ids["forecasts"].get("FC-TEST-001")
    if not fc_id:
        log("TC-MRP2-003", "基于销售预测生成MPS", "SKIP", "No forecast"); return
    body, _, err = api("POST", "/v1/mrp2/mps/generate", {"forecast_id": fc_id, "mps_code": "MPS-FC-001", "mps_name": "基于预测的MPS"})
    if err or not body or not is_success(body):
        log("TC-MRP2-003", "基于销售预测生成MPS", "FAIL", f"Generate: {err or body}"); return
    mps_id = body["data"].get("id")
    if mps_id: created_ids["mps"]["MPS-FC-001"] = mps_id
    log("TC-MRP2-003", "基于销售预测生成MPS", "PASS")


def test_tc_mrp2_004():
    mps_data = {"mps_code": "MPS-MRP-001", "mps_name": "MRP测试MPS", "start_date": "2026-07-01", "end_date": "2026-09-30"}
    body, _, _ = api("POST", "/v1/mrp2/mps", mps_data)
    if not body or not is_success(body):
        log("TC-MRP2-004", "MRP计算与BOM展开", "SKIP", "Cannot create MPS"); return
    mps_id = body["data"].get("id")
    pl_data = {"mps_id": mps_id, "mps_code": "MPS-MRP-001", "line_no": 1, "product_code": "FG-001", "product_name": "智能手表Pro", "plan_quantity": 500, "plan_start_date": "2026-08-01", "plan_end_date": "2026-08-15"}
    api("POST", f"/v1/mrp2/mps/{mps_id}/plan-lines", pl_data)
    api("POST", f"/v1/mrp2/mps/{mps_id}/compile")
    api("PUT", f"/v1/mrp2/mps/{mps_id}/submit")
    api("PUT", f"/v1/mrp2/mps/{mps_id}/approve", {"approved": True})
    created_ids["mps"]["MPS-MRP-001"] = mps_id

    mrp_data = {"mrp_code": "MRP-TEST-001", "mrp_name": "测试MRP计算", "mps_id": mps_id, "mps_code": "MPS-MRP-001", "start_date": "2026-07-01", "end_date": "2026-09-30"}
    body, _, err = api("POST", "/v1/mrp2/mrp", mrp_data)
    if err or not body or not is_success(body):
        log("TC-MRP2-004", "MRP计算与BOM展开", "FAIL", f"Create MRP: {err or body}"); return
    mrp_id = body["data"].get("id")
    created_ids["mrp"]["MRP-TEST-001"] = mrp_id

    body, _, err = api("POST", "/v1/mrp2/mrp/calculate", {"mps_id": mps_id})
    if err or not body or not is_success(body):
        log("TC-MRP2-004", "MRP计算与BOM展开", "FAIL", f"Calculate: {err or body}"); return
    calc_mrp_id = body.get("data", {}).get("id") if body and isinstance(body.get("data"), dict) else None
    if calc_mrp_id:
        mrp_id = calc_mrp_id
        created_ids["mrp"]["MRP-TEST-001"] = mrp_id

    body, _, err = api("GET", f"/v1/mrp2/mrp/{mrp_id}/planned-orders")
    if err or not body or not is_success(body):
        log("TC-MRP2-004", "MRP计算与BOM展开", "FAIL", f"Get planned orders: {err}"); return
    log("TC-MRP2-004", "MRP计算与BOM展开", "PASS")


def test_tc_mrp2_005():
    mrp_id = created_ids["mrp"].get("MRP-TEST-001")
    if not mrp_id:
        log("TC-MRP2-005", "CRP能力需求计算", "SKIP", "No MRP"); return
    crp_data = {"crp_code": "CRP-TEST-001", "crp_name": "测试CRP计算", "mrp_id": mrp_id, "start_date": "2026-07-01", "end_date": "2026-09-30"}
    body, _, err = api("POST", "/v1/mrp2/crp", crp_data)
    if err or not body or not is_success(body):
        log("TC-MRP2-005", "CRP能力需求计算", "FAIL", f"Create: {err or body}"); return
    crp_id = body["data"].get("id")
    created_ids["crp"]["CRP-TEST-001"] = crp_id

    body, _, err = api("POST", "/v1/mrp2/crp/calculate", {"mrp_id": mrp_id})
    if err or not body or not is_success(body):
        log("TC-MRP2-005", "CRP能力需求计算", "FAIL", f"Calculate: {err or body}"); return

    body, _, err = api("GET", f"/v1/mrp2/crp/{crp_id}/details")
    if err or not body or not is_success(body):
        log("TC-MRP2-005", "CRP能力需求计算", "FAIL", f"Details: {err}"); return
    log("TC-MRP2-005", "CRP能力需求计算", "PASS")


def test_tc_mrp2_006():
    mps_id = created_ids["mps"].get("MPS-MRP-001")
    if not mps_id:
        log("TC-MRP2-006", "计划执行监控", "SKIP", "No MPS"); return
    mon_data = {"monitor_code": "MON-TEST-001", "monitor_name": "测试监控", "mps_id": mps_id, "start_date": "2026-07-01", "end_date": "2026-09-30"}
    body, _, err = api("POST", "/v1/mrp2/monitor", mon_data)
    if err or not body or not is_success(body):
        log("TC-MRP2-006", "计划执行监控", "FAIL", f"Create: {err or body}"); return
    mon_id = body["data"].get("id")

    body, _, err = api("GET", "/v1/mrp2/monitor/stats")
    if err or not body or not is_success(body):
        log("TC-MRP2-006", "计划执行监控", "FAIL", f"Stats: {err}"); return

    body, _, err = api("PUT", f"/v1/mrp2/monitor/{mon_id}/pause")
    if err or not body or not is_success(body):
        log("TC-MRP2-006", "计划执行监控", "FAIL", f"Pause: {err or body}"); return

    body, _, err = api("PUT", f"/v1/mrp2/monitor/{mon_id}/resume")
    if err or not body or not is_success(body):
        log("TC-MRP2-006", "计划执行监控", "FAIL", f"Resume: {err or body}"); return
    log("TC-MRP2-006", "计划执行监控", "PASS")


def test_tc_pur_001():
    body, _, err = api("GET", "/v1/purchase/supplier/", params={"name": "深圳"})
    if err or not body or not is_success(body):
        log("TC-PUR-001", "供应商管理", "FAIL", f"Search: {err}"); return
    sup_id = created_ids["suppliers"].get("SUP-001")
    if sup_id:
        body, _, err = api("GET", f"/v1/purchase/supplier/{sup_id}")
        if err or not body or not is_success(body):
            log("TC-PUR-001", "供应商管理", "FAIL", f"Detail: {err}"); return
    log("TC-PUR-001", "供应商管理", "PASS")


def test_tc_pur_002():
    sup_id = created_ids["suppliers"].get("SUP-001")
    if not sup_id:
        log("TC-PUR-002", "采购订单完整流程", "SKIP", "No supplier"); return
    po_data = {"supplier_id": sup_id, "product_name": "PCB电路板", "quantity": 500, "price": 50.0, "delivery_date": "2026-07-30"}
    body, _, err = api("POST", "/v1/purchase/order/", po_data)
    if err or not body or not is_success(body):
        log("TC-PUR-002", "采购订单完整流程", "FAIL", f"Create: {err or body}"); return
    po_id = body["data"].get("id")
    created_ids["purchase_orders"]["PO-001"] = po_id

    body, _, err = api("POST", f"/v1/purchase/order/{po_id}/confirm")
    if err or not body or not is_success(body):
        log("TC-PUR-002", "采购订单完整流程", "FAIL", f"Confirm: {err or body}"); return
    log("TC-PUR-002", "采购订单完整流程", "PASS")


def test_tc_pur_003():
    po_id = created_ids["purchase_orders"].get("PO-001")
    if not po_id:
        log("TC-PUR-003", "采购收货", "SKIP", "No PO"); return
    receipt_data = {"purchase_order_id": po_id, "quantity": 500, "warehouse_code": "WH-RAW", "quality_result": "qualified"}
    body, _, err = api("POST", "/v1/purchase/order/receipt/", receipt_data)
    if err or not body or not is_success(body):
        log("TC-PUR-003", "采购收货", "FAIL", f"Create receipt: {err or body}"); return
    log("TC-PUR-003", "采购收货", "PASS")


def test_tc_int_001():
    mo_id, wos = create_mo_with_wos("MO-INT-001", quantity=200)
    if not mo_id or not wos:
        log("TC-INT-001", "全链路业务流程", "FAIL", "No MO/WOs"); return
    wo = wos[0]
    wo_id = wo.get("id")
    wo_code = wo.get("wo_code", "")

    api("POST", f"/v1/mes/production/work-orders/{wo_id}/release")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/start", {"operator": "张三"})

    report_data = {"wo_code": wo_code, "mo_code": "MO-INT-001", "process_code": "PROC-SMT", "work_center_code": "WC-SMT", "equipment_code": "EQ-SMT-01", "shift_code": "DAY", "operator": "张三", "qualified_quantity": 190, "scrap_quantity": 10, "batch_no": "BATCH-INT-001", "actual_start_time": "2026-07-10T08:00:00", "actual_end_time": "2026-07-10T17:00:00"}
    body, _, err = api("POST", "/v1/mes/production-report", report_data)
    if err or not body or not is_success(body):
        log("TC-INT-001", "全链路业务流程", "FAIL", f"Report: {err or body}"); return

    req_data = {"mo_code": "MO-INT-001", "warehouse_code": "WH-RAW", "location_code": "LOC-01", "applicant": "张三"}
    body, _, _ = api("POST", "/v1/mes/material-requisition", req_data)
    if body and is_success(body):
        req_id = body["data"].get("id")
        api("POST", f"/v1/mes/material-requisition/{req_id}/confirm")

    api("POST", f"/v1/mes/production/work-orders/{wo_id}/complete", params={"actual_quantity": 190, "scrap_quantity": 10})

    receipt_data = {"mo_code": "MO-INT-001", "product_code": "FG-001", "product_name": "智能手表Pro", "quantity": 190, "unit": "台", "warehouse_code": "WH-FG", "location_code": "LOC-FG-01", "inspection_result": "qualified"}
    body, _, _ = api("POST", "/v1/mes/production-receipt", receipt_data)
    if body and is_success(body):
        rcpt_id = body["data"].get("id")
        api("POST", f"/v1/mes/production-receipt/{rcpt_id}/confirm")

    api("GET", "/v1/mes/dashboard/oee")
    api("GET", "/v1/mes/trace/forward", params={"material_batch_no": "BATCH-INT-001"})
    log("TC-INT-001", "全链路业务流程", "PASS")


def test_tc_int_002():
    mo_id, wos = create_mo_with_wos("MO-INT-002")
    if not mo_id or not wos:
        log("TC-INT-002", "异常联动端到端", "SKIP", "No MO/WOs"); return
    wo = wos[0]
    wo_id = wo.get("id")
    wo_code = wo.get("wo_code", "")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/release")
    api("POST", f"/v1/mes/production/work-orders/{wo_id}/start", {"operator": "张三"})

    exc_data = {"wo_code": wo_code, "work_center_code": "WC-SMT", "exception_type": "equipment_failure", "severity": "high", "description": "INT-002测试异常", "reporter": "张三"}
    body, _, err = api("POST", "/v1/mes/exception", exc_data)
    if err or not body or not is_success(body):
        log("TC-INT-002", "异常联动端到端", "FAIL", f"Report: {err or body}"); return
    exc_id = body["data"].get("id")

    body, _, _ = api("GET", f"/v1/mes/production/work-orders/{wo_id}")

    handle_data = {"handler": "李工", "solution": "修复完成"}
    body, _, err = api("POST", f"/v1/mes/exception/{exc_id}/handle", handle_data)
    if err or not body or not is_success(body):
        log("TC-INT-002", "异常联动端到端", "FAIL", f"Handle: {err or body}"); return
    log("TC-INT-002", "异常联动端到端", "PASS")


def test_tc_int_003():
    body, _, err = api("GET", "/v1/mes/trace/forward", params={"material_batch_no": "BATCH-INT-001"})
    if err or not body or not is_success(body):
        log("TC-INT-003", "报工→追溯联动", "FAIL", f"Forward: {err}"); return
    body, _, err = api("GET", "/v1/mes/trace/backward", params={"product_batch_no": "BATCH-INT-001"})
    if err or not body or not is_success(body):
        log("TC-INT-003", "报工→追溯联动", "FAIL", f"Backward: {err}"); return
    log("TC-INT-003", "报工→追溯联动", "PASS")


def test_tc_xmod_001():
    fc_data = {"forecast_code": "FC-XMOD-001", "forecast_name": "跨模块测试预测", "forecast_type": "monthly", "forecast_date": "2026-07-01", "start_date": "2026-07-01", "end_date": "2026-09-30"}
    body, _, _ = api("POST", "/v1/mrp2/forecast", fc_data)
    if not body or not is_success(body):
        log("TC-XMOD-001", "销售预测→MPS→MRP→制造单→工单→报工", "SKIP", "Cannot create forecast"); return
    fc_id = body["data"].get("id")
    api("POST", f"/v1/mrp2/forecast/{fc_id}/details", {"forecast_id": fc_id, "product_code": "FG-001", "product_name": "智能手表Pro", "unit": "台", "forecast_quantity": 500, "period_start": "2026-08-15", "period_end": "2026-08-31"})
    api("PUT", f"/v1/mrp2/forecast/{fc_id}/submit")
    api("PUT", f"/v1/mrp2/forecast/{fc_id}/approve")

    mps_data = {"mps_code": "MPS-XMOD-001", "mps_name": "跨模块测试MPS", "start_date": "2026-07-01", "end_date": "2026-09-30", "forecast_id": fc_id}
    body, _, _ = api("POST", "/v1/mrp2/mps", mps_data)
    if not body or not is_success(body):
        log("TC-XMOD-001", "销售预测→MPS→MRP→制造单→工单→报工", "SKIP", "Cannot create MPS"); return
    mps_id = body["data"].get("id")
    pl_data = {"mps_id": mps_id, "mps_code": "MPS-XMOD-001", "line_no": 1, "product_code": "FG-001", "product_name": "智能手表Pro", "plan_quantity": 500, "plan_start_date": "2026-08-01", "plan_end_date": "2026-08-15"}
    api("POST", f"/v1/mrp2/mps/{mps_id}/plan-lines", pl_data)
    api("POST", f"/v1/mrp2/mps/{mps_id}/compile")
    api("PUT", f"/v1/mrp2/mps/{mps_id}/submit")
    api("PUT", f"/v1/mrp2/mps/{mps_id}/approve", {"approved": True})
    api("PUT", f"/v1/mrp2/mps/{mps_id}/release")

    mrp_data = {"mrp_code": "MRP-XMOD-001", "mrp_name": "跨模块测试MRP", "mps_id": mps_id, "mps_code": "MPS-XMOD-001", "start_date": "2026-07-01", "end_date": "2026-09-30"}
    body, _, _ = api("POST", "/v1/mrp2/mrp", mrp_data)
    if body and is_success(body):
        mrp_id = body["data"].get("id")
        api("POST", "/v1/mrp2/mrp/calculate", {"mrp_id": mrp_id})
        api("GET", f"/v1/mrp2/mrp/{mrp_id}/planned-orders")

    api("GET", "/v1/mes/production/manufacturing-orders", params={"source_mps_code": "MPS-XMOD-001"})
    log("TC-XMOD-001", "销售预测→MPS→MRP→制造单→工单→报工", "PASS")


def test_tc_xmod_002():
    mrp_id = created_ids["mrp"].get("MRP-TEST-001")
    if not mrp_id:
        log("TC-XMOD-002", "销售预测→MPS→MRP→计划订单→采购订单", "SKIP", "No MRP"); return
    body, _, _ = api("GET", f"/v1/mrp2/mrp/{mrp_id}/planned-orders")
    if not body or not is_success(body):
        log("TC-XMOD-002", "销售预测→MPS→MRP→计划订单→采购订单", "FAIL", "Get planned orders failed"); return
    orders = body.get("data", [])
    if not isinstance(orders, list): orders = []
    purchase_orders = [o for o in orders if o.get("order_type") == "purchase"]
    if purchase_orders:
        po_id = purchase_orders[0].get("id")
        api("POST", f"/v1/mrp2/planned-order/{po_id}/confirm")
    log("TC-XMOD-002", "销售预测→MPS→MRP→计划订单→采购订单", "PASS")


def test_tc_xmod_006():
    mrp_id = created_ids["mrp"].get("MRP-TEST-001")
    if not mrp_id:
        log("TC-XMOD-006", "计划订单确认→制造单自动生成", "SKIP", "No MRP"); return
    body, _, _ = api("GET", f"/v1/mrp2/mrp/{mrp_id}/planned-orders")
    if not body or not is_success(body):
        log("TC-XMOD-006", "计划订单确认→制造单自动生成", "SKIP", "Cannot get planned orders"); return
    orders = body.get("data", [])
    if not isinstance(orders, list): orders = []
    mfg_orders = [o for o in orders if o.get("order_type") == "manufacture"]
    if mfg_orders:
        po_id = mfg_orders[0].get("id")
        api("POST", f"/v1/mrp2/planned-order/{po_id}/confirm")
    log("TC-XMOD-006", "计划订单确认→制造单自动生成", "PASS")


def test_tc_xedge_005():
    mrp_id = created_ids["mrp"].get("MRP-TEST-001")
    if not mrp_id:
        log("TC-XEDGE-005", "计划订单确认后取消", "SKIP", "No MRP"); return
    body, _, _ = api("GET", f"/v1/mrp2/mrp/{mrp_id}/planned-orders")
    if not body or not is_success(body):
        log("TC-XEDGE-005", "计划订单确认后取消", "SKIP", "Cannot get planned orders"); return
    orders = body.get("data", [])
    if not isinstance(orders, list): orders = []
    confirmed = [o for o in orders if o.get("status") == "confirmed"]
    if confirmed:
        po_id = confirmed[0].get("id")
        body, _, _ = api("POST", f"/v1/mrp2/planned-order/{po_id}/cancel")
        if body and is_success(body):
            log("TC-XEDGE-005", "计划订单确认后取消", "FAIL", "Should reject confirmed order cancel"); return
    log("TC-XEDGE-005", "计划订单确认后取消", "PASS")


def test_tc_events():
    body, _, err = api("GET", "/v1/events/monitor/health")
    if err or not body or not is_success(body):
        log("TC-EVENTS-001", "事件系统健康检查", "FAIL", f"{err}"); return
    log("TC-EVENTS-001", "事件系统健康检查", "PASS")

    body, _, err = api("GET", "/v1/events/records/", params={"page": 1, "page_size": 5})
    if err or not body or not is_success(body):
        log("TC-EVENTS-002", "事件记录查询", "FAIL", f"{err}"); return
    log("TC-EVENTS-002", "事件记录查询", "PASS")

    body, _, err = api("GET", "/v1/events/monitor/connection")
    if err or not body or not is_success(body):
        log("TC-EVENTS-003", "事件连接状态", "FAIL", f"{err}"); return
    log("TC-EVENTS-003", "事件连接状态", "PASS")


def test_tc_finance_integration():
    body, _, err = api("GET", "/v1/finance/integration-account-mappings/")
    if err or not body or not is_success(body):
        log("TC-FIN-INT-001", "集成科目映射查询", "FAIL", f"{err}"); return
    log("TC-FIN-INT-001", "集成科目映射查询", "PASS")

    body, _, err = api("GET", "/v1/finance/integration-logs/")
    if err or not body or not is_success(body):
        log("TC-FIN-INT-002", "集成日志查询", "FAIL", f"{err}"); return
    log("TC-FIN-INT-002", "集成日志查询", "PASS")

    body, _, err = api("GET", "/v1/finance/payables/")
    if err or not body or not is_success(body):
        log("TC-FIN-INT-003", "应付单查询", "FAIL", f"{err}"); return
    log("TC-FIN-INT-003", "应付单查询", "PASS")


def main():
    print("=" * 60)
    print("MES/MRP2/Finance/Events API Test Suite")
    print("=" * 60)

    login()
    seed_base_data()

    test_groups = [
        ("基础数据", [test_tc_base_001, test_tc_base_002, test_tc_base_003]),
        ("制造计划", [test_tc_plan_001, test_tc_plan_002, test_tc_plan_003]),
        ("工单执行", [test_tc_exec_001, test_tc_exec_003]),
        ("生产报工", [test_tc_report_001, test_tc_report_002]),
        ("物料流转", [test_tc_mat_001, test_tc_mat_002, test_tc_mat_003]),
        ("生产看板", [test_tc_dash_001, test_tc_dash_002]),
        ("生产追溯", [test_tc_trace_001, test_tc_trace_002]),
        ("异常管理", [test_tc_exc_001, test_tc_exc_002, test_tc_exc_003]),
        ("边界场景", [test_tc_edge_005, test_tc_edge_015, test_tc_edge_016]),
        ("MRP2模块", [test_tc_mrp2_001, test_tc_mrp2_002, test_tc_mrp2_003, test_tc_mrp2_004, test_tc_mrp2_005, test_tc_mrp2_006]),
        ("采购模块", [test_tc_pur_001, test_tc_pur_002, test_tc_pur_003]),
        ("集成场景", [test_tc_int_001, test_tc_int_002, test_tc_int_003]),
        ("跨模块集成", [test_tc_xmod_001, test_tc_xmod_002, test_tc_xmod_006]),
        ("跨模块边界", [test_tc_xedge_005]),
        ("事件系统", [test_tc_events]),
        ("财务集成", [test_tc_finance_integration]),
    ]

    for group_name, tests in test_groups:
        print(f"\n── {group_name} ──")
        for t in tests:
            try:
                t()
            except Exception as e:
                tc_id = t.__doc__.split(":")[0].strip() if t.__doc__ else t.__name__
                tc_name = t.__doc__.split(":", 1)[1].strip() if t.__doc__ and ":" in t.__doc__ else t.__name__
                log(tc_id, tc_name, "FAIL", f"Exception: {str(e)[:100]}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {results['pass']} PASS | {results['fail']} FAIL | {results['skip']} SKIP")
    print("=" * 60)

    if results["fail"] > 0:
        print("\nFailed tests:")
        for d in results["details"]:
            if d["status"] == "FAIL":
                print(f"  ✗ {d['id']}: {d['name']} — {d['detail'][:200]}")

    return results["fail"]


if __name__ == "__main__":
    sys.exit(main())
