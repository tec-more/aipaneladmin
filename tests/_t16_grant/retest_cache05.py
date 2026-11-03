"""CACHE-05 复测：Redis 宕机降级（拉长等待与超时，多次采样）"""
import asyncio
import os
import subprocess
import sys
import time

import aiohttp

BASE = "http://127.0.0.1:9998/api"
TOK = open(os.path.join(os.path.dirname(__file__), "token.txt")).read().strip()


async def login_cus(session):
    async with session.post(f"{BASE}/v1/customer/auth/login",
                            json={"email": "t16cusa@t.com", "password": "T16@Cus123"},
                            timeout=aiohttp.ClientTimeout(total=20)) as r:
        d = await r.json()
        return d["data"]["access_token"]


async def hit(session, tok, timeout=60):
    t0 = time.time()
    try:
        async with session.get(f"{BASE}/v1/agent/u/resources", params={"type": "kb"},
                               headers={"Authorization": f"Bearer {tok}"},
                               timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            return r.status, (time.time() - t0)
    except Exception as e:
        return f"ERR:{type(e).__name__}", (time.time() - t0)


async def main():
    async with aiohttp.ClientSession() as s:
        tok = await login_cus(s)
        print("baseline:", await hit(s, tok))
        subprocess.run(["docker", "stop", "aipanel-redis-test"], capture_output=True, timeout=40)
        time.sleep(3)
        results = []
        for i in range(3):
            results.append(await hit(s, tok))
            time.sleep(1)
        print("redis-down samples:", results)
        subprocess.run(["docker", "start", "aipanel-redis-test"], capture_output=True, timeout=40)
        time.sleep(3)
        print("recovered:", await hit(s, tok))
        ok = all(r[0] == 200 for r in results)
        print(f"CACHE-05-RETEST {'PASS' if ok else 'FAIL'}")


asyncio.run(main())
