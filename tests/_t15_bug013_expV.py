"""
BUG-T15-013 实验 V：断开后调 resume API（而非 cancel）—— control 死控裁决

resume 与 cancel 同路径（_controls.get → control.resume(payload)），判别：
- resume 唤醒成功（runner 推进 → success 收尾 → 日志+落库+槽释放）
  → cancel 特有 bug（与 resume 分叉点排查）
- resume 同样无效（无日志/无落库/paused 不变）
  → 断开后 control 成「死控」石锤：_controls 表内对象与 runner 实际等待的 control 失配，
    或 runner 所在 task 已被事件循环隔离

运行: .venv/Scripts/python.exe tests/_t15_bug013_expV.py
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

    try:
        busy = await WorkflowExecution.filter(
            owner_type="usr", owner_id=1, status__in=["running", "paused"]).all()
        print(f"[预检] busy={[(e.id, e.status) for e in busy]}", flush=True)
        if busy:
            print("[中止] 槽位非空闲", flush=True)
            return

        async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "BUG013实验V", "graph_json": GRAPH_HITL})
            wid = (r.json().get("data") or {}).get("id")
            created.append(wid)

            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "v"}},
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
                    row = await WorkflowExecution.get_or_none(id=eid)
                    if row and row.status == "paused":
                        break
                    await asyncio.sleep(0.3)
            print(f"[V] exec={eid} paused 落库后断开 SSE", flush=True)

            await asyncio.sleep(0.5)
            rv = await cli.post(f"/v1/agent/u/executions/{eid}/resume", headers=headers,
                                json={"approved": True, "comment": "实验V"})
            print(f"[V] resume http={rv.status_code} 响应体={rv.json()}", flush=True)

            t0 = time.monotonic()
            timeline = []
            while time.monotonic() - t0 < 15.0:
                row = await WorkflowExecution.get_or_none(id=eid)
                st = row.status if row else None
                el = round(time.monotonic() - t0, 1)
                if not timeline or timeline[-1][1] != st:
                    timeline.append((el, st))
                    print(f"    [V] t={el}s status={st}", flush=True)
                if st in ("success", "failed", "cancelled", "interrupted"):
                    break
                await asyncio.sleep(0.5)
            print(f"[V] 状态时间线: {timeline}", flush=True)
            woke = any(s in ("success", "failed") for _, s in timeline[1:])
            print(f"\n[裁决] resume 断开唤醒: {'YES（control 有效→cancel 特有 bug）' if woke else 'NO（死控石锤：断开后 _controls 对象与 runner 失配）'}", flush=True)
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
