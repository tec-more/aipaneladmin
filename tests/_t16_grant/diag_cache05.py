"""D2 诊断：复现“池化连接黑洞”并逐段计时（Redis 先连后停）
步骤：连接Redis(池预热) → docker stop → 逐段计时 is_rate_limited / _customer_org_ids / check_many
"""
import asyncio
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tortoise import Tortoise
from base.common.setting import get_model_list


async def seg(name, coro):
    t0 = time.time()
    try:
        r = await coro
        print(f"  [{name}] {time.time()-t0:.2f}s -> {str(r)[:80]}")
    except Exception as e:
        print(f"  [{name}] {time.time()-t0:.2f}s EXC {type(e).__name__}: {e}")


async def main():
    await Tortoise.init(db_url="postgres://admin:Admin@123@127.0.0.1:15432/aipaneladmin",
                        modules={"models": get_model_list()})
    from base.common.cache import RedisCache
    from base.common.authz import audit as audit_mod
    from base.common.authz.service import ResourceGrantService, _customer_org_ids

    # 1) Redis up：建立连接并预热连接池
    cache = await RedisCache.get_instance()
    print("ping:", await cache._client.ping())
    await cache.set("diag:warm", "1", expire=60)
    print("warm get:", await cache.get("diag:warm"))

    # 2) 停容器（制造死连接）
    subprocess.run(["docker", "stop", "aipanel-redis-test"], capture_output=True, timeout=40)
    time.sleep(2)
    print("--- redis stopped, begin segments ---")

    await seg("raw client.exists", cache._client.exists("rl:authz404:block:cus:2"))
    await seg("is_rate_limited", audit_mod.is_rate_limited("cus:2"))
    await seg("_customer_org_ids", _customer_org_ids(2))
    await seg("check_many", ResourceGrantService.check_many(("cus", 2), "kb", ["22", "21"]))
    await seg("list_by_subject", ResourceGrantService.list_by_subject(("cus", 2), "kb"))

    # 3) 恢复
    subprocess.run(["docker", "start", "aipanel-redis-test"], capture_output=True, timeout=40)
    time.sleep(3)
    print("--- redis restarted ---")
    await seg("post-recover get", cache.get("diag:warm"))
    await seg("post-recover org_ids", _customer_org_ids(2))
    await Tortoise.close_connections()


asyncio.run(main())
