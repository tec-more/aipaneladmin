"""
BUG-T15-013 实验 Y：断开后不 cancel，短超时观察 runner 自主推进

判别目标：
- HITL timeout_s=8 + timeout_action=fail，SSE 断开后不调用 cancel
- 若 ~8s 后 runner 自主超时推进（HitlTimeout → run_failed → _finalize 落库 interrupted/failed
  + 槽释放 + 收尾日志）→ runner/loop 活着 → cancel 唤不醒 = resume_event 失配（control 对象错位）
- 若 20s 内无任何动静 → runner 整体死/卡（loop/transport 级问题，与 cancel 无关）

运行: .venv/Scripts/python.exe tests/_t15_bug013_expY.py
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

GRAPH_HITL_T8 = {
    "schema_version": 2,
    "nodes": [
        {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
         "data": {"outputs": [{"name": "query", "type": "string"}]}},
        {"id": "h1", "type": "hitl", "position": {"x": 200, "y": 0},
         "data": {"config": {"timeout_s": 8, "timeout_action": "fail"},
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
                               json={"name": "BUG013实验Y", "graph_json": GRAPH_HITL_T8})
            wid = (r.json().get("data") or {}).get("id")
            created.append(wid)

            t0 = time.monotonic()
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "y"}},
                                  timeout=30.0) as resp:
                print(f"[Y] dry-run http={resp.status_code} "
                      f"hdrs={dict(resp.headers)}", flush=True)
                if resp.status_code != 200:
                    body = (await resp.aread()).decode("utf-8", "replace")[:400]
                    print(f"[Y] dry-run 拒绝 body={body}", flush=True)
                    return
                eid = int(resp.headers.get("X-Execution-Id"))
                last_ev = None
                async for line in resp.aiter_lines():
                    if line.startswith("event:"):
                        last_ev = line[6:].strip()
                    if last_ev == "run_paused":
                        break
            print(f"[Y] exec={eid} 收到 run_paused 即断开 @t={time.monotonic()-t0:.2f}s，"
                  f"不 cancel，观察 20s（timeout_s=8 应自主超时推进）", flush=True)

            timeline = []
            while time.monotonic() - t0 < 22.0:
                row = await WorkflowExecution.get_or_none(id=eid)
                st = row.status if row else None
                el = round(time.monotonic() - t0, 1)
                if not timeline or timeline[-1][1] != st:
                    timeline.append((el, st))
                    print(f"    [Y] t={el}s status={st}", flush=True)
                if st in ("failed", "interrupted", "cancelled", "success"):
                    break
                await asyncio.sleep(0.5)
            print(f"[Y] 状态时间线: {timeline}", flush=True)

            # 槽位观测
            await asyncio.sleep(1.0)
            p = await cli.post(f"/v1/agent/u/workflows/{wid}/dry-run", headers=headers,
                               json={"inputs": {"query": "probe"}})
            print(f"[Y] 槽位探测 http={p.status_code}（200=已释放，429=仍占用）", flush=True)
            try:
                await cli.post(f"/v1/agent/u/workflows/{wid}/dry-run", headers=headers,
                               json={"inputs": {"query": "probe2"}})
            except Exception:
                pass

            auto = any(s in ("failed", "interrupted", "cancelled") for _, s in timeline[1:])
            print(f"\n[裁决] runner 断开后自主超时推进: {'YES（runner 活着，'
                  f'cancel 唤醒失效=control 失配）' if auto else 'NO（runner 死/卡，'
                  f'loop/transport 级问题）'}", flush=True)
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
