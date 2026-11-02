"""诊断2：HITL dry-run【持续读 SSE 不 break】+ 并发 0.05s 轮询 status 16s。
- 若持续读时 status 稳定 paused → 证明之前 cancelled 是 break 关闭连接所致（连接管理问题）
- 若持续读也自动 cancelled → v2 服务端 bug
同时记录完整 SSE 事件序列（含 : ping）。"""
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
                               json={"name": "DIAG2-HITL", "graph_json": GRAPH_HITL})
            wid = (r.json().get("data") or {}).get("id")
            print(f"wid={wid}", flush=True)

            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "diag2"}},
                                  timeout=30.0) as resp:
                eid = int(resp.headers.get("X-Execution-Id"))
                events = []
                stop = asyncio.Event()

                async def read_sse():
                    try:
                        async for line in resp.aiter_lines():   # 持续读，不 break
                            if stop.is_set():
                                return
                            if line.startswith("event:"):
                                events.append(line[6:].strip())
                            elif line.strip() == ": ping":
                                events.append(":ping")
                    except Exception as e:
                        events.append(f"<reader_exc:{type(e).__name__}>")

                reader = asyncio.create_task(read_sse())
                print(f"exec={eid} 持续读 SSE（不 break）+ 轮询 status 16s ...", flush=True)
                t0 = time.monotonic()
                prev = None
                auto_cancel = False
                while time.monotonic() - t0 < 16.0:
                    row = await WorkflowExecution.get_or_none(id=eid)
                    st = row.status if row else None
                    if st != prev:
                        print(f"  t={round(time.monotonic()-t0,3)}s status: {prev} -> {st}",
                              flush=True)
                        prev = st
                    if st in ("cancelled", "interrupted", "failed", "success"):
                        print(f"  [判定] 持续读不break下 status 仍收敛到 {st} → 服务端自动取消",
                              flush=True)
                        auto_cancel = True
                        break
                    await asyncio.sleep(0.05)
                if not auto_cancel:
                    print(f"  [判定] 16s 持续读不break，status 稳定 = {prev} → HITL 正常停留", flush=True)
                stop.set()
                reader.cancel()
                print(f"  SSE 事件序列={events}", flush=True)
            # 出块断开 + 清理
            await asyncio.sleep(1.0)
            row = await WorkflowExecution.get_or_none(id=eid)
            print(f"断开后 status={row.status if row else None}", flush=True)
            try:
                await cli.post(f"/v1/agent/u/executions/{eid}/cancel", headers=headers)
            except Exception:
                pass
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
