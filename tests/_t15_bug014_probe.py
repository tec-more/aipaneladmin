"""
BUG-T15-014 根因判别实验：「generator 悬挂 + cancel」能否唤醒 HITL 等待中的 runner

背景：C3b（SSE 断开后 cancel）真实环境 4/4 必现失败；但 sim 脚本（aclose + 窗口内 cancel）通过。
两者差异：sim 里 aclose 触发了 generator finally 的 request_cancel；真实场景 uvicorn 未感知断开，
generator 悬挂在 queue.get()，finally 未执行，唤醒完全依赖 cancel API 的 resume_event.set()。

实验场景（真实 stream_events + 真实 InProcessBackend + GRAPH_HITL，mock DB/配额/Trace）：
- H1：消费至 run_paused → 保持 agen 引用不 aclose（模拟 uvicorn 悬挂）→ 同 task 直接 cancel
- H2：同上，但 cancel 在独立 task 中调用（模拟 HTTP 请求 handler task 与 runner task 跨 task 唤醒）

判别：
- runner 唤醒（落库 cancelled + 槽释放）→ 唤醒链路代码级无缺陷，根因在服务端传输层/进程/时序
- runner 未唤醒 → 代码级确定性缺陷，精确定位断点

运行: .venv/Scripts/python.exe tests/_t15_bug014_probe.py
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


async def run_scenario(tag: str, exec_id: int, cancel_in_separate_task: bool) -> bool:
    """返回 runner 是否被唤醒收尾（cancelled 落库 + 槽释放）"""
    update_status_calls.clear()
    release_calls.clear()
    ctx = SimpleNamespace(execution_id=exec_id, owner=("usr", 1), quota_hold_id=None,
                          version_id=1, settings={})
    agen = ExecutionService.stream_events(ctx, GRAPH_HITL, {"query": "probe"})
    got_paused = False
    async for f in agen:
        if "run_paused" in f:
            got_paused = True
            break
    assert got_paused, f"[{tag}] 未收到 run_paused"
    await asyncio.sleep(0.2)  # 后台 paused 落库 task 完成
    print(f"[{tag}] run_paused 已收到，generator 保持悬挂（不 aclose）", flush=True)
    print(f"[{tag}] _controls={list(ExecutionService._controls.keys())}", flush=True)

    fake_exec = SimpleNamespace(status="paused")
    with patch.object(es_mod.WorkflowExecution, "get_or_none",
                      lambda id: _fake_get(fake_exec)):
        t0 = time.monotonic()
        if cancel_in_separate_task:
            # 模拟 HTTP handler：独立 task 中执行 cancel（跨 task Event.set 唤醒）
            ret = await asyncio.create_task(ExecutionService.cancel(exec_id))
        else:
            ret = await ExecutionService.cancel(exec_id)
        print(f"[{tag}] cancel 返回={ret} 耗时={time.monotonic()-t0:.3f}s", flush=True)

    await asyncio.sleep(2.0)  # 观测窗口
    woke = any(s == "cancelled" for _, s, _ in update_status_calls)
    released = len(release_calls) >= 1
    print(f"[{tag}] update_status_calls={update_status_calls}", flush=True)
    print(f"[{tag}] release_calls={release_calls}", flush=True)
    print(f"[{tag}] 判定: runner唤醒={woke}, 槽释放={released}", flush=True)
    # 清理：若 runner 未醒，强制关闭 generator 触发 finally 兜底，防 task 泄漏影响后续场景
    if not woke:
        await agen.aclose()
        await asyncio.sleep(0.5)
    return woke and released


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

        h1 = await run_scenario("H1 同task cancel", 8801, cancel_in_separate_task=False)
        h2 = await run_scenario("H2 独立task cancel", 8802, cancel_in_separate_task=True)

        print(f"\n===== 总结：H1(同task)={'PASS' if h1 else 'FAIL'}, "
              f"H2(独立task)={'PASS' if h2 else 'FAIL'} =====", flush=True)
        if h1 and h2:
            print("结论：唤醒链路代码级无缺陷 → 真实环境根因在传输层/断开检测/进程时序，"
                  "修复方向=cancel/resume 唤醒确认+保底自救 + _finalize 超时保护", flush=True)
        else:
            print("结论：代码级确定性缺陷 → 需精确定位 runner 未唤醒断点", flush=True)


asyncio.run(main())
