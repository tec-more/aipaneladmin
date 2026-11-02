"""
BUG-T15-012 / BUG-T15-013 修复自测

进程内直调 stream_events（mock 引擎/配额/Trace），验证三场景：
- 场景 A（正常路径）：完整消费 SSE generator，finally 触发收尾，release_concurrency 调 1 次
- 场景 B（SSE 中断，BUG-012）：取首帧后保持引用不 aclose（finally 不执行），runner 完成后
  done_callback 兜底触发 _finalize_once → release_concurrency 仍被调用
- 场景 C（HITL paused + DB 挂起，BUG-013）：mock _update_status 对 paused 挂起 30s，验证
  emit(RUN_PAUSED) 后台化后 runner 不被落库卡死（elapsed < 2s），HITL 超时推进 + 收尾正常

溯源：BUG-012 generator finally 不执行致槽泄漏；BUG-013 runner 卡死于 emit 内 paused 落库挂起（race）。
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
from base.plugins.agent.services.engine import events as evt
from base.plugins.agent.services.engine.backend import InProcessBackend
from base.plugins.agent.services.execution_service import ExecutionService
from base.plugins.agent.services.trace_service import TraceService

release_calls = []


async def fake_release_concurrency(owner):
    release_calls.append(owner)


async def fake_heartbeat_concurrency(owner):
    pass


async def fake_quota_release(hold_id):
    pass


class FakeWriter:
    async def emit(self, event_type, node_id, payload):
        return {"event_type": event_type, "node_id": node_id, "payload": payload, "seq": 1}


async def fake_create_writer(execution_id):
    return FakeWriter()


async def fake_close_writer(execution_id):
    pass


async def fake_execute(self, ctx, graph, inputs, emit, control):
    await emit("node_started", "n1", {})
    await asyncio.sleep(0.05)
    return {"status": "success", "outputs": {"answer": "ok"}, "tokens": {"in": 1, "out": 1}}


async def fake_execute_hitl(self, ctx, graph, inputs, emit, control):
    # 触发 RUN_PAUSED（修复后后台化落库，runner 不阻塞），随后模拟 HITL resume 等待超时推进
    await emit(evt.EventType.RUN_PAUSED, "hitl1", {})
    await asyncio.sleep(0.2)
    return {"status": "interrupted", "outputs": {}, "tokens": {"in": 0, "out": 0},
            "error": {"code": "HITL_TIMEOUT", "message": "HITL 审批超时"}}


async def selective_hang_update_status(execution_id, status, **kw):
    # 仅 paused 落库模拟 DB 间歇挂起（> wait_for 10s 超时）；终态直接返回（无 DB 环境，落库非验证点）
    if status == "paused":
        await asyncio.sleep(30)


def make_ctx(eid):
    return SimpleNamespace(execution_id=eid, owner=("usr", 1), quota_hold_id=None)


async def scenario_normal():
    ctx = make_ctx(9001)
    frames = []
    async for f in ExecutionService.stream_events(ctx, {}, {}):
        frames.append(f)
    return len(frames)


async def scenario_interrupt(holder):
    ctx = make_ctx(9002)
    agen = ExecutionService.stream_events(ctx, {}, {})
    first = await agen.__anext__()
    holder.append(agen)  # 保持引用阻止 GC 触发 finally（模拟 StreamingResponse 持有未关闭）
    await asyncio.sleep(0.4)
    return first


async def scenario_hitl_db_hang():
    ctx = make_ctx(9003)
    start = time.monotonic()
    frames = []
    async for f in ExecutionService.stream_events(ctx, {}, {}):
        frames.append(f)
    return len(frames), time.monotonic() - start


def base_patches():
    return [
        patch.object(QuotaService, "release_concurrency", fake_release_concurrency),
        patch.object(QuotaService, "heartbeat_concurrency", fake_heartbeat_concurrency),
        patch.object(QuotaService, "quota_release", fake_quota_release),
        patch.object(TraceService, "create_writer", fake_create_writer),
        patch.object(TraceService, "close_writer", fake_close_writer),
    ]


async def main():
    holder = []
    # 场景 A/B：BUG-012（不 patch _update_status；无 DB 终态落库走 _finalize try-catch 兜底）
    with ExitStack() as stack:
        for p in base_patches():
            stack.enter_context(p)
        stack.enter_context(patch.object(InProcessBackend, "execute", fake_execute))
        n_normal = await scenario_normal()
        r_after_normal = len(release_calls)
        first = await scenario_interrupt(holder)
        await asyncio.sleep(0.2)
        r_after_interrupt = len(release_calls)

    # 场景 C：BUG-013（patch _update_status 使 paused 挂起；HITL 执行）
    with ExitStack() as stack:
        for p in base_patches():
            stack.enter_context(p)
        stack.enter_context(patch.object(InProcessBackend, "execute", fake_execute_hitl))
        stack.enter_context(patch.object(ExecutionService, "_update_status", selective_hang_update_status))
        n_c, elapsed_c = await scenario_hitl_db_hang()
        r_after_c = len(release_calls)

    print(f"[A] normal        : frames={n_normal}, release={r_after_normal}")
    print(f"[B] interrupt     : first={'ok' if first else 'none'}, release_total={r_after_interrupt}")
    print(f"[C] hitl+db_hang  : frames={n_c}, elapsed={elapsed_c:.2f}s, release_total={r_after_c}")

    assert r_after_normal == 1, f"场景A release 应为1，实际 {r_after_normal}"
    assert r_after_interrupt == 2, f"场景B done_callback 兜底 release 累计应为2，实际 {r_after_interrupt}"
    # 场景 C 核心断言：runner 不被 paused 落库(30s 挂起)卡死，HITL 0.2s 超时推进完成
    assert elapsed_c < 2.0, (
        f"场景C runner 被 paused 落库卡死（elapsed={elapsed_c:.1f}s ≥2s），BUG-013 未修复"
    )
    assert r_after_c == 3, f"场景C 收尾 release 累计应为3，实际 {r_after_c}"
    print("PASS: BUG-012 done_callback 兜底 + BUG-013 HITL paused 后台化防卡死 均验证通过")


if __name__ == "__main__":
    asyncio.run(main())
