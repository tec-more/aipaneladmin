"""
BUG-T15-014 修复自测：cancel/resume 唤醒确认 + 保底自救 + 收尾互斥 + SSE 心跳帧

场景设计（真实 stream_events + 真实 RunControl/引擎链路，mock DB/配额/Trace）：
- D：HITL paused → cancel → ack 秒回（正常唤醒路径），cancelled 收尾 + 槽释放
- E：runner 卡死（永不 set ack）→ cancel 等 ack 5s 超时 → 保底强制收尾：
  cancelled 落库 + 槽释放 + control 清理；done_callback 互斥（release 仅 1 次）
- F：runner 卡死 → resume 等 ack 5s 超时 → 保底强制收尾 interrupted；返回 (False, interrupted)
- P：SSE_PING_INTERVAL_S patch 为 0.1s → 0.35s 内应收到 ≥2 个 ": ping" comment 帧
- 回归：场景 A/B/C（BUG-012/013 证据链）由 _t15_bug012_selfcheck.py 独立保持

运行: .venv/Scripts/python.exe tests/_t15_bug014_selfcheck.py
"""
import asyncio
import os
import sys
import time
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.common.quota.services.quota_service import QuotaService
from base.plugins.agent.services.execution_service import ExecutionService
from base.plugins.agent.services.trace_service import TraceService
from base.plugins.agent.services.engine import events as evt
from base.plugins.agent.services.engine.backend import InProcessBackend
import base.plugins.agent.services.execution_service as es_mod

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

release_calls = []
update_status_calls = []


async def fake_release_concurrency(owner):
    release_calls.append(("release", owner, round(time.monotonic(), 2)))


async def fake_heartbeat_concurrency(owner):
    pass


async def fake_quota_release(hold_id):
    pass


async def fake_update_status(execution_id, status, **kw):
    update_status_calls.append((execution_id, status, round(time.monotonic(), 2)))


class FakeWriter:
    async def emit(self, event_type, node_id, payload):
        return {"event_type": event_type, "node_id": node_id, "payload": payload, "seq": 1}


async def fake_create_writer(execution_id):
    return FakeWriter()


async def fake_close_writer(execution_id):
    pass


async def _fake_get(fake):
    return fake


async def fake_execute_stuck(self, ctx, graph, inputs, emit, control):
    """模拟 runner 卡死：emit RUN_STARTED 后永久挂起，不检查 cancel、不响应 resume、不 set ack"""
    await emit(evt.EventType.RUN_STARTED, None, {"execution_id": ctx.execution_id})
    await asyncio.sleep(3600)
    return {"status": "success", "tokens": {"in": 0, "out": 0}}


def make_ctx(exec_id):
    return SimpleNamespace(execution_id=exec_id, owner=("usr", 1), quota_hold_id=None,
                           version_id=1, settings={})


def make_fake_exec(status="paused"):
    return SimpleNamespace(status=status, owner_type="usr", owner_id=1)


async def scenario_D() -> bool:
    """正常唤醒：HITL paused → cancel → ack 秒回 → cancelled 收尾"""
    tag = "D 正常唤醒cancel"
    update_status_calls.clear(); release_calls.clear()
    ctx = make_ctx(9101)
    agen = ExecutionService.stream_events(ctx, GRAPH_HITL, {"query": "d"})
    async for f in agen:
        if "run_paused" in f:
            break
    await asyncio.sleep(0.2)
    fake_exec = make_fake_exec("paused")
    with patch.object(es_mod.WorkflowExecution, "get_or_none", lambda id: _fake_get(fake_exec)):
        t0 = time.monotonic()
        ret = await ExecutionService.cancel(9101)
        elapsed = time.monotonic() - t0
    await asyncio.sleep(0.5)
    woke = any(s == "cancelled" for _, s, _ in update_status_calls)
    ok = (ret == "cancelled" and elapsed < 2.0 and woke
          and len(release_calls) == 1 and 9101 not in ExecutionService._controls)
    print(f"[{tag}] ret={ret} elapsed={elapsed:.2f}s woke={woke} release={len(release_calls)} "
          f"controls={list(ExecutionService._controls.keys())} -> {'PASS' if ok else 'FAIL'}", flush=True)
    return ok


async def scenario_E() -> bool:
    """保底自救：runner 卡死 → cancel ack 超时(5s) → 强制收尾 cancelled + 互斥防双重释放"""
    tag = "E 卡死保底cancel"
    update_status_calls.clear(); release_calls.clear()
    with patch.object(InProcessBackend, "execute", fake_execute_stuck):
        ctx = make_ctx(9102)
        agen = ExecutionService.stream_events(ctx, GRAPH_HITL, {"query": "e"})
        async for f in agen:
            if "run_started" in f:
                break
        await asyncio.sleep(0.1)
        fake_exec = make_fake_exec("running")
        with patch.object(es_mod.WorkflowExecution, "get_or_none", lambda id: _fake_get(fake_exec)):
            t0 = time.monotonic()
            ret = await ExecutionService.cancel(9102)
            elapsed = time.monotonic() - t0
        await asyncio.sleep(1.0)  # 等 done_callback 竞态窗口
        woke = any(s == "cancelled" for _, s, _ in update_status_calls)
        ok = (ret == "cancelled" and 4.0 < elapsed < 7.0 and woke
              and len(release_calls) == 1 and 9102 not in ExecutionService._controls)
        print(f"[{tag}] ret={ret} elapsed={elapsed:.2f}s woke={woke} release={len(release_calls)} "
              f"(互斥期望=1) controls={list(ExecutionService._controls.keys())} "
              f"-> {'PASS' if ok else 'FAIL'}", flush=True)
        return ok


