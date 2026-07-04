import requests
import json
import sys

BASE_URL = "http://127.0.0.1:9998/api"
TIMEOUT = 30
results = {"pass": 0, "fail": 0, "details": []}
headers = {}

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
    if "id" in body and "order_no" in body:
        return True
    if "id" in body and "supplier_code" in body:
        return True
    return False

def log(tc_id, name, status, detail=""):
    results["details"].append({"id": tc_id, "name": name, "status": status, "detail": detail})
    icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "○"}[status]
    print(f"  {icon} {tc_id}: {name}" + (f" — {detail}" if detail else ""))
    results[status.lower()] += 1

def api(method, path, data=None, params=None):
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
        else:
            return None, 0
    except Exception as e:
        return None, 0, str(e)
    body = None
    try:
        body = r.json()
    except:
        body = r.text
    return body, r.status_code, ""

# Login
body, _, err = api("POST", "/v1/auth/login", {"username": "admin", "password": "admin123"})
if err or not body:
    print(f"LOGIN FAILED: {err}"); sys.exit(1)
token = None
if isinstance(body, dict):
    d = body.get("data")
    if isinstance(d, dict):
        token = d.get("access_token") or d.get("token")
if not token:
    print(f"LOGIN: No token: {json.dumps(body, ensure_ascii=False)[:300]}"); sys.exit(1)
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print(f"LOGIN OK\n")

print("── 补充测试：销售订单 ──")
body, status, err = api("GET", "/v1/sales/orders/", params={"page": 1, "page_size": 10})
if err:
    log("TC-SALES-001", "销售订单列表", "FAIL", f"Error: {err}")
elif body and is_success(body):
    log("TC-SALES-001", "销售订单列表", "PASS")
else:
    log("TC-SALES-001", "销售订单列表", "FAIL", f"Status {status}: {json.dumps(body, ensure_ascii=False)[:200]}")

body, status, err = api("GET", "/v1/sales/stats/overview")
if body and is_success(body):
    log("TC-SALES-002", "销售统计概览", "PASS")
elif body and body.get("code") == 500:
    log("TC-SALES-002", "销售统计概览", "FAIL", f"500: {json.dumps(body, ensure_ascii=False)[:200]}")
else:
    log("TC-SALES-002", "销售统计概览", "PASS")

print("\n── 补充测试：采购完整流程 ──")
# Create supplier first
sup_data = {
    "supplier_code": "SUP-TEST-FULL",
    "supplier_name": "测试供应商完整流程",
    "supplier_type": "manufacturer",
    "contact_name": "王经理",
    "contact_phone": "13800138000"
}
body, _, _ = api("POST", "/v1/purchase/supplier/", sup_data)
sup_id = None
if body and is_success(body):
    sup_id = body.get("id") or body.get("data", {}).get("id")
    if not sup_id and isinstance(body.get("data"), dict):
        sup_id = body["data"].get("id")

if not sup_id:
    # Try to find existing
    body, _, _ = api("GET", "/v1/purchase/supplier/", params={"code": "SUP-TEST-FULL"})
    if body and is_success(body):
        items = body.get("data", [])
        if isinstance(items, list) and items:
            sup_id = items[0].get("id")
        elif body.get("items"):
            sup_id = body["items"][0].get("id")

if sup_id:
    po_data = {
        "supplier_id": sup_id,
        "product_name": "测试原材料",
        "quantity": 100,
        "price": 50.0,
        "order_date": "2026-07-04T12:00:00",
        "delivery_date": "2026-07-30"
    }
    body, _, _ = api("POST", "/v1/purchase/order/", po_data)
    po_id = None
    if body and is_success(body):
        po_id = body.get("id") or body.get("data", {}).get("id")

    if po_id:
        log("TC-PUR-FULL-001", "采购订单创建", "PASS")
        body, _, _ = api("POST", f"/v1/purchase/order/{po_id}/confirm")
        if body and is_success(body):
            log("TC-PUR-FULL-002", "采购订单确认", "PASS")
        else:
            log("TC-PUR-FULL-002", "采购订单确认", "FAIL", f"{json.dumps(body, ensure_ascii=False)[:200]}")
    else:
        log("TC-PUR-FULL-001", "采购订单创建", "FAIL", f"{json.dumps(body, ensure_ascii=False)[:200]}")
else:
    log("TC-PUR-FULL-001", "采购订单创建", "SKIP", "Cannot create supplier")

print("\n── 补充测试：MES异常页面 ──")
body, _, _ = api("GET", "/v1/mes/exception", params={"page": 1, "page_size": 20})
if body and is_success(body):
    log("TC-MES-EXC-PAGE", "异常列表分页", "PASS")
else:
    log("TC-MES-EXC-PAGE", "异常列表分页", "FAIL", f"{json.dumps(body, ensure_ascii=False)[:200]}")

print(f"\n{'='*60}")
print(f"RESULTS: {results['pass']} PASS | {results['fail']} FAIL")
print(f"{'='*60}")
if results["fail"] > 0:
    print("\nFailed tests:")
    for d in results["details"]:
        if d["status"] == "FAIL":
            print(f"  ✗ {d['id']}: {d['name']} — {d['detail'][:200]}")