import requests, json
r = requests.post('http://127.0.0.1:9998/api/v1/auth/login', json={'username':'admin','password':'admin123'})
token = r.json().get('data',{}).get('access_token')
headers = {'Authorization': f'Bearer {token}'}
r2 = requests.post('http://127.0.0.1:9998/api/v1/purchase/order/', json={'supplier_id':7,'product_name':'test2','quantity':1,'price':10,'order_date':'2026-07-04T12:00:00'}, headers=headers)
body = r2.json()
print(f"Status: {r2.status_code}")
print(f"Is dict: {isinstance(body, dict)}")
if isinstance(body, dict):
    print(f"Keys: {list(body.keys())}")
    print(f"Has 'code': {'code' in body}")
    print(f"code value: {body.get('code')}")
    print(f"Has 'id': {'id' in body}")
print(f"Body[:500]: {json.dumps(body, ensure_ascii=False)[:500]}")