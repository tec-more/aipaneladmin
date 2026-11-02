"""
BUG-T15-012 复测：SSE 中断并发槽泄漏修复验证（_finalize_once 幂等 + runner done_callback 兜底）

修复点（execution_service.py stream_events 重构）：
- _finalize_once（finalized 标记幂等）：heartbeat.cancel + _finalize（状态落库/配额释放/槽释放）
- runner 改为 return result（经 task 传递）
- runner task done_callback：SSE 中断致 generator finally 未执行时兜底触发 _finalize_once

复测矩阵：
- C0 预检：usr:1 无 running/paused 实例（槽位空闲基线）
- C1 基线防回归：完整消费 → 槽释放（正常路径 generator finally 触发，done_callback 幂等不重复释放）
- C2 核心修复断言：流式读 1 帧断开（不 aclose，模拟用户关闭浏览器）
  → runner 完成后 done_callback 兜底 → DB status=success（非 running 僵尸）→ 再 dry-run 200（不 429）
- C3 paused 语义断言：HITL 暂停中断开 → 槽保持（429，设计语义）→ cancel 解除
  → status=cancelled 且槽释放（再 dry-run 200）；C3 的 429 同时间接验证释放不过冲（计数精确为 0）

运行: .venv/Scripts/python.exe tests/_t15_bug012_retest.py
"""
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from tortoise import Tortoise

from base.common.security import create_access_token

BASE = "http://127.0.0.1:9998"

RESULTS: list[dict] = []


def record(case_id: str, name: str, passed: bool, detail: str):
    RESULTS.append({"id": case_id, "name": name, "pass": passed, "detail": detail})
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {case_id} {name} :: {detail}", flush=True)


def make_token() -> str:
    return create_access_token({"typ": "usr", "sub": "1"}, expires_delta=timedelta(hours=2))


GRAPH_FAST = {
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

    headers = {"Authorization": f"Bearer {make_token()}"}
    created = []

    async def exec_row(exec_id):
        return await WorkflowExecution.get_or_none(id=exec_id)

    async def wait_status(exec_id, targets, timeout=15.0):
        for _ in range(int(timeout / 0.5)):
            row = await exec_row(exec_id)
            if row and row.status in targets:
                return row
            await asyncio.sleep(0.5)
        return await exec_row(exec_id)

    try:
        # ---- C0 预检
        busy = await WorkflowExecution.filter(
            owner_type="usr", owner_id=1, status__in=["running", "paused"]).all()
        record("C0", "预检：usr:1 无 running/paused 实例（槽位空闲）",
               len(busy) == 0, f"busy={[e.id for e in busy]}")
        if busy:
            print("[预检中止] 请先重启服务清槽", flush=True)
            return

        async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "BUG012复测-快速图", "graph_json": GRAPH_FAST})
            wid_fast = (r.json().get("data") or {}).get("id")
            created.append(wid_fast)
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "BUG012复测-HITL图", "graph_json": GRAPH_HITL})
            wid_hitl = (r.json().get("data") or {}).get("id")
            created.append(wid_hitl)

            async def probe(tag, wid=wid_fast) -> int:
                """探测槽位：完整消费一次 dry-run，返回状态码"""
                async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                      headers=headers, json={"inputs": {"query": "probe"}},
                                      timeout=30.0) as resp:
                    code = resp.status_code
                    if code == 200:
                        async for _ in resp.aiter_lines():
                            pass
                    else:
                        body = (await resp.aread()).decode("utf-8", "replace")[:160]
                        print(f"    [{tag}] 探测: {code} body={body}", flush=True)
                        return code
                print(f"    [{tag}] 探测: {code}（槽位空闲）", flush=True)
                return code

            # ---- C1 基线：完整消费 → 释放
            print("\n[C1] 基线：流式完整消费 dry-run ...", flush=True)
            exec_id_c1 = None
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid_fast}/dry-run",
                                  headers=headers, json={"inputs": {"query": "c1"}},
                                  timeout=30.0) as resp:
                exec_id_c1 = resp.headers.get("X-Execution-Id")
                async for _ in resp.aiter_lines():
                    pass
            await asyncio.sleep(1.0)
            row1 = await exec_row(exec_id_c1)
            p1 = await probe("C1")
            record("C1", "基线防回归：完整消费后状态落库且槽释放（正常路径幂等）",
                   p1 == 200 and row1 is not None and row1.status == "success",
                   f"probe={p1} exec_status={row1.status if row1 else None}")

            # ---- C2 核心：读 1 帧断开 → done_callback 兜底
            print("\n[C2] 流式读 1 帧后断开（模拟用户关闭浏览器）...", flush=True)
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid_fast}/dry-run",
                                  headers=headers, json={"inputs": {"query": "c2"}},
                                  timeout=30.0) as resp:
                assert resp.status_code == 200, f"C2 初次执行被拒: {resp.status_code}"
                exec_id_c2 = resp.headers.get("X-Execution-Id")
                async for _ in resp.aiter_lines():
                    break  # 读一帧即断开
            print(f"    [C2] 已断开 execution_id={exec_id_c2}，轮询等待 done_callback 兜底 ...",
                  flush=True)
            row2 = await wait_status(exec_id_c2, {"success", "failed", "cancelled"}, timeout=15.0)
            zombie = row2 is not None and row2.status in ("running", "paused")
            p2 = await probe("C2")
            record("C2a", "SSE 中断后 runner 完成 done_callback 兜底：终态落库，不留 running 僵尸",
                   row2 is not None and not zombie and row2.completed_at is not None,
                   f"status={row2.status if row2 else None} "
                   f"completed_at={row2.completed_at if row2 else None}")
            record("C2b", "SSE 中断后并发槽已释放：再 dry-run 不再 429",
                   p2 == 200, f"probe={p2}")

            # ---- C3 paused 语义：paused 落库后断开 → 持槽(429) → cancel 解除
            # （注意：断开时机须待 paused 落库完成，runner 进入 resume_event.wait 后，
            #   cancel 才能唤醒；「读帧即断」的竞速窗口另案 BUG-T15-013 回流开发）
            print("\n[C3] HITL run_paused 落库后断开（设计语义：paused 持槽）...", flush=True)
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid_hitl}/dry-run",
                                  headers=headers, json={"inputs": {"query": "c3"}},
                                  timeout=30.0) as resp:
                assert resp.status_code == 200, f"C3 初次执行被拒: {resp.status_code}"
                exec_id_c3 = resp.headers.get("X-Execution-Id")
                last_ev = None
                async for line in resp.aiter_lines():
                    if line.startswith("event:"):
                        last_ev = line[6:].strip()
                    if last_ev == "run_paused":
                        break
                # 保持连接，轮询等待 emit(RUN_PAUSED) 内 _update_status(paused) 落库完成
                row_wait = await wait_status(exec_id_c3, {"paused"}, timeout=5.0)
            await asyncio.sleep(0.5)
            row3a = await exec_row(exec_id_c3)
            p3 = await probe("C3-持槽")
            record("C3a", "SSE 中断于 HITL paused（落库后）：执行保持 paused 且槽占用（设计语义，非泄漏）",
                   row_wait is not None and row_wait.status == "paused"
                   and p3 == 429 and row3a is not None and row3a.status == "paused",
                   f"paused_落库={row_wait.status if row_wait else None} probe={p3} "
                   f"status={row3a.status if row3a else None}")

            print("    [C3] 调用 cancel 解除 paused 持槽 ...", flush=True)
            rc = await cli.post(f"/v1/agent/u/executions/{exec_id_c3}/cancel", headers=headers)
            row3b = await wait_status(exec_id_c3, {"cancelled"}, timeout=15.0)
            p3b = await probe("C3-解除")
            record("C3b", "cancel 解除 paused 持槽：状态 cancelled 且并发槽释放（可自救，非永久泄漏）",
                   rc.status_code == 200 and row3b is not None
                   and row3b.status == "cancelled" and p3b == 200,
                   f"cancel_http={rc.status_code} status={row3b.status if row3b else None} "
                   f"probe={p3b}")
    finally:
        async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as cli:
            for wid in created:
                if wid:
                    try:
                        await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=headers)
                    except Exception:
                        pass
        await Tortoise.close_connections()
        print("\n[清理完成]", flush=True)

    print("\n===== BUG-T15-012 复测汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")
    if passed == len(RESULTS):
        print("结论: BUG-T15-012 修复有效——SSE 中断不再泄漏并发槽/留 running 僵尸；"
              "paused 持槽为设计语义且可经 cancel 解除")


asyncio.run(main())
