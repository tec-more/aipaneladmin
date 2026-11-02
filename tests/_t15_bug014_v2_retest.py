"""
BUG-T15-014 v2 结构性修复复测（shield 原子化 + finally 协作唤醒 + runner-done 短路）

v2 预期（与 v1 语义不同——断开后不再保持 paused 持槽，而是秒级自愈）：
- 断开 SSE → generator finally：request_cancel + resume({"cancelled": True}) 协作唤醒
  → runner 走 ExecutionCancelled（ack + 「执行被取消」日志）→ done_callback/_finalize_once
  → shield(_finalize) → 落库 cancelled + 释放槽 + 「执行结束」日志

复测场景：
- V2-A 断开无操作自愈专项：断开不调任何 API，≤3s status=cancelled + probe 200（核心验收）
- V2-B 断开后 cancel（多轮 race）：HTTP 200 + status cancelled + probe 200（可自救不泄漏）
- V2-C 断开后 resume：恢复无从谈起（accepted=False），槽释放 probe 200
- V2-D 心跳帧观测：HITL 静默期读 ~16s，应收到 : ping comment 帧
- C1/C2 防回归：快速图完整消费 / 读 1 帧断开 done_callback 兜底

运行: .venv/Scripts/python.exe tests/_t15_bug014_v2_retest.py
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

    async def exec_row(eid):
        return await WorkflowExecution.get_or_none(id=eid)

    async def wait_status(eid, targets, timeout=15.0):
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            row = await exec_row(eid)
            if row and row.status in targets:
                return row, round(time.monotonic() - t0, 2)
            await asyncio.sleep(0.1)
        return await exec_row(eid), round(time.monotonic() - t0, 2)

    try:
        busy = await WorkflowExecution.filter(
            owner_type="usr", owner_id=1, status__in=["running", "paused"]).all()
        record("C0", "预检：usr:1 槽位空闲", len(busy) == 0, f"busy={[e.id for e in busy]}")
        if busy:
            print("[预检中止] 请先重启服务清槽", flush=True)
            return

        async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "BUG014v2-快速图", "graph_json": GRAPH_FAST})
            wid_fast = (r.json().get("data") or {}).get("id")
            created.append(wid_fast)
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "BUG014v2-HITL图", "graph_json": GRAPH_HITL})
            wid_hitl = (r.json().get("data") or {}).get("id")
            created.append(wid_hitl)

            async def probe(tag, wid=wid_fast) -> int:
                async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                      headers=headers, json={"inputs": {"query": "probe"}},
                                      timeout=30.0) as resp:
                    code = resp.status_code
                    if code == 200:
                        async for _ in resp.aiter_lines():
                            pass
                    else:
                        body = (await resp.aread()).decode("utf-8", "replace")[:120]
                        print(f"    [{tag}] 探测: {code} body={body}", flush=True)
                        return code
                print(f"    [{tag}] 探测: {code}（槽空闲）", flush=True)
                return code

            async def start_hitl_to_paused(tag):
                """dry-run HITL → run_paused + paused 落库，返回 exec_id（此时连接仍开着）"""
                resp_cm = cli.stream("POST", f"/v1/agent/u/workflows/{wid_hitl}/dry-run",
                                     headers=headers, json={"inputs": {"query": tag}},
                                     timeout=30.0)
                resp = await resp_cm.__aenter__()
                assert resp.status_code == 200, f"{tag} dry-run 被拒: {resp.status_code}"
                eid = int(resp.headers.get("X-Execution-Id"))
                last_ev = None
                async for line in resp.aiter_lines():
                    if line.startswith("event:"):
                        last_ev = line[6:].strip()
                    if last_ev == "run_paused":
                        break
                row, _ = await wait_status(eid, {"paused"}, timeout=5.0)
                assert row is not None and row.status == "paused", f"{tag} paused 未落库"
                return eid, resp_cm

            # ================= C1 防回归：完整消费 =================
            print("\n[C1] 快速图完整消费 ...", flush=True)
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid_fast}/dry-run",
                                  headers=headers, json={"inputs": {"query": "c1"}},
                                  timeout=30.0) as resp:
                eid_c1 = resp.headers.get("X-Execution-Id")
                async for _ in resp.aiter_lines():
                    pass
            await asyncio.sleep(1.0)
            row1 = await exec_row(eid_c1)
            p1 = await probe("C1")
            record("C1", "防回归：完整消费 success 落库 + 槽释放",
                   p1 == 200 and row1 is not None and row1.status == "success",
                   f"probe={p1} status={row1.status if row1 else None}")

            # ================= C2 防回归：读1帧断开 done_callback =================
            print("\n[C2] 快速图读 1 帧断开 ...", flush=True)
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid_fast}/dry-run",
                                  headers=headers, json={"inputs": {"query": "c2"}},
                                  timeout=30.0) as resp:
                eid_c2 = resp.headers.get("X-Execution-Id")
                async for _ in resp.aiter_lines():
                    break
            row2, _ = await wait_status(eid_c2, {"success", "failed", "cancelled"}, timeout=15.0)
            p2 = await probe("C2")
            record("C2", "防回归：中断后 done_callback 兜底终态落库 + 槽释放",
                   row2 is not None and row2.status in ("success", "failed", "cancelled")
                   and p2 == 200,
                   f"status={row2.status if row2 else None} probe={p2}")

            # ================= V2-A 断开无操作自愈专项 =================
            print("\n[V2-A] HITL 断开无操作自愈专项（不调任何 API）...", flush=True)
            eid_a, cm_a = await start_hitl_to_paused("V2-A")
            t_disc = time.monotonic()
            await cm_a.__aexit__(None, None, None)   # 断开 SSE，不调任何 API
            print(f"    [V2-A] exec={eid_a} 已断开 t={time.strftime('%H:%M:%S')}，观察自愈 ...",
                  flush=True)
            row_a, el_a = await wait_status(eid_a, {"cancelled"}, timeout=3.0)
            healed_a = row_a is not None and row_a.status == "cancelled"
            p_a = await probe("V2-A")
            record("V2-A", "断开无操作自愈：≤3s status=cancelled + 槽释放（finally 协作唤醒）",
                   healed_a and p_a == 200,
                   f"自愈={healed_a} 耗时={el_a}s status={row_a.status if row_a else None} "
                   f"probe={p_a}")

            # ================= V2-B 断开后 cancel（多轮 race） =================
            for rnd in (1, 2):
                print(f"\n[V2-B{rnd}] HITL 断开后 cancel 第 {rnd} 轮 ...", flush=True)
                eid_b, cm_b = await start_hitl_to_paused(f"V2-B{rnd}")
                await cm_b.__aexit__(None, None, None)   # 断开
                await asyncio.sleep(1.5)   # 给自愈留窗口
                row_b_pre = await exec_row(eid_b)
                rc = await cli.post(f"/v1/agent/u/executions/{eid_b}/cancel", headers=headers)
                await asyncio.sleep(0.5)
                row_b = await exec_row(eid_b)
                p_b = await probe(f"V2-B{rnd}")
                record(f"V2-B{rnd}",
                       "断开后 cancel：HTTP200 + status cancelled + 槽释放（自愈短路或保底）",
                       rc.status_code == 200 and row_b is not None
                       and row_b.status == "cancelled" and p_b == 200,
                       f"断开1.5s后status={row_b_pre.status if row_b_pre else None} "
                       f"cancel_http={rc.status_code} 终态={row_b.status if row_b else None} "
                       f"probe={p_b}")

            # ================= V2-C 断开后 resume =================
            print("\n[V2-C] HITL 断开后 resume ...", flush=True)
            eid_c, cm_c = await start_hitl_to_paused("V2-C")
            await cm_c.__aexit__(None, None, None)   # 断开
            rr = await cli.post(f"/v1/agent/u/executions/{eid_c}/resume", headers=headers,
                                json={"approved": True, "comment": "v2复测"})
            body_c = rr.json().get("data") or {}
            await asyncio.sleep(0.5)
            row_c = await exec_row(eid_c)
            p_c = await probe("V2-C")
            # 恢复无从谈起：accepted=False；状态收敛（cancelled 自愈 或 interrupted 保底）；槽释放
            record("V2-C", "断开后 resume：accepted=False（恢复无从谈起）+ 状态收敛 + 槽释放",
                   rr.status_code == 200 and body_c.get("accepted") is False
                   and row_c is not None and row_c.status in ("cancelled", "interrupted")
                   and p_c == 200,
                   f"http={rr.status_code} body={body_c} 终态={row_c.status if row_c else None} "
                   f"probe={p_c}")

            # ================= V2-D 心跳帧观测 =================
            print("\n[V2-D] HITL 静默期心跳帧观测（读 ~16s）...", flush=True)
            pings = 0
            try:
                async with cli.stream("POST", f"/v1/agent/u/workflows/{wid_hitl}/dry-run",
                                      headers=headers, json={"inputs": {"query": "v2d"}},
                                      timeout=30.0) as resp:
                    eid_d = int(resp.headers.get("X-Execution-Id"))
                    last_ev = None
                    t0 = time.monotonic()
                    async for line in resp.aiter_lines():
                        if line.startswith("event:"):
                            last_ev = line[6:].strip()
                        if last_ev == "run_paused":
                            last_ev = None  # 继续读，等 ping
                        if line.strip() == ": ping":
                            pings += 1
                        if time.monotonic() - t0 > 16.0:
                            break
            except Exception as e:
                print(f"    [V2-D] 读流异常: {type(e).__name__}", flush=True)
            record("V2-D", "SSE 心跳帧：HITL 静默期收到 : ping comment 帧",
                   pings >= 1, f"16s 内 ping 帧数={pings}")
            # V2-D 断开后自愈，等槽释放
            await asyncio.sleep(2.0)
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

    print("\n===== BUG-T15-014 v2 复测汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")


asyncio.run(main())
