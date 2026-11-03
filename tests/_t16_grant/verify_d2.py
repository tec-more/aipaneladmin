"""D2 复验：Redis 宕机快速降级 + 熔断 + 自愈
基线(up) → docker stop → 连续计时请求 → docker start → 冷却期降级 → 自愈确认
"""
import asyncio
import json
import subprocess
import time
import urllib.request

BASE = "http://127.0.0.1:9998/api/v1"
ADMIN = open(r"d:\programs\fastapi\aipaneladmin\tests\_t16_grant\token.txt", encoding="utf-8").read().strip()
REDIS_CONTAINER = "aipanel-redis-test"


def docker(*args):
    subprocess.run(["docker", *args], capture_output=True, timeout=60)


def redis_cli(*args):
    r = subprocess.run(["docker", "exec", REDIS_CONTAINER, "redis-cli", "-a", "Test@Redis123", *args],
                       capture_output=True, text=True, timeout=20)
    return r.stdout.strip()


def timed(path, token, timeout=30):
    t0 = time.time()
    try:
        req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {token}"})
        body = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        return round(time.time() - t0, 2), 200, body.get("success"), None
    except Exception as e:
        return round(time.time() - t0, 2), -1, None, str(e)[:80]


async def cus_token():
    import aiohttp
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{BASE}/customer/auth/login",
                          json={"email": "t16cusa@t.com", "password": "T16@Cus123"},
                          timeout=aiohttp.ClientTimeout(total=15)) as r:
            return (await r.json())["data"]["access_token"]


def show(tag, res):
    ms, st, ok, err = res
    print(f"  [{tag}] {ms}s status={st} success={ok} {err or ''}")


async def main():
    ctok = await cus_token()
    U = "/agent/u/resources?type=kb"
    A = "/agent/admin/grants/list"

    print("== 阶段1: Redis 正常基线 ==")
    redis_cli("DEL", "authz:org_ids:2")
    show("up u/resources#1", timed(U, ctok))   # MISS→DB→SET
    show("up u/resources#2", timed(U, ctok))   # HIT
    print("  org_ids缓存键:", redis_cli("KEYS", "authz:org_ids:2"))
    show("up grants/list", timed(A, ADMIN))

    print("== 阶段2: docker stop Redis ==")
    docker("stop", REDIS_CONTAINER)
    time.sleep(1)
    for i in range(1, 6):
        show(f"down u/resources#{i}", timed(U, ctok))
    show("down grants/list", timed(A, ADMIN))

    print("== 阶段3: docker start Redis，冷却期内仍应快速降级 ==")
    docker("start", REDIS_CONTAINER)
    time.sleep(2)
    show("cooldown u/resources", timed(U, ctok))

    print("== 阶段4: 冷却期(30s)过后自愈 ==")
    time.sleep(31)
    redis_cli("DEL", "authz:org_ids:2")
    show("heal u/resources#1", timed(U, ctok))
    show("heal u/resources#2", timed(U, ctok))
    print("  org_ids缓存键(自愈后应重建):", redis_cli("KEYS", "authz:org_ids:2"))
    show("heal grants/list", timed(A, ADMIN))


asyncio.run(main())
