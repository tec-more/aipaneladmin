import httpx

BASE = "http://127.0.0.1:9998"
client = httpx.Client(timeout=30)
r = client.post(BASE + "/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
token = r.json()["data"]["access_token"]
client.headers["Authorization"] = "Bearer " + token

r = client.get(BASE + "/v1/finance/integration-logs/?page=1&page_size=5")
data = r.json().get("data", r.json())
for log in data["data"]:
    name = log["event_name"]
    result = log["result"]
    error = log.get("error_message", "N/A")
    pid = log.get("payable_id", "N/A")
    print(f"  {name}: {result}, error={error}, payable_id={pid}")

# Check event records for recursion
r2 = client.get(BASE + "/api/v1/events/records/?page=1&page_size=5")
data2 = r2.json().get("data", r2.json())
total = data2["total"]
print(f"\nTotal event records: {total}")

# Check model.created for event_records
r3 = client.get(BASE + "/api/v1/events/records/statistics?group_by=event_name")
stats = r3.json().get("data", r3.json())
print(f"Event breakdown: {stats}")