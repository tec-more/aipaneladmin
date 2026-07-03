import httpx
import json

BASE = "http://127.0.0.1:9998"
client = httpx.Client(timeout=30)
r = client.post(BASE + "/api/v1/auth/login", json={"username": "admin", "password": "admin"})
token = r.json()["data"]["access_token"]
client.headers["Authorization"] = "Bearer " + token

# Get a specific event by UUID to verify
r = client.get(BASE + "/api/v1/events/records/?page=1&page_size=1")
data = r.json()
events = data.get("data", data)
if events["data"]:
    uuid = events["data"][0]["event_uuid"]
    print(f"Trying to get event by UUID: {uuid}")
    r2 = client.get(BASE + f"/api/v1/events/records/{uuid}")
    print(f"Status: {r2.status_code}")
    print(f"Body: {r2.text[:300]}")