"""
BUG-T15-013 修复后回归：C3b 失败根因裁决实验

背景：BUG-013 修复（RUN_PAUSED 落库后台 task 化）后，_t15_bug012_retest.py 第 1 轮
C3b FAIL：cancel_http=200 但 status 停留 paused、并发槽不释放、服务端无 _finalize 日志。
修复前（15:15/15:24 历史日志）同脚本 C3b 均 PASS。

对照设计（判别「cancel→resume 唤醒链路」vs「SSE 断开组合时序」）：
- 组 1【流内 cancel 对照】：保持 SSE 连接，收到 run_paused 帧后立即 cancel
  → 若 runner 被唤醒：状态快速收敛 cancelled，流内可见后续事件
- 组 2【断开后 cancel，C3 精确复现】：收到 run_paused → 等 paused 落库 → 断开 → cancel
  → 密集轮询（0.3s×100=30s）记录状态收敛精确时刻（覆盖 finally 5s 窗口 + 收尾）

判别口径：
- 组 1 PASS + 组 2 FAIL → 断开时序组合缺陷（_finalize_once 幂等短路 / control pop 竞态）
- 组 1 FAIL → cancel→resume 唤醒链路本身被修复破坏（更高级别阻断）

运行: .venv/Scripts/python.exe tests/_t15_bug013_repro.py
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

    async def status_of(eid):
        row = await WorkflowExecution.get_or_none(id=eid)
        return row.status if row else None

    async def poll_converge(eid, label, timeout=30.0, interval=0.3):
        """密集轮询至终态，返回 (收敛状态, 收敛耗时)"""
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            st = await status_of(eid)
            if st in ("success", "failed", "cancelled", "interrupted"):
                return st, time.monotonic() - t0
            await asyncio.sleep(interval)
        return await status_of(eid), timeout

    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
            # 预检槽位
            busy = await WorkflowExecution.filter(
                owner_type="usr", owner_id=1, status__in=["running", "paused"]).all()
            print(f"[预检] busy={[(e.id, e.status) for e in busy]}", flush=True)
            if busy:
                print("[预检中止] 槽位非空闲", flush=True)
                return

            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "BUG013裁决-HITL", "graph_json": GRAPH_HITL})
            wid = (r.json().get("data") or {}).get("id")
            created.append(wid)

            # ==================== 组 1：流内 cancel（不断开） ====================
            print("\n[G1] 流内 cancel：保持 SSE，run_paused 后立即 cancel ...", flush=True)
            g1_events = []
            t0 = time.monotonic()
            cancel_t = None
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "g1"}},
                                  timeout=60.0) as resp:
                eid1 = int(resp.headers.get("X-Execution-Id"))
                last_ev = None
                async for line in resp.aiter_lines():
                    if line.startswith("event:"):
                        last_ev = line[6:].strip()
                        g1_events.append((round(time.monotonic() - t0, 2), last_ev))
                    if last_ev == "run_paused" and cancel_t is None:
                        rc = await cli.post(f"/v1/agent/u/executions/{eid1}/cancel",
                                            headers=headers)
                        cancel_t = time.monotonic() - t0
                        print(f"    [G1] exec={eid1} cancel_http={rc.status_code} "
                              f"@t={cancel_t:.2f}s", flush=True)
                        # 继续读流，观察是否有后续帧（runner 唤醒证据）
                # 流自然结束（runner 收尾后 SSE 关闭）
            g1_dur = time.monotonic() - t0
            st1, conv1 = await poll_converge(eid1, "G1", timeout=10.0)
            print(f"    [G1] 流结束耗时={g1_dur:.2f}s 事件序列={g1_events}", flush=True)
            print(f"    [G1] 终态={st1} 收敛耗时(自信念起)={conv1:.2f}s", flush=True)
            g1_pass = st1 == "cancelled"
            print(f"[{'PASS' if g1_pass else 'FAIL'}] G1 流内 cancel → cancelled", flush=True)

            # 确保槽位归零再进组 2
            for _ in range(20):
                busy = await WorkflowExecution.filter(
                    owner_type="usr", owner_id=1, status__in=["running", "paused"]).count()
                if busy == 0:
                    break
                await asyncio.sleep(0.5)
            print(f"    [G1→G2] 槽位清零确认 busy={busy}", flush=True)

            # ==================== 组 2：断开后 cancel（C3 精确复现） ====================
            print("\n[G2] 断开后 cancel：run_paused 落库后断开 SSE，再 cancel ...", flush=True)
            t0 = time.monotonic()
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "g2"}},
                                  timeout=30.0) as resp:
                eid2 = int(resp.headers.get("X-Execution-Id"))
                last_ev = None
                async for line in resp.aiter_lines():
                    if line.startswith("event:"):
                        last_ev = line[6:].strip()
                    if last_ev == "run_paused":
                        break
                # 保持连接等 paused 落库（与 C3 一致）
                t_wait = time.monotonic()
                while time.monotonic() - t_wait < 5.0:
                    if await status_of(eid2) == "paused":
                        break
                    await asyncio.sleep(0.3)
                st_before_close = await status_of(eid2)
            t_disconnect = time.monotonic() - t0
            print(f"    [G2] exec={eid2} paused_落库={st_before_close} "
                  f"断开@t={t_disconnect:.2f}s", flush=True)
            await asyncio.sleep(0.5)
            rc = await cli.post(f"/v1/agent/u/executions/{eid2}/cancel", headers=headers)
            t_cancel = time.monotonic() - t0
            print(f"    [G2] cancel_http={rc.status_code} @t={t_cancel:.2f}s，密集轮询 30s ...",
                  flush=True)
            st2, conv2 = poll_from = await poll_converge(eid2, "G2", timeout=30.0, interval=0.3)
            print(f"    [G2] 终态={st2} 收敛耗时(自cancel起)={conv2:.2f}s", flush=True)
            g2_pass = st2 == "cancelled" and conv2 < 10.0
            print(f"[{'PASS' if g2_pass else 'FAIL'}] G2 断开后 cancel → cancelled"
                  f"（10s 内收敛）", flush=True)

            # 组 2 附加观测：槽位释放
            p = await cli.post(f"/v1/agent/u/workflows/{wid}/dry-run", headers=headers,
                               json={"inputs": {"query": "probe"}})
            print(f"    [G2] 末次探测槽位 http={p.status_code}"
                  f"（200=槽空闲，429=槽泄漏）", flush=True)
            try:
                p2 = await cli.post(f"/v1/agent/u/workflows/{wid}/dry-run",
                                    headers=headers, json={"inputs": {"query": "probe2"}})
                print(f"    [G2] 探测2 http={p2.status_code}", flush=True)
            except Exception:
                pass

            print("\n===== 裁决汇总 =====", flush=True)
            print(f"G1 流内 cancel : {'PASS' if g1_pass else 'FAIL'} (终态={st1})", flush=True)
            print(f"G2 断开 cancel : {'PASS' if g2_pass else 'FAIL'} "
                  f"(终态={st2}, 收敛={conv2:.2f}s)", flush=True)
    finally:
        async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as cli:
            for w in created:
                if w:
                    try:
                        await cli.delete(f"/v1/agent/u/workflows/{w}", headers=headers)
                    except Exception:
                        pass
        await Tortoise.close_connections()
        print("\n[清理完成]", flush=True)


asyncio.run(main())