async def scenario_F() -> bool:
    """保底自救：runner 卡死(但 execution 为 paused) → resume ack 超时 → 强制收尾 interrupted"""
    tag = "F 卡死保底resume"
    update_status_calls.clear(); release_calls.clear()
    with patch.object(InProcessBackend, "execute", fake_execute_stuck):
        ctx = make_ctx(9103)
        agen = ExecutionService.stream_events(ctx, GRAPH_HITL, {"query": "f"})
        async for f in agen:
            if "run_started" in f:
                break
        await asyncio.sleep(0.1)
        fake_exec = make_fake_exec("paused")
        with patch.object(es_mod.WorkflowExecution, "get_or_none", lambda id: _fake_get(fake_exec)):
            t0 = time.monotonic()
            accepted, status = await ExecutionService.resume(9103, approved=True)
            elapsed = time.monotonic() - t0
        await asyncio.sleep(1.0)
        interrupted = any(s == "interrupted" for _, s, _ in update_status_calls)
        ok = (accepted is False and status == "interrupted" and 4.0 < elapsed < 7.0
              and interrupted and len(release_calls) == 1
              and 9103 not in ExecutionService._controls)
        print(f"[{tag}] accepted={accepted} status={status} elapsed={elapsed:.2f}s "
              f"interrupted={interrupted} release={len(release_calls)} "
              f"controls={list(ExecutionService._controls.keys())} -> {'PASS' if ok else 'FAIL'}",
              flush=True)
        return ok


async def scenario_P() -> bool:
    """SSE 心跳帧：ping 间隔 patch 0.1s → 0.35s 内 ≥2 个 comment 帧"""
    tag = "P SSE心跳帧"
    update_status_calls.clear(); release_calls.clear()
    with patch.object(es_mod, "SSE_PING_INTERVAL_S", 0.1):
        ctx = make_ctx(9104)
        agen = ExecutionService.stream_events(ctx, GRAPH_HITL, {"query": "p"})
        pings = 0
        got_paused = False
        t0 = time.monotonic()
        while time.monotonic() - t0 < 0.35:
            try:
                f = await asyncio.wait_for(agen.__anext__(), timeout=0.2)
            except asyncio.TimeoutError:
                break
            if "run_paused" in f:
                got_paused = True
            if f.startswith(": ping"):
                pings += 1
        # 清理
        control = ExecutionService._controls.get(9104)
        if control is not None and control.runner_task is not None:
            control.runner_task.cancel()
        await agen.aclose()
        await asyncio.sleep(0.3)
        ok = got_paused and pings >= 2
        print(f"[{tag}] got_paused={got_paused} pings={pings} (期望>=2) -> {'PASS' if ok else 'FAIL'}",
              flush=True)
        return ok


async def scenario_H() -> bool:
    """v2 断开自愈：aclose 模拟 SSE 断开 → finally 协作唤醒 runner（resume+request_cancel）
    → ExecutionCancelled 秒级收尾（v1 需等 5s 超时强杀）→ cancelled 落库 + 槽释放。
    同时验证 shield：aclose 完成后收尾状态已收敛（finalized 与收尾原子绑定）。"""
    tag = "H 断开协作自愈"
    update_status_calls.clear(); release_calls.clear()
    ctx = make_ctx(9105)
    agen = ExecutionService.stream_events(ctx, GRAPH_HITL, {"query": "h"})
    async for f in agen:
        if "run_paused" in f:
            break
    await asyncio.sleep(0.2)
    t0 = time.monotonic()
    await agen.aclose()  # 模拟 SSE 断开触发的 generator 关闭
    close_elapsed = time.monotonic() - t0
    await asyncio.sleep(0.5)  # 收尾收敛窗口
    woke = any(s == "cancelled" for _, s, _ in update_status_calls)
    ok = (woke and len(release_calls) == 1
          and 9105 not in ExecutionService._controls
          and close_elapsed < 3.0)  # v2 协作唤醒秒级；v1 需 ~5s 超时强杀
    print(f"[{tag}] aclose耗时={close_elapsed:.2f}s (v2协作唤醒期望<3s) woke={woke} "
          f"release={len(release_calls)} controls={list(ExecutionService._controls.keys())} "
          f"-> {'PASS' if ok else 'FAIL'}", flush=True)
    return ok


async def main():
    with ExitStack() as stack:
        for p in [
            patch.object(QuotaService, "release_concurrency", fake_release_concurrency),
            patch.object(QuotaService, "heartbeat_concurrency", fake_heartbeat_concurrency),
            patch.object(QuotaService, "quota_release", fake_quota_release),
            patch.object(TraceService, "create_writer", fake_create_writer),
            patch.object(TraceService, "close_writer", fake_close_writer),
            patch.object(ExecutionService, "_update_status", fake_update_status),
        ]:
            stack.enter_context(p)
        d = await scenario_D()
        e = await scenario_E()
        f_ = await scenario_F()
        p_ = await scenario_P()
        h = await scenario_H()
        print(f"\n===== BUG-014 自测汇总：D={'PASS' if d else 'FAIL'} E={'PASS' if e else 'FAIL'} "
              f"F={'PASS' if f_ else 'FAIL'} P={'PASS' if p_ else 'FAIL'} "
              f"H={'PASS' if h else 'FAIL'} =====", flush=True)
        if all([d, e, f_, p_, h]):
            print("PASS: 唤醒确认 + 保底自救 + 收尾互斥 + SSE 心跳帧 + 断开协作自愈 全部验证通过", flush=True)
        else:
            print("FAIL: 存在未通过场景", flush=True)
            sys.exit(1)


asyncio.run(main())
