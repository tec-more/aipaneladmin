"""审计补充验证：UPDATE(刷新过期)是否捕获 + CREATE重复捕获确认"""
import asyncio
import os
import sys
import time

import aiohttp
import asyncpg

BASE = "http://127.0.0.1:9998/api"
GRANTS = f"{BASE}/v1/agent/admin/grants"
TOK = open(os.path.join(os.path.dirname(__file__), "token.txt")).read().strip()
H = {"Content-Type": "application/json", "Authorization": f"Bearer {TOK}"}

DSN = dict(host="127.0.0.1", port=15432, user="admin", password="Admin@123", database="aipaneladmin", timeout=10)


async def q(sql, *args):
    conn = await asyncpg.connect(**DSN)
    try:
        return await conn.fetch(sql, *args)
    finally:
        await conn.close()


async def main():
    async with aiohttp.ClientSession() as s:
        async def req(method, url, body=None):
            async with s.request(method, url, json=body, headers=H,
                                 timeout=aiohttp.ClientTimeout(total=20)) as r:
                return r.status, await r.json()

        body = {"owner_type": "usr", "owner_id": 2, "resource_type": "node_type", "resource_id": "sub_agent"}
        await req("DELETE", GRANTS, body)
        await q("DELETE FROM data_change_log WHERE table_name='resource_grant'")
        await q("DELETE FROM resource_grant WHERE owner_type='usr' AND owner_id=2 AND resource_type='node_type' AND resource_id='sub_agent'")

        # 1) CREATE
        await req("POST", GRANTS, {**body, "expires_at": "2030-01-01T00:00:00"})
        time.sleep(1.5)
        rows1 = await q("SELECT id, change_type, record_id, changed_fields FROM data_change_log WHERE table_name='resource_grant' ORDER BY id")
        print("after CREATE:", [(r["id"], r["change_type"], r["record_id"]) for r in rows1])

        # 2) UPDATE（刷新过期时间）
        await req("POST", GRANTS, {**body, "expires_at": "2031-01-01T00:00:00"})
        time.sleep(1.5)
        rows2 = await q("SELECT id, change_type, record_id, changed_fields FROM data_change_log WHERE table_name='resource_grant' ORDER BY id")
        print("after UPDATE:", [(r["id"], r["change_type"], r["record_id"], r["changed_fields"]) for r in rows2])

        # 3) DELETE（Q6）
        await req("DELETE", GRANTS, body)
        time.sleep(1.5)
        rows3 = await q("SELECT id, change_type, record_id FROM data_change_log WHERE table_name='resource_grant' ORDER BY id")
        print("after DELETE:", [(r["id"], r["change_type"], r["record_id"]) for r in rows3])
        has_delete = any(r["change_type"] == "DELETE" for r in rows3)
        print("Q6 verdict: revoke DELETE captured =", has_delete)


asyncio.run(main())
