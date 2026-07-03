import httpx
import json
import time

BASE = "http://127.0.0.1:9998"
client = httpx.Client(timeout=30)

r = client.post(f"{BASE}/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
assert r.status_code == 200, f"Login failed: {r.text}"
token = r.json()["data"]["access_token"]
client.headers["Authorization"] = f"Bearer {token}"
print("1. Login OK")

r = client.post(f"{BASE}/v1/purchase/order/", json={
    "supplier_id": 1,
    "order_date": "2026-07-03",
    "items": [{"product_name": "Test Material", "quantity": 100, "unit_price": 10.0}]
})
assert r.status_code == 200, f"Create PO failed: {r.text}"
po_resp = r.json()
po_data = po_resp.get("data", po_resp)
po_id = po_data["id"]
print(f"2. Purchase Order created: id={po_id}, order_no={po_data.get('order_no')}")

r = client.post(f"{BASE}/v1/purchase/order/{po_id}/confirm")
assert r.status_code == 200, f"Confirm PO failed: {r.text}"
print("3. Purchase Order confirmed")

time.sleep(1)
r = client.get(f"{BASE}/v1/finance/integration-logs/?page=1&page_size=10")
assert r.status_code == 200, f"Get logs failed: {r.text}"
logs_resp = r.json()
logs = logs_resp.get("data", logs_resp)
print(f"4. Integration logs: total={logs['total']}")
for log in logs["data"][-3:]:
    print(f"   - {log['event_name']}: {log['result']} (payable_id={log.get('payable_id')})")

r = client.get(f"{BASE}/api/v1/events/records/?page=1&page_size=5")
assert r.status_code == 200, f"Get events failed: {r.text}"
events_resp = r.json()
events = events_resp.get("data", events_resp)
print(f"5. Event records: total={events['total']}")
for evt in events["data"][:3:]:
    print(f"   - {evt['event_name']}: status={evt.get('status')}")

r = client.get(f"{BASE}/api/v1/events/monitor/health")
assert r.status_code == 200, f"Health check failed: {r.text}"
health = r.json()["data"]
print(f"6. Event system health: {json.dumps(health, ensure_ascii=False)}")

r = client.get(f"{BASE}/v1/finance/integration-account-mappings/?page=1&page_size=20")
assert r.status_code == 200, f"Get mappings failed: {r.text}"
mappings_resp = r.json()
mappings = mappings_resp.get("data", mappings_resp)
print(f"7. Account mappings: total={mappings['total']}")
for m in mappings["data"]:
    print(f"   - {m['event_type']}: {m['debit_account_code']}/{m['credit_account_code']} active={m['is_active']}")

r = client.get(f"{BASE}/api/v1/events/records/statistics")
assert r.status_code == 200, f"Statistics failed: {r.text}"
stats = r.json()["data"]
print(f"8. Event statistics: {json.dumps(stats, ensure_ascii=False)}")

r = client.get(f"{BASE}/api/v1/events/monitor/connection")
assert r.status_code == 200, f"Connection status failed: {r.text}"
conn_status = r.json()["data"]
print(f"9. RabbitMQ connection: {json.dumps(conn_status, ensure_ascii=False)}")

r = client.get(f"{BASE}/api/v1/events/monitor/queues")
assert r.status_code == 200, f"Queue metrics failed: {r.text}"
queues = r.json()["data"]
print(f"10. Queue metrics: {json.dumps(queues, ensure_ascii=False)}")

print()
print("=== ALL 10 TESTS PASSED ===")
