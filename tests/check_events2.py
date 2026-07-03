import httpx
import json

BASE = "http://127.0.0.1:9998"
client = httpx.Client(timeout=30)
r = client.post(BASE + "/api/v1/auth/login", json={"username": "admin", "password": "admin"})
token = r.json()["data"]["access_token"]
client.headers["Authorization"] = "Bearer " + token

r = client.get(BASE + "/api/v1/events/records/?page=1&page_size=3")
data = r.json()
events = data.get("data", data)
total = events["total"]
print(f"Total event records: {total}")
for e in events["data"]:
    name = e["event_name"]
    status = e["status"]
    print(f"  {name}: {status}")

# Check if model.created for event_records still exists
r2 = client.get(BASE + "/api/v1/events/records/?page=1&page_size=100")
data2 = r2.json()
events2 = data2.get("data", data2)
model_created_for_events = [e for e in events2["data"] if e["event_name"] == "model.created"]
print(f"model.created events: {len(model_created_for_events)}")
if model_created_for_events:
    for e in model_created_for_events[:3]:
        payload = e.get("payload", {})
        table = payload.get("table_name", "unknown")
        print(f"  model.created for table: {table}")