"""诊断：HITL dry-run 读 run_paused 后【保持连接不断开】，高频轮询 status 8s。
区分：(a) 脚本连接管理 bug 致提前断开；(b) v2 服务端 HITL 自动 cancelled。
对齐 v1 C3：在 async with 块内 break + 轮询（连接保持）。"""
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


async def main():
    from base.common.database import TORTOISE_ORM
    await Tortoise.init(config=TORTOISE_ORM)
    from base.plugins.agent.models.workflow import WorkflowExecution
    headers = {"Authorization": f"Bearer {create_access_token({'typ':'usr','sub':'1'}, expires_delta=timedelta(hours=2))}"}
    wid = None
    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "DIAG-HITL", "graph_json": GRAPH_HITL})
            wid = (r.json().get("data") or {}).get("id")
            print(f"wid={wid}", flush=True)

            # 对齐 v1 C3：async with 块内读 run_paused break，保持连接，块内轮询
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "diag"}},
                                  timeout=30.0) as resp:
                eid = int(resp.headers.get("X-Execution-Id"))
                events = []
                last_ev = None
                async for line in resp.aiter_lines():
                    if line.startswith("event:"):
                        last_ev = line[6:].strip()
                        events.append(last_ev)
                    if last_ev == "run_paused":
                        break
                print(f"exec={eid} 收到事件序列={events}", flush=True)
                print("保持连接（async with 块内），0.05s 高频轮询 status 8s ...", flush=True)
                t0 = time.monotonic()
                prev = None
                while time.monotonic() - t0 < 8.0:
                    row = await WorkflowExecution.get_or_none(id=eid)
                    st = row.status if row else None
                    if st != prev:
                        print(f"  t={round(time.monotonic()-t0,3)}s status: {prev} -> {st}",
                              flush=True)
                        prev = st
                    if st in ("cancelled", "interrupted", "failed", "success"):
                        print(f"  [结论] 连接保持下 status 收敛到 {st}（自动取消=服务端bug）",
                              flush=True)
                        break
                    await asyncio.sleep(0.05)
                else:
                    print(f"  [结论] 8s 内 status 稳定 = {prev}（未自动取消，连接保持正常）",
                          flush=True)
            # 出 async with 块才断开
            print("出 async with 块（现在才断开）", flush=True)
            await asyncio.sleep(1.0)
            row = await WorkflowExecution.get_or_none(id=eid)
            print(f"断开 1s 后 status={row.status if row else None}", flush=True)
            # 清理：cancel 防持槽
            try:
                rc = await cli.post(f"/v1/agent/u/executions/{eid}/cancel", headers=headers)
                print(f"清理 cancel http={rc.status_code}", flush=True)
            except Exception as e:
                print(f"清理 cancel 异常: {e}", flush=True)
            await asyncio.sleep(1.0)
    finally:
        if wid:
            async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as cli:
                try:
                    await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=headers)
                except Exception:
                    pass
        await Tortoise.close_connections()


asyncio.run(main())
