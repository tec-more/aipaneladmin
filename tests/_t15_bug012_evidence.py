"""
BUG-T15-012 补强取证：中途断开后执行记录僵尸状态（running 悬置）+ 槽位泄漏确认
"""
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from tortoise import Tortoise

from base.common.database import TORTOISE_ORM
from base.common.security import create_access_token

BASE = "http://127.0.0.1:9998"

GRAPH = {
    "schema_version": 2,
    "nodes": [
        {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
         "data": {"outputs": [{"name": "query", "type": "string"}]}},
        {"id": "e1", "type": "end", "position": {"x": 300, "y": 0},
         "data": {"inputs": [{"name": "answer", "type": "string", "from": "s1.query"}]}},
    ],
    "edges": [{"id": "e1", "source": "s1", "target": "e1",
               "sourceHandle": "out", "targetHandle": "in"}],
    "variables": [],
}


async def main():
    headers = {"Authorization": "Bearer " + create_access_token(
        {"typ": "usr", "sub": "1"}, expires_delta=timedelta(hours=2))}
    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
        # 清理同名残留靶场
        rl = await cli.get("/v1/agent/u/workflows", headers=headers, params={"page_size": 100})
        for it in ((rl.json().get("data") or {}).get("items") or []):
            if "BUG012" in (it.get("name") or ""):
                await cli.delete("/v1/agent/u/workflows/" + str(it["id"]), headers=headers)

        r = await cli.post("/v1/agent/u/workflows", headers=headers,
                           json={"name": "BUG012取证2", "graph_json": GRAPH})
        wid = r.json()["data"]["id"]

        async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                              headers=headers, json={"inputs": {"query": "zombie"}}) as resp:
            eid = resp.headers.get("X-Execution-Id")
            print("dry-run http:", resp.status_code, "execution_id:", eid, flush=True)
            async for _ in resp.aiter_lines():
                break  # 读一帧即断开（模拟用户关闭页面）

        await asyncio.sleep(3)
        await Tortoise.init(config=TORTOISE_ORM)
        from base.plugins.agent.models.workflow import WorkflowExecution
        ex = await WorkflowExecution.get_or_none(id=int(eid))
        print("3s 后执行记录: status =", ex.status, "| completed_at =", ex.completed_at, flush=True)

        rl2 = await cli.get("/v1/agent/u/executions", headers=headers,
                            params={"workflow_id": wid})
        print("执行列表视角:", json.dumps(rl2.json().get("data"), ensure_ascii=False,
                                        default=str)[:300], flush=True)

        rp = await cli.post(f"/v1/agent/u/workflows/{wid}/dry-run", headers=headers,
                            json={"inputs": {"query": "probe"}})
        print("同用户再次 dry-run:", rp.status_code,
              rp.text[:150] if rp.status_code != 200 else "(SSE 正常)", flush=True)

        await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=headers)
        await Tortoise.close_connections()
        print("[清理完成]", flush=True)


asyncio.run(main())
