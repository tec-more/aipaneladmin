"""
审批模块端到端测试（判定下沉到 Service 层，基于 BaseBusinessService 基类）。

验证点：
 1. /approval/rules/check 按 model 参数匹配（核心逻辑保留）
 2. 规则列表返回 model 字段
 3. POST /purchase/order 由 BaseBusinessService.create() 内置门禁拦截 -> 400 + code 40001
    （不再依赖中间件或装饰器：基类自动查 approval_rule 表决定是否需要审批）
 4. 拦截响应携带自动创建的 instance_id（证明门禁已在 service 内建单）
 5. 创建审批实例（非阻断，兼容性）

注意：请求必须先通过 Pydantic 校验才能到达 service 触发门禁，
因此测试 payload 必须是合法的采购订单结构（含真实存在的 supplier_id）。
"""
import requests

BASE = "http://127.0.0.1:9998"
API = "/api/v1"  # 运行时若失败回退 /v1


def login():
    for prefix in ["/api/v1", "/v1"]:
        try:
            r = requests.post(
                f"{BASE}{prefix}/auth/login",
                json={"username": "admin", "password": "admin123"},
                timeout=10,
            )
            if r.status_code == 200:
                body = r.json()
                data = body.get("data", {}) if isinstance(body.get("data"), dict) else {}
                token = data.get("access_token") or body.get("access_token")
                if token:
                    print(f"[登录] 成功 via {prefix}")
                    return prefix, token
        except Exception as e:
            print(f"[登录] {prefix} 失败: {e}")
    return None, None


def ensure_supplier(headers):
    """确保存在一个可用供应商，返回其 id（优先复用第一个，否则新建）。"""
    try:
        r = requests.get(f"{BASE}{API}/purchase/supplier",
                         params={"page": 1, "page_size": 1}, headers=headers, timeout=10)
        items = r.json().get("data", {}).get("items", [])
        if items:
            return items[0]["id"]
    except Exception:
        pass
    try:
        r = requests.post(f"{BASE}{API}/purchase/supplier",
                          json={"supplier_name": "审批测试供应商"}, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {})
            return data.get("id")
    except Exception as e:
        print(f"[供应商] 创建失败: {e}")
    return None


def main():
    global API
    prefix, token = login()
    assert token, "登录失败，请确认 admin 用户存在"
    API = prefix
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 按模型检查（核心逻辑）
    r = requests.post(
        f"{BASE}{API}/approval/rules/check",
        params={"model": "purchase_order", "method": "POST"},
        headers=headers, timeout=10,
    )
    assert r.status_code == 200, f"check 状态码异常: {r.status_code}"
    body = r.json()
    print(f"[1] /rules/check?model=purchase_order -> {body}")
    assert body.get("data", {}).get("require_approval") is True, "按模型应需要审批"
    assert body.get("data", {}).get("model") == "purchase_order"

    # 2. 规则列表含 model 字段
    r = requests.get(
        f"{BASE}{API}/approval/rules",
        params={"page": 1, "page_size": 10},
        headers=headers, timeout=10,
    )
    items = r.json().get("data", {}).get("items", [])
    print(f"[2] 规则列表: {[(i.get('id'), i.get('model')) for i in items]}")
    assert any(i.get("model") == "purchase_order" for i in items), "规则应包含 model=purchase_order"

    # 准备合法供应商 id（service 门禁需要能通过 Pydantic 校验）
    supplier_id = ensure_supplier(headers)
    assert supplier_id, "无法获取/创建供应商，无法构造合法采购单"
    payload = {
        "supplier_id": supplier_id,
        "items": [{"product_name": "审批测试商品", "quantity": 1, "unit_price": 100}],
    }

    # 3. Service 层门禁拦截（无中间件）
    r = requests.post(
        f"{BASE}{API}/purchase/order",
        json=payload,
        headers=headers, timeout=10,
    )
    print(f"[3] Service 门禁拦截 POST /purchase/order -> {r.status_code} {r.text[:300]}")
    assert r.status_code == 400 and r.json().get("code") == 40001, "应被 service 门禁拦截返回 40001"
    assert r.json().get("model") == "purchase_order", "响应应携带 model"
    assert r.json().get("instance_id"), "响应应携带自动创建的 instance_id"
    instance_id = r.json().get("instance_id")
    print(f"    -> 自动创建审批实例 instance_id={instance_id}")

    # 4. 创建审批实例（非阻断，兼容性）
    try:
        r = requests.post(
            f"{BASE}{API}/approval/instances",
            json={
                "business_type": "purchase_order",
                "title": "测试采购审批",
                "applicant_id": 1,
                "business_data": {"amount": 100},
            },
            headers=headers, timeout=10,
        )
        print(f"[4] 创建实例 -> {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"[4] 创建实例异常(非阻断): {e}")

    print("\n✅ 方案A：Service 层审批门禁验证通过")
    print("   审批通过后由 ApprovalExecutor 自动回调 PurchaseOrderService 落库，")
    print("   可在 /approval/center 审批该实例验证自动执行。")


if __name__ == "__main__":
    main()
