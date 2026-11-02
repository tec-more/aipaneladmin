"""
BUG-T15-013 修复回归：A8/A9 关联用例精简执行（自包含，无 KB/agent 依赖）

- A8 hitl timeout_minutes=5 + on_timeout=approve → ~300s 超时自动通过 auto_approved=True
  （不断开 SSE，完整消费；验证 emit 内 settle 超时保护对长 HITL 执行无影响）
- A9 hitl 旧字段 timeout_s=300 + timeout_action=fail → run_paused 且 deadline≈now+300s，
  流内 cancel（不断开，同 G1 模式）→ 快速终态 cancelled

运行: .venv/Scripts/python.exe tests/_t15_a8_a9_retest.py
"""
import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from base.common.security import create_access_token

BASE = "http://127.0.0.1:9998"
RESULTS: list[dict] = []


def record(case_id: str, name: str, passed: bool, detail: str):
    RESULTS.append({"id": case_id, "name": name, "pass": passed, "detail": detail})
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {case_id} {name} :: {detail}", flush=True)


def make_token() -> str:
    return create_access_token({"typ": "usr", "sub": "1"}, expires_delta=timedelta(hours=2))


def _start_node():
    return {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
            "data": {"outputs": [{"name": "query", "type": "string"}]}}


def _end_node(x=400, inputs=None):
    return {"id": "e1", "type": "end", "position": {"x": x, "y": 0},
            "data": {"inputs": inputs or []}}


def graph_hitl(config: dict) -> dict:
    return {
        "schema_version": 2,
        "nodes": [
            _start_node(),
            {"id": "h1", "type": "hitl", "position": {"x": 200, "y": 0},
             "data": {"config": config,
                      "inputs": [{"name": "context", "type": "string", "from": "s1.query"}],
                      "outputs": [{"name": "approved", "type": "boolean"},
                                  {"name": "auto_approved", "type": "boolean"}]}},
            _end_node(inputs=[{"name": "approved", "type": "boolean", "from": "h1.approved"},
                              {"name": "auto_approved", "type": "boolean", "from": "h1.auto_approved"}]),
        ],
        "edges": [
            {"id": "e1", "source": "s1", "target": "h1", "sourceHandle": "out", "targetHandle": "in"},
            {"id": "e2", "source": "h1", "target": "e1", "sourceHandle": "out", "targetHandle": "in"},
        ],
        "variables": [],
    }


async def main():
    headers = {"Authorization": f"Bearer {make_token()}"}
    created = []

    async def create_wf(cli, name, graph):
        r = await cli.post("/v1/agent/u/workflows", headers=headers,
                           json={"name": name, "graph_json": graph})
        wid = (r.json().get("data") or {}).get("id") if r.status_code == 200 else None
        if not wid:
            print(f"  [建图失败] {name}: {r.status_code} {r.text[:200]}", flush=True)
        return wid

    async def get_exec(cli, exec_id):
        if not exec_id:
            return {}
        await asyncio.sleep(0.8)
        r = await cli.get(f"/v1/agent/u/executions/{exec_id}", headers=headers)
        return (r.json().get("data") or {}) if r.status_code == 200 else {}

    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
            # ==================== A8 ====================
            print("\n===== A8 hitl timeout_minutes=5 + on_timeout=approve（约300s） =====",
                  flush=True)
            wid = await create_wf(cli, "T15-013回归-A8超时approve",
                                  graph_hitl({"timeout_minutes": 5, "on_timeout": "approve"}))
            created.append(wid)
            t0 = time.monotonic()
            exec_id_a8, http_a8, data_text = None, None, ""
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "T15复测"}},
                                  timeout=420.0) as resp:
                http_a8 = resp.status_code
                exec_id_a8 = resp.headers.get("X-Execution-Id")
                if http_a8 == 200:
                    async for line in resp.aiter_lines():
                        if line.startswith("data:"):
                            data_text += line[5:].strip() + "\n"
            elapsed_a8 = time.monotonic() - t0
            exec_a8 = await get_exec(cli, exec_id_a8)
            out_a8 = exec_a8.get("output_data") or {}
            record("A8a", "timeout_minutes=5 被解析：~300s 后超时（非默认72h挂起）",
                   http_a8 == 200 and 290.0 <= elapsed_a8 <= 400.0,
                   f"http={http_a8} elapsed={elapsed_a8:.1f}s ∈[290,400]")
            record("A8b", "on_timeout=approve 生效：超时自动通过 approved/auto_approved=True，执行成功",
                   exec_a8.get("status") == "success" and out_a8.get("auto_approved") is True
                   and out_a8.get("approved") is True,
                   f"exec_status={exec_a8.get('status')} "
                   f"output={json.dumps(out_a8, ensure_ascii=False)[:150]}")

            # ==================== A9 ====================
            print("\n===== A9 hitl 旧字段 timeout_s=300 / timeout_action=fail"
                  "（流内 cancel，不断开） =====", flush=True)
            wid = await create_wf(cli, "T15-013回归-A9兼容hitl",
                                  graph_hitl({"timeout_s": 300, "timeout_action": "fail"}))
            created.append(wid)
            t0 = time.monotonic()
            paused_deadline, cancel_http, exec_id_a9, http_a9 = None, None, None, None
            events_a9, last_ev = [], None
            async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                                  headers=headers, json={"inputs": {"query": "T15复测"}},
                                  timeout=90.0) as resp:
                http_a9 = resp.status_code
                exec_id_a9 = resp.headers.get("X-Execution-Id")
                if http_a9 == 200:
                    async for line in resp.aiter_lines():
                        if line.startswith("event:"):
                            last_ev = line[6:].strip()
                            events_a9.append(last_ev)
                        elif line.startswith("data:") and last_ev == "run_paused" \
                                and paused_deadline is None:
                            try:
                                paused_deadline = json.loads(line[5:].strip()).get("deadline")
                            except Exception:
                                pass
                            rc = await cli.post(
                                f"/v1/agent/u/executions/{exec_id_a9}/cancel",
                                headers=headers)
                            cancel_http = rc.status_code
            elapsed_a9 = time.monotonic() - t0
            exec_a9 = await get_exec(cli, exec_id_a9)
            dl_ok = False
            if paused_deadline:
                try:
                    delta = (datetime.fromisoformat(paused_deadline)
                             - datetime.now()).total_seconds()
                    dl_ok = 240.0 <= delta <= 330.0
                except Exception:
                    pass
            record("A9a", "旧字段 timeout_s=300 被引擎解析：进入 run_paused 且 deadline≈now+300s",
                   http_a9 == 200 and paused_deadline is not None and dl_ok,
                   f"http={http_a9} deadline={paused_deadline} events={events_a9[:6]}")
            record("A9b", "paused 态流内 cancel 生效：快速终态 cancelled（无需等待 300s 超时）",
                   cancel_http == 200 and exec_a9.get("status") == "cancelled"
                   and elapsed_a9 < 60.0,
                   f"cancel_http={cancel_http} exec_status={exec_a9.get('status')} "
                   f"elapsed={elapsed_a9:.1f}s")
    finally:
        async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as cli:
            for w in created:
                if w:
                    try:
                        await cli.delete(f"/v1/agent/u/workflows/{w}", headers=headers)
                    except Exception:
                        pass
        print("\n[清理完成]", flush=True)

    print("\n===== A8/A9 回归汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")


asyncio.run(main())
