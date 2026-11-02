"""
BUG-T15-013 C3b 失败根因：本地决定性模拟实验

在本地事件循环完整复现 C3 场景（真实 ExecutionService.stream_events + 真实
InProcessBackend + GRAPH_HITL），mock 仅 DB/配额/Trace 层：

时序精确复现：
1. 消费 SSE 至 run_paused 帧
2. aclose(generator)（模拟客户端断开，触发 generator finally：
   request_cancel + wait_for(task, 5s) 窗口）
3. 在 finally 的 5s 窗口内调用 ExecutionService.cancel（真实，走 _controls 注册表）
4. 观测：runner 是否被唤醒（ExecutionCancelled）、_finalize 是否执行、
   release_concurrency 是否调用、cancel() 返回值

判别：
- 若 runner 唤醒且收尾执行 → 本地链路正常，服务端问题在传输层/时序（深查 uvicorn）
- 若 runner 未唤醒/收尾未执行 → 代码级确定性缺陷，精确定位断点

运行: .venv/Scripts/python.exe tests/_t15_bug013_sim.py
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

# ---- mock 观测钩子 ----
release_calls = []
update_status_calls = []
finalize_calls = []


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

        ctx = SimpleNamespace(execution_id=7777, owner=("usr", 1), quota_hold_id=None,
                              version_id=1, settings={})
        agen = ExecutionService.stream_events(ctx, GRAPH_HITL, {"query": "sim"})

        # 1) 消费至 run_paused 帧
        got_paused = False
        frames = []
        async for f in agen:
            frames.append(f)
            if "run_paused" in f:
                got_paused = True
                break
        print(f"[1] 收到 run_paused={got_paused}, frames={len(frames)}", flush=True)
        await asyncio.sleep(0.2)  # 让后台 paused 落库 task 完成
        print(f"    update_status_calls={update_status_calls}", flush=True)
        print(f"    _controls 注册: {list(ExecutionService._controls.keys())}", flush=True)

        # 2) aclose 模拟断开 → generator finally 启动（request_cancel + wait_for(task,5s)）
        print("[2] aclose() 模拟断开 ...", flush=True)
        close_task = asyncio.create_task(agen.aclose())
        await asyncio.sleep(0.5)  # finally 已进入 wait_for(task, 5s) 窗口
        print(f"    aclose 进行中 done={close_task.done()}, "
              f"_controls={list(ExecutionService._controls.keys())}", flush=True)

        # 3) 5s 窗口内调用真实 cancel（走 _controls 注册表 → resume_event.set()）
        print("[3] 窗口内调用 ExecutionService.cancel(7777) ...", flush=True)
        # cancel() 首行查 DB（get_or_none），mock 环境无 DB → 直接 patch 掉该查询
        fake_exec = SimpleNamespace(status="paused")

        class FakeQS:
            async def get_or_none(self, id):
                return fake_exec

        # 直接 patch WorkflowExecution.get_or_none 路径：cancel 内引用的是模块级导入
        import base.plugins.agent.services.execution_service as es_mod
        with patch.object(es_mod.WorkflowExecution, "get_or_none",
                          lambda id: _fake_get(fake_exec)):
            t0 = time.monotonic()
            ret = await ExecutionService.cancel(7777)
            print(f"    cancel 返回={ret} 耗时={time.monotonic()-t0:.3f}s", flush=True)

        # 4) 观测 runner 唤醒与收尾
        print("[4] 等待 3s 观测收尾 ...", flush=True)
        await asyncio.sleep(3.0)
        print(f"    aclose done={close_task.done()}", flush=True)
        print(f"    update_status_calls={update_status_calls}", flush=True)
        print(f"    release_calls={release_calls}", flush=True)
        print(f"    _controls={list(ExecutionService._controls.keys())}", flush=True)

        # 判定
        woke = any(s == "cancelled" for _, s, _ in update_status_calls)
        released = len(release_calls) >= 1
        print(f"\n判定: runner唤醒落库cancelled={woke}, 槽释放={released}, "
              f"aclose完成={close_task.done()}", flush=True)
        if woke and released:
            print("结论: 本地链路正常——问题在服务端传输层/断开检测时序", flush=True)
        else:
            print("结论: 本地复现代码级缺陷——cancel 唤醒或收尾链路存在确定性断点", flush=True)


async def _fake_get(fake):
    return fake


asyncio.run(main())
