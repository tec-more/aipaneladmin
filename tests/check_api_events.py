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
print(f"Total via API: {total}")
for e in events["data"]:
    name = e["event_name"]
    status = e["status"]
    pub = e.get("published_at", "N/A")
    print(f"  {name}: status={status}, published_at={pub}")

# Check the latest event
r2 = client.get(BASE + "/api/v1/events/records/?page=1&page_size=1")
data2 = r2.json()
events2 = data2.get("data", data2)
if events2["data"]:
    latest = events2["data"][0]
    print(f"\nLatest event: {json.dumps(latest, ensure_ascii=False, default=str)[:500]}")