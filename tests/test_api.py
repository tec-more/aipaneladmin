import time
import urllib.request

time.sleep(10)

try:
    response = urllib.request.urlopen('http://localhost:9998/v1/product/attributes')
    data = response.read().decode('utf-8')
    print('API Response:')
    print(data)
except Exception as e:
    print(f'Error: {e}')