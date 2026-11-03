"""FUNC-04 / FUNC-17 复测（修正断言与方法）"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import aiohttp

BASE = "http://127.0.0.1:9998/api"
GRANTS = f"{BASE}/v1/agent/admin/grants"
HERE = os.path.dirname(__file__)
TOK = open(os.path.join(HERE, "token.txt")).read().strip()
H = {"Content-Type": "application/json", "Authorization": f"Bearer {TOK}"}
CUS_C = 4


async def db(sql):
    import asyncpg
    conn = await asyncpg.connect(host="127.0.0.1", port=15432, user="admin",
                                 password="Admin@123", database="aipaneladmin", timeout=10)
    try:
        return await conn.fetch(sql)
    finally:
        await conn.close()


async def req(session, method, url, body=None, params=None):
    async with session.request(method, url, json=body, params=params, headers=H,
                               timeout=aiohttp.ClientTimeout(total=20)) as r:
        return r.status, await r.json()


async def main():
    async with aiohttp.ClientSession() as s:
        # --- FUNC-04 复测：比较重复授权前后 expires_at 是否不变（UTC 存储语义）---
        await req(s, "DELETE", GRANTS, body={"owner_type": "cus", "owner_id": CUS_C,
                                             "resource_type": "node_type", "resource_id": "hitl"})
        await req(s, "POST", GRANTS, body={"owner_type": "cus", "owner_id": CUS_C,
                                           "resource_type": "node_type", "resource_id": "hitl",
                                           "expires_at": "2030-01-01T00:00:00"})
        r1 = await db(f"SELECT expires_at FROM resource_grant WHERE owner_type='cus' AND owner_id={CUS_C} "
                      f"AND resource_type='node_type' AND resource_id='hitl'")
        exp1 = r1[0]["expires_at"] if r1 else None
        st, d = await req(s, "POST", GRANTS, body={"owner_type": "cus", "owner_id": CUS_C,
                                                   "resource_type": "node_type", "resource_id": "hitl"})
        r2 = await db(f"SELECT expires_at FROM resource_grant WHERE owner_type='cus' AND owner_id={CUS_C} "
                      f"AND resource_type='node_type' AND resource_id='hitl'")
        exp2 = r2[0]["expires_at"] if r2 else None
        ok = exp1 is not None and exp1 == exp2
        print(f"[FUNC] FUNC-04-RETEST {'PASS' if ok else 'FAIL'} | Q4保持原过期时间 | "
              f"首次={exp1} 重复后={exp2} (UTC存储, 2030-01-01 00:00 +08:00 语义不变={ok})")
        # 同时验证响应中 created 语义：单条 grant 无 created 标志，仅batch有 —— 记录
        print(f"  注: 单条POST响应体={json.dumps(d.get('data'), default=str)[:200]}")
        await req(s, "DELETE", GRANTS, body={"owner_type": "cus", "owner_id": CUS_C,
                                             "resource_type": "node_type", "resource_id": "hitl"})

        # --- FUNC-17 复测：改用 resource_type 过滤定位 ghost_node 记录 ---
        await db("DELETE FROM resource_grant WHERE owner_type='cus' AND owner_id=999 AND resource_id='ghost_node'")
        await db("INSERT INTO resource_grant (owner_type, owner_id, resource_type, resource_id, effect, "
                 "granted_by, created_at, updated_at) VALUES ('cus', 999, 'node_type', 'ghost_node', 'allow', "
                 "'admin:1', NOW(), NOW())")
        st, d = await req(s, "GET", f"{GRANTS}/list", params={"resource_type": "node_type", "page_size": 100})
        ghost = [i for i in d["data"]["items"] if i["resource_id"] == "ghost_node"]
        flag = ghost[0]["resource_deleted"] if ghost else None
        label = ghost[0]["resource_label"] if ghost else None
        print(f"[FUNC] FUNC-17-RETEST {'PASS' if flag is True else 'FAIL'} | §6.2资源已删除标注 | "
              f"resource_deleted={flag}, label={label}")
        # 附带观察：keyword=ghost_node 查不到该记录（关键词仅匹配存在的资源名/主体名）——设计行为观察
        st2, d2 = await req(s, "GET", f"{GRANTS}/list", params={"keyword": "ghost_node"})
        print(f"  观察: keyword='ghost_node' 命中 total={d2['data']['total']}"
              f"（关键词搜索基于现存资源元数据，已删除资源记录无法按名称关键词检索——仅能按resource_type筛选追溯）")
        await db("DELETE FROM resource_grant WHERE owner_type='cus' AND owner_id=999 AND resource_id='ghost_node'")


asyncio.run(main())
