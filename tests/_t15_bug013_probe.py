"""
BUG-T15-013 C3b 根因探针：G2 场景 cancel 响应体 + execution 存在性验证

G2 已证实失败（cancel 200 但无唤醒/无落库/无日志）。本探针回答：
1. cancel 响应体 status 字段：cancelled（走了分支）vs not_found（get_or_none 返回 None）
2. cancel 前后 exec 在 DB 中的存在性与状态
3. cancel 后长轮询（40s）捕捉任何延迟收尾

运行: .venv/Scripts/python.exe tests/_t15_bug013_probe.py
"""
import asyncio
import sys
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from tortoise import Tortoise

from base.common.security import create_access_token

BASE = "http://127.0.0.1:9998"

GRAPH_HITL = {
    "schema_version": 2,
    "nodes": [
        {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
         "data": {"outputs": [{"name": "query", "type": "string"}]}},
        {"id": "h1", "type": "hitl", "position": {"x": 200, "y": 0},
         "data": {"config": {"timeout_minutes": 5, "on_timeout": "approve"},
                  "inputs": [{"name": "context", "type": "string", "from": "s1.query"}],
                  "outputs": [{"name": "approved", "type": "boolean"}]}},
        {"id": "e1", "type": "end", "position": {"x": 400, "y": 0}, "data": {"inputs": []}},
    ],
    "edges": [
        {"id": "e1", "source": "s1", "target": "h1", "sourceHandle": "out", "targetHandle": "in"},
        {"id": "e2", "source": "h1", "target": "e1", "sourceHandle": "out", "targetHandle": "in"},
    ],
    "variables": [],
}


def make_token() -> str:
    return create_access_token({"typ": "usr", "sub": "1"}, expires_delta=timedelta(hours=2))


async def main():
    from base.common.database import TORTOISE_ORM
    await Tortoise.init(config=TORTOISE_ORM)
    from base.plugins.agent.models.workflow import WorkflowExecution

    headers = {"Authorization": f"Bearer {make_token()}"}
    created = []

    async def row_of(eid):
        return await WorkflowExecution.get_or_none(id=eid)

    try:
        busy = await WorkflowExecution.filter(
            owner_type="usr", owner_id=1, status__in=["running", "paused"]).all()
        print(f"[预检] busy={[(e.id, e.status) for e in busy]}", flush=True)
        if busy:
            print("[中止] 槽位非空闲，需重启服务", flush=True)
            return

        async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "BUG013探针", "graph_json": GRAPH_HITL})
            wid = (r.json().get("data") or {}).get("id")
            created.append(wid)

            print("[P] dry-run HITL，等 run_paused + paused 落库后断开 ...", flush=True)
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "p"}},
                                  timeout=30.0) as resp:
                eid = int(resp.headers.get("X-Execution-Id"))
                last_ev = None
                async for line in resp.aiter_lines():
                    if line.startswith("event:"):
                        last_ev = line[6:].strip()
                    if last_ev == "run_paused":
                        break
                t_wait = time.monotonic()
                while time.monotonic() - t_wait < 5.0:
                    row = await row_of(eid)
                    if row and row.status == "paused":
                        break
                    await asyncio.sleep(0.3)
                row_pre = await row_of(eid)
            print(f"[P] exec={eid} 断开前 DB: exists={row_pre is not None} "
                  f"status={row_pre.status if row_pre else None}", flush=True)

            await asyncio.sleep(0.5)
            row_mid = await row_of(eid)
            print(f"[P] cancel 前 DB: exists={row_mid is not None} "
                  f"status={row_mid.status if row_mid else None}", flush=True)

            rc = await cli.post(f"/v1/agent/u/executions/{eid}/cancel", headers=headers)
            body = rc.json()
            print(f"[P] cancel http={rc.status_code} 响应体={body}", flush=True)

            row_post = await row_of(eid)
            print(f"[P] cancel 后即时 DB: exists={row_post is not None} "
                  f"status={row_post.status if row_post else None}", flush=True)

            # 40s 长轮询
            t0 = time.monotonic()
            final = None
            while time.monotonic() - t0 < 40.0:
                row = await row_of(eid)
                st = row.status if row else None
                if st != "paused":
                    final = (st, round(time.monotonic() - t0, 1))
                    break
                await asyncio.sleep(1.0)
            print(f"[P] 40s 轮询结果: {final or ('仍 paused', 40)}", flush=True)
    finally:
        async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as cli:
            for w in created:
                if w:
                    try:
                        await cli.delete(f"/v1/agent/u/workflows/{w}", headers=headers)
                    except Exception:
                        pass
        await Tortoise.close_connections()
        print("[清理完成]", flush=True)


asyncio.run(main())
