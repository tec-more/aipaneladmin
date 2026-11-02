"""
BUG-T15-014 v2 复测（HITL 矩阵，修正断开方式：持续读 + 显式 aclose，避免 break 提前关连接）

v2 核心验收：断开后槽不泄漏（probe 200）+ cancel/resume 可自救。
观察项：断开后是否「执行被取消」（协作唤醒）还是强杀（tokens=None）。

场景：
- V2-A 断开无操作自愈：paused 落库后断开不调 API → ≤3s cancelled + probe 200
- V2-B 断开后 cancel（2 轮 race）：HTTP200 + cancelled + probe 200
- V2-C 断开后 resume：accepted=False + 状态收敛(cancelled/interrupted) + probe 200
- V2-D 心跳帧：持续读 16s 收 : ping

运行: .venv/Scripts/python.exe tests/_t15_bug014_v2_hitl.py
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


def record(cid, name, passed, detail):
    RESULTS.append({"id": cid, "pass": passed})
    print(f"[{'PASS' if passed else 'FAIL'}] {cid} {name} :: {detail}", flush=True)


def make_token():
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
            await asyncio.sleep(0.05)
        return await exec_row(eid), round(time.monotonic() - t0, 2)

    try:
        busy = await WorkflowExecution.filter(
            owner_type="usr", owner_id=1, status__in=["running", "paused"]).all()
        record("C0", "预检槽位空闲", len(busy) == 0, f"busy={[e.id for e in busy]}")
        if busy:
            print("[中止] 需重启服务清槽", flush=True)
            return

        async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "V2H-快速", "graph_json": GRAPH_FAST})
            wid_fast = (r.json().get("data") or {}).get("id"); created.append(wid_fast)
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "V2H-HITL", "graph_json": GRAPH_HITL})
            wid_hitl = (r.json().get("data") or {}).get("id"); created.append(wid_hitl)

            async def probe(tag):
                async with cli.stream("POST", f"/v1/agent/u/workflows/{wid_fast}/dry-run",
                                      headers=headers, json={"inputs": {"query": "p"}},
                                      timeout=30.0) as resp:
                    code = resp.status_code
                    if code == 200:
                        async for _ in resp.aiter_lines():
                            pass
                    else:
                        print(f"    [{tag}] probe={code}（槽占用）", flush=True)
                        return code
                print(f"    [{tag}] probe=200（槽空闲）", flush=True)
                return 200

            async def start_hitl(tag):
                """启动 HITL，持续读 SSE（不 break）等 paused 落库，返回断开句柄"""
                resp_cm = cli.stream("POST", f"/v1/agent/u/workflows/{wid_hitl}/dry-run",
                                     headers=headers, json={"inputs": {"query": tag}}, timeout=30.0)
                resp = await resp_cm.__aenter__()
                assert resp.status_code == 200, f"{tag} dry-run 被拒 {resp.status_code}"
                eid = int(resp.headers.get("X-Execution-Id"))
                stop = asyncio.Event(); events = []

                async def read():
                    try:
                        async for line in resp.aiter_lines():
                            if stop.is_set():
                                return
                            if line.startswith("event:"):
                                events.append(line[6:].strip())
                            elif line.strip() == ": ping":
                                events.append(":ping")
                    except Exception:
                        pass
                reader = asyncio.create_task(read())
                row, _ = await wait_status(eid, {"paused"}, timeout=5.0)
                assert row is not None and row.status == "paused", f"{tag} paused 未落库: {row.status if row else None}"
                return eid, resp, resp_cm, reader, stop, events

            async def disconnect(resp, resp_cm, reader, stop):
                stop.set(); reader.cancel()
                try:
                    await resp.aclose()
                except Exception:
                    pass
                try:
                    await resp_cm.__aexit__(None, None, None)
                except Exception:
                    pass

            # ---- V2-A 断开无操作自愈 ----
            print("\n[V2-A] paused 后断开，不调任何 API，观察自愈 ...", flush=True)
            eid_a, ra, cma, rda, sta, eva = await start_hitl("V2-A")
            t0 = time.monotonic()
            await disconnect(ra, cma, rda, sta)
            print(f"    [V2-A] exec={eid_a} 断开 t={time.strftime('%H:%M:%S')}", flush=True)
            row_a, el_a = await wait_status(eid_a, {"cancelled"}, timeout=3.0)
            healed = row_a is not None and row_a.status == "cancelled"
            p_a = await probe("V2-A")
            record("V2-A", "断开无操作自愈：≤3s cancelled + 槽释放",
                   healed and p_a == 200,
                   f"自愈={healed} 耗时={el_a}s status={row_a.status if row_a else None} probe={p_a} 事件={eva}")

            # ---- V2-B 断开后 cancel（2 轮） ----
            for rnd in (1, 2):
                print(f"\n[V2-B{rnd}] paused 后断开，1.5s 后 cancel ...", flush=True)
                eid_b, rb, cmb, rdb, stb, evb = await start_hitl(f"V2-B{rnd}")
                await disconnect(rb, cmb, rdb, stb)
                await asyncio.sleep(1.5)
                row_pre = await exec_row(eid_b)
                rc = await cli.post(f"/v1/agent/u/executions/{eid_b}/cancel", headers=headers)
                await asyncio.sleep(0.5)
                row_b = await exec_row(eid_b)
                p_b = await probe(f"V2-B{rnd}")
                record(f"V2-B{rnd}", "断开后 cancel：HTTP200 + cancelled + 槽释放",
                       rc.status_code == 200 and row_b is not None
                       and row_b.status == "cancelled" and p_b == 200,
                       f"断开1.5s后={row_pre.status if row_pre else None} http={rc.status_code} "
                       f"终态={row_b.status if row_b else None} probe={p_b}")

            # ---- V2-C 断开后 resume ----
            print("\n[V2-C] paused 后断开，立即 resume ...", flush=True)
            eid_c, rcn, cmc, rdc, stc, evc = await start_hitl("V2-C")
            await disconnect(rcn, cmc, rdc, stc)
            rr = await cli.post(f"/v1/agent/u/executions/{eid_c}/resume", headers=headers,
                                json={"approved": True, "comment": "v2"})
            body_c = rr.json().get("data") or {}
            await asyncio.sleep(0.8)
            row_c = await exec_row(eid_c)
            p_c = await probe("V2-C")
            record("V2-C", "断开后 resume：accepted=False + 状态收敛 + 槽释放",
                   rr.status_code == 200 and body_c.get("accepted") is False
                   and row_c is not None and row_c.status in ("cancelled", "interrupted")
                   and p_c == 200,
                   f"http={rr.status_code} accepted={body_c.get('accepted')} "
                   f"status_ret={body_c.get('status')} 终态={row_c.status if row_c else None} probe={p_c}")

            # ---- V2-D 心跳帧 ----
            print("\n[V2-D] HITL 持续读 16s 观测 : ping ...", flush=True)
            eid_d, rd, cmd, rdd, std, evd = await start_hitl("V2-D")
            t0 = time.monotonic()
            while time.monotonic() - t0 < 16.0:
                await asyncio.sleep(0.5)
            pings = evd.count(":ping")
            record("V2-D", "SSE 心跳帧：16s 内收到 : ping", pings >= 1,
                   f"ping 帧数={pings} 事件={evd}")
            await disconnect(rd, cmd, rdd, std)
            await asyncio.sleep(2.0)
            await probe("V2-D清理")
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

    print("\n===== BUG-T15-014 v2 HITL 矩阵汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']}")


asyncio.run(main())
