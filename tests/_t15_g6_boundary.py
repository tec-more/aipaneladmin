"""
T15 节点3 / G6 边界与非功能 P1 用例集（9 条）

依据锚点：
- G6-01 超大 graph_json 传输：PRD RK-12 大图（100+ 节点）；契约未设 body 上限 → 预期接受且内容保真
- G6-02 空输入：PRD §4 变量 required；引擎 render_template 未解析占位→空串（观测实际行为，对照契约）
- G6-03 超长文本输入：100KB 单变量 → 不崩溃、不截断（无平台上限声明）
- G6-04 特殊类型变量：object/array/boolean/number/null/unicode 跨节点透传保真（04-§4.1 类型契约）
- G6-05 大量节点执行：120 节点线性链 dry-run 全节点覆盖（RK-12/AC-15）
- G6-06 试跑并发=1：04-F2 单用户试跑并发=1；超并发 → 42901 item=concurrency
- G6-07 乐观锁：05-§1.2 保存草稿 draft_version 冲突 → 409 code=40901 + current_draft_version
- G6-08 发布幂等：04-§1.2/5.2 Idempotency-Key 24h 去重，重放返回原 version_no，不产生新版本
- G6-09 Trace 完整性：AC-15 + N4-6：seq 全局单调递增、事件覆盖全部节点、SSE 与 trace API 一致

运行: .venv/Scripts/python.exe tests/_t15_g6_boundary.py
"""
import asyncio
import json
import sys
import time
from datetime import timedelta
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


# ============================================================
# 图构造（Schema v2，契约字段口径）
# ============================================================

def _start(outputs):
    return {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
            "data": {"outputs": [{"name": n, "type": t} for n, t in outputs]}}


def _end(inputs=None, x=400):
    return {"id": "e1", "type": "end", "position": {"x": x, "y": 0},
            "data": {"inputs": inputs or []}}


def _edge(i, src, tgt):
    return {"id": f"e{i}", "source": src, "target": tgt,
            "sourceHandle": "out", "targetHandle": "in"}


def graph_linear_templates(n_mid: int, tpl_text: str, out_vars=("query",)) -> dict:
    """start → n_mid 个 template → end 的线性链"""
    nodes = [_start([(n, "string") for n in out_vars])]
    for i in range(1, n_mid + 1):
        nodes.append({
            "id": f"t{i}", "type": "template", "position": {"x": 100 * i, "y": 0},
            "data": {"config": {"template": tpl_text},
                     "inputs": [], "outputs": [{"name": "output", "type": "string"}]},
        })
    nodes.append(_end(inputs=[{"name": "answer", "type": "string", "from": f"t{n_mid}.output"}],
                      x=100 * (n_mid + 1)))
    edges = []
    ids = ["s1"] + [f"t{i}" for i in range(1, n_mid + 1)] + ["e1"]
    for i in range(len(ids) - 1):
        edges.append(_edge(i + 1, ids[i], ids[i + 1]))
    return {"schema_version": 2, "nodes": nodes, "edges": edges,
            "variables": [{"name": n, "type": "string", "required": True} for n in out_vars]}


def graph_hitl() -> dict:
    return {
        "schema_version": 2,
        "nodes": [
            _start([("query", "string")]),
            {"id": "h1", "type": "hitl", "position": {"x": 200, "y": 0},
             "data": {"config": {"timeout_minutes": 5, "on_timeout": "approve"},
                      "inputs": [{"name": "context", "type": "any", "from": "s1.query"}],
                      "outputs": [{"name": "approved", "type": "boolean"}]}},
            _end(),
        ],
        "edges": [_edge(1, "s1", "h1"), _edge(2, "h1", "e1")],
        "variables": [{"name": "query", "type": "string"}],
    }


async def create_wf(cli, headers, name, graph) -> tuple:
    t0 = time.monotonic()
    r = await cli.post("/v1/agent/u/workflows", headers=headers,
                       json={"name": name, "graph_json": graph})
    dt = time.monotonic() - t0
    wid = (r.json().get("data") or {}).get("id") if r.status_code == 200 else None
    if not wid:
        print(f"  [建图失败] {name}: {r.status_code} {r.text[:200]}", flush=True)
    return wid, dt, r


async def dry_run_collect(cli, wid, headers, inputs=None, timeout=150.0) -> dict:
    """dry-run SSE 收集：events=[(type, data_dict)], 含 seq"""
    t0 = time.monotonic()
    events, data_lines = [], []
    try:
        async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                              headers=headers, json={"inputs": inputs if inputs is not None else {"query": "G6"}},
                              timeout=timeout) as resp:
            status = resp.status_code
            exec_id = resp.headers.get("X-Execution-Id")
            if status != 200:
                text = await resp.aread()
                return {"status": status, "exec_id": exec_id, "events": [],
                        "data_text": text.decode("utf-8", "replace")[:500],
                        "elapsed": time.monotonic() - t0}
            cur_type = None
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    cur_type = line[6:].strip()
                    events.append([cur_type, None])
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
                    if events and events[-1][1] is None:
                        try:
                            events[-1][1] = json.loads(data_lines[-1])
                        except Exception:
                            events[-1][1] = {}
    except Exception as e:
        return {"status": -1, "exec_id": None, "events": events,
                "data_text": f"{type(e).__name__}: {e}\n" + "\n".join(data_lines[-3:]),
                "elapsed": time.monotonic() - t0}
    return {"status": status, "exec_id": exec_id, "events": events,
            "data_text": "\n".join(data_lines[-5:]), "elapsed": time.monotonic() - t0}


async def get_exec(cli, headers, exec_id) -> dict:
    if not exec_id:
        return {}
    await asyncio.sleep(0.8)
    r = await cli.get(f"/v1/agent/u/executions/{exec_id}", headers=headers)
    return (r.json().get("data") or {}) if r.status_code == 200 else {}


async def get_trace(cli, headers, exec_id) -> list:
    if not exec_id:
        return []
    r = await cli.get(f"/v1/agent/u/executions/{exec_id}/trace", headers=headers,
                      params={"limit": 1000})
    return ((r.json().get("data") or {}).get("events") or []) if r.status_code == 200 else []


# ============================================================
# 主流程
# ============================================================

async def main():
    headers = {"Authorization": f"Bearer {make_token()}"}
    created_wfs: list = []

    async with httpx.AsyncClient(base_url=BASE, timeout=180.0) as cli:
        try:
            # ====================================================
            # G6-01 超大 graph_json（200 节点，~600KB 载荷）
            # ====================================================
            print("\n===== G6-01 超大 graph_json 传输 =====", flush=True)
            big_tpl = ("步骤说明{{query}}" + "长文本填充" * 120)  # ~1.4KB/节点
            big_graph = graph_linear_templates(198, big_tpl)
            payload_kb = len(json.dumps(big_graph, ensure_ascii=False).encode("utf-8")) / 1024
            wid, dt_create, r = await create_wf(cli, headers, "G6-01超大图", big_graph)
            created_wfs.append(wid)
            record("G6-01a", f"200 节点大图创建（载荷 {payload_kb:.0f}KB）不 413/500",
                   r.status_code == 200 and wid is not None,
                   f"http={r.status_code} wid={wid} payload={payload_kb:.0f}KB create_ms={dt_create*1000:.0f}")

            t0 = time.monotonic()
            rv = await cli.post(f"/v1/agent/u/workflows/{wid}/validate", headers=headers,
                                json={"graph_json": big_graph})
            dt_val = time.monotonic() - t0
            vdata = (rv.json().get("data") or {}) if rv.status_code == 200 else {}
            record("G6-01b", "大图全量校验：无阻断级错误（warning 可存在）",
                   rv.status_code == 200 and vdata.get("valid") is True,
                   f"http={rv.status_code} valid={vdata.get('valid')} "
                   f"errors={vdata.get('error_count')} warnings={vdata.get('warning_count')} "
                   f"validate_ms={dt_val*1000:.0f}")

            t0 = time.monotonic()
            rg = await cli.get(f"/v1/agent/u/workflows/{wid}", headers=headers)
            dt_get = time.monotonic() - t0
            detail = (rg.json().get("data") or {}) if rg.status_code == 200 else {}
            dnodes = (detail.get("definition") or {}).get("nodes") or []
            tpl_ok = any(
                (((n.get("data") or {}).get("config") or {}).get("template") == big_tpl)
                for n in dnodes if n.get("id") == "t100")
            record("G6-01c", "大图详情回读：节点数与模板内容保真（序列化无损）",
                   rg.status_code == 200 and len(dnodes) == 200 and tpl_ok,
                   f"http={rg.status_code} nodes={len(dnodes)} tpl_intact={tpl_ok} get_ms={dt_get*1000:.0f}")

            # ====================================================
            # G6-02 空输入（inputs={}，缺 required 变量 query）
            # ====================================================
            print("\n===== G6-02 空输入处理 =====", flush=True)
            g = graph_linear_templates(1, "前缀[{{query}}]后缀")
            wid2, _, _ = await create_wf(cli, headers, "G6-02空输入", g)
            created_wfs.append(wid2)
            res = await dry_run_collect(cli, wid2, headers, inputs={})
            exec2 = await get_exec(cli, headers, res["exec_id"])
            etypes = [e[0] for e in res["events"]]
            out2 = (exec2.get("output_data") or {})
            record("G6-02a", "空输入不崩溃：SSE 正常建立且有终态事件（非 ENGINE_CRASH）",
                   res["status"] == 200 and ("run_completed" in etypes or "run_failed" in etypes),
                   f"http={res['status']} events={etypes}")
            record("G6-02b", "空输入执行终态明确（观测未解析占位→空串替换行为）",
                   exec2.get("status") in ("success", "failed"),
                   f"exec_status={exec2.get('status')} output={json.dumps(out2, ensure_ascii=False)[:120]}")

            # ====================================================
            # G6-03 超长文本输入（query=50000 字，~150KB）
            # ====================================================
            print("\n===== G6-03 超长文本输入 =====", flush=True)
            long_text = "长文本边界验证🤖" * 6250  # 50k 字符
            g3 = graph_linear_templates(1, "{{query}}")
            wid3, _, _ = await create_wf(cli, headers, "G6-03超长文本", g3)
            created_wfs.append(wid3)
            res3 = await dry_run_collect(cli, wid3, headers, inputs={"query": long_text})
            exec3 = await get_exec(cli, headers, res3["exec_id"])
            ans3 = ((exec3.get("output_data") or {}).get("answer"))
            record("G6-03a", "50k 字符输入：dry-run 执行成功不 500/不崩溃",
                   res3["status"] == 200 and exec3.get("status") == "success",
                   f"http={res3['status']} exec_status={exec3.get('status')} elapsed={res3['elapsed']:.1f}s")
            record("G6-03b", "超长文本跨节点透传保真（无截断、无损坏）",
                   isinstance(ans3, str) and len(ans3) == len(long_text),
                   f"expect_len={len(long_text)} actual_len={len(ans3) if isinstance(ans3, str) else type(ans3).__name__}")

            # ====================================================
            # G6-04 特殊类型变量传递（object/array/bool/number/null/unicode/模板符）
            # ====================================================
            print("\n===== G6-04 特殊类型变量透传 =====", flush=True)
            g4 = {
                "schema_version": 2,
                "nodes": [
                    _start([("payload", "object"), ("tags", "array<string>"),
                            ("flag", "boolean"), ("count", "number"), ("note", "string")]),
                    _end(inputs=[
                        {"name": "payload", "type": "any", "from": "s1.payload"},
                        {"name": "tags", "type": "any", "from": "s1.tags"},
                        {"name": "flag", "type": "any", "from": "s1.flag"},
                        {"name": "count", "type": "any", "from": "s1.count"},
                        {"name": "note", "type": "any", "from": "s1.note"},
                    ]),
                ],
                "edges": [_edge(1, "s1", "e1")],
                "variables": [],
            }
            special_inputs = {
                "payload": {"k": "值", "nested": [1, 2.5, {"x": None}], "emoji": "🤖"},
                "tags": ["a", "b", "测"],
                "flag": True,
                "count": 3.14,
                "note": "line1\nline2 \"引号\" {{不应被模板解析}}",
            }
            wid4, _, _ = await create_wf(cli, headers, "G6-04特殊类型", g4)
            created_wfs.append(wid4)
            res4 = await dry_run_collect(cli, wid4, headers, inputs=special_inputs)
            exec4 = await get_exec(cli, headers, res4["exec_id"])
            out4 = exec4.get("output_data") or {}
            fidelity = (
                res4["status"] == 200 and exec4.get("status") == "success"
                and out4.get("payload") == special_inputs["payload"]
                and out4.get("tags") == special_inputs["tags"]
                and out4.get("flag") is True
                and abs((out4.get("count") or 0) - 3.14) < 1e-9
                and out4.get("note") == special_inputs["note"]
            )
            record("G6-04", "object/array/bool/number/null/unicode/模板符 透传保真",
                   fidelity,
                   f"http={res4['status']} exec_status={exec4.get('status')} "
                   f"keys={sorted(out4.keys())} null_kept={out4.get('payload', {}).get('nested', [None])[2] if isinstance(out4.get('payload'), dict) else '?'}")

            # ====================================================
            # G6-05 大量节点执行（120 节点线性链 dry-run）
            # ====================================================
            print("\n===== G6-05 大量节点执行（120 节点） =====", flush=True)
            g5 = graph_linear_templates(118, "step[{{query}}]")
            wid5, _, _ = await create_wf(cli, headers, "G6-05大链执行", g5)
            created_wfs.append(wid5)
            res5 = await dry_run_collect(cli, wid5, headers, inputs={"query": "bulk"}, timeout=120.0)
            exec5 = await get_exec(cli, headers, res5["exec_id"])
            trace5 = await get_trace(cli, headers, res5["exec_id"])
            started_nodes = {e.get("node_id") for e in trace5 if e.get("event_type") == "node_started"}
            expected_nodes = set(f"t{i}" for i in range(1, 119)) | {"s1", "e1"}
            record("G6-05a", "120 节点链执行成功",
                   res5["status"] == 200 and exec5.get("status") == "success",
                   f"http={res5['status']} exec_status={exec5.get('status')} elapsed={res5['elapsed']:.1f}s")
            record("G6-05b", "Trace 覆盖全部 120 个节点（AC-15 大图口径）",
                   started_nodes == expected_nodes,
                   f"trace_started={len(started_nodes)}/120 missing={sorted(expected_nodes - started_nodes)[:5]}")

            # ====================================================
            # G6-06 试跑并发=1（F2）：A 持槽暂停 → B 429 → 取消 A → C 放行
            # ====================================================
            print("\n===== G6-06 试跑并发=1 =====", flush=True)
            widA, _, _ = await create_wf(cli, headers, "G6-06A占槽hitl", graph_hitl())
            widB, _, _ = await create_wf(cli, headers, "G6-06B简单图", graph_linear_templates(1, "x{{query}}"))
            created_wfs += [widA, widB]

            a_events, a_done = [], asyncio.Event()

            async def consume_a():
                try:
                    async with cli.stream("POST", f"/v1/agent/u/workflows/{widA}/dry-run",
                                          headers=headers, json={"inputs": {"query": "hold"}},
                                          timeout=120.0) as ra:
                        a_events.append(("__http__", ra.status_code))
                        a_events.append(("exec_id", ra.headers.get("X-Execution-Id")))
                        cur = None
                        async for line in ra.aiter_lines():
                            if line.startswith("event:"):
                                cur = line[6:].strip()
                                a_events.append((cur, None))
                                if cur == "run_paused":
                                    a_done.set()  # 已占槽并暂停
                except Exception as e:
                    a_events.append(("__err__", f"{type(e).__name__}: {e}"))
                finally:
                    a_done.set()

            task_a = asyncio.create_task(consume_a())
            try:
                await asyncio.wait_for(a_done.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                pass
            paused_seen = any(t == "run_paused" for t, _ in a_events)
            exec_a = next((v for t, v in a_events if t == "exec_id"), None)
            record("G6-06a", "A（hitl）试跑进入暂停并持有并发槽",
                   paused_seen and exec_a is not None,
                   f"paused_seen={paused_seen} exec_a={exec_a}")

            resB = await dry_run_collect(cli, widB, headers, inputs={"query": "B"}, timeout=30.0)
            # BUG-T15-011 修复后契约 04-§2.3：顶层 code=业务码 42901，msg 为字符串，data 透传
            try:
                b_env = json.loads(resB["data_text"])
            except Exception:
                b_env = {}
            record("G6-06b", "B 试跑被并发拦截：HTTP 429 + 顶层 code=42901 + data.item=concurrency（F2 并发=1）",
                   resB["status"] == 429 and b_env.get("code") == 42901
                   and isinstance(b_env.get("msg"), str)
                   and (b_env.get("data") or {}).get("item") == "concurrency",
                   f"http={resB['status']} code={b_env.get('code')} msg_type={type(b_env.get('msg')).__name__} data={b_env.get('data')}")

            rc = await cli.post(f"/v1/agent/u/executions/{exec_a}/cancel", headers=headers)
            await task_a  # 读尽 A 流，让服务端完成 finalize 释放槽位
            execA_final = await get_exec(cli, headers, exec_a)
            record("G6-06c", "A 取消生效：终态 cancelled（F5 协作式取消）",
                   rc.status_code == 200 and execA_final.get("status") == "cancelled",
                   f"cancel_http={rc.status_code} A_status={execA_final.get('status')}")

            await asyncio.sleep(0.5)
            resC = await dry_run_collect(cli, widB, headers, inputs={"query": "C"}, timeout=30.0)
            execC = await get_exec(cli, headers, resC["exec_id"])
            record("G6-06d", "槽位释放后 C 试跑放行成功",
                   resC["status"] == 200 and execC.get("status") == "success",
                   f"http={resC['status']} exec_status={execC.get('status')}")

            # ====================================================
            # G6-07 乐观锁 409（05-§1.2）
            # ====================================================
            print("\n===== G6-07 草稿乐观锁 =====", flush=True)
            wid7, _, _ = await create_wf(cli, headers, "G6-07乐观锁", graph_linear_templates(1, "v1{{query}}"))
            created_wfs.append(wid7)
            rg7 = await cli.get(f"/v1/agent/u/workflows/{wid7}", headers=headers)
            dv0 = ((rg7.json().get("data") or {}).get("draft_version"))
            g7b = graph_linear_templates(1, "v2{{query}}")
            r1 = await cli.put(f"/v1/agent/u/workflows/{wid7}/draft", headers=headers,
                               json={"graph_json": g7b, "draft_version": dv0})
            dv1 = ((r1.json().get("data") or {}).get("draft_version")) if r1.status_code == 200 else None
            r2 = await cli.put(f"/v1/agent/u/workflows/{wid7}/draft", headers=headers,
                               json={"graph_json": g7b, "draft_version": dv0})  # 过期版本
            d2 = r2.json() if r2.status_code in (409, 422) else {}
            # BUG-T15-011 修复后契约 04-§2.3：顶层 code=业务码，msg 字符串，额外字段收拢进 data
            inner2 = d2
            record("G6-07a", "正确 draft_version 保存成功并递增",
                   r1.status_code == 200 and dv1 == (dv0 or 0) + 1,
                   f"first_put={r1.status_code} dv {dv0}->{dv1}")
            record("G6-07b", "过期 draft_version 被 409 拦截：顶层 code=40901 + data.current_draft_version",
                   r2.status_code == 409 and inner2.get("code") == 40901
                   and isinstance(inner2.get("msg"), str)
                   and (inner2.get("data") or {}).get("current_draft_version") == dv1,
                   f"second_put={r2.status_code} code={inner2.get('code')} "
                   f"msg_type={type(inner2.get('msg')).__name__} data={inner2.get('data')}")

            # ====================================================
            # G6-08 发布幂等（Idempotency-Key 24h 去重）
            # ====================================================
            print("\n===== G6-08 发布幂等 =====", flush=True)
            wid8, _, _ = await create_wf(cli, headers, "G6-08发布幂等", graph_linear_templates(1, "p{{query}}"))
            created_wfs.append(wid8)
            idem = {"Idempotency-Key": "G6-08-IDEM-KEY-0001"}
            rp1 = await cli.post(f"/v1/agent/u/workflows/{wid8}/publish", headers={**headers, **idem},
                                 json={"description": "首次发布"})
            p1 = (rp1.json().get("data") or {}) if rp1.status_code == 200 else {}
            rp2 = await cli.post(f"/v1/agent/u/workflows/{wid8}/publish", headers={**headers, **idem},
                                 json={"description": "重复重放"})
            p2 = (rp2.json().get("data") or {}) if rp2.status_code == 200 else {}
            rvs = await cli.get(f"/v1/agent/u/workflows/{wid8}/versions", headers=headers)
            versions = rvs.json().get("data") or []
            record("G6-08a", "首次发布成功 version_no=1",
                   rp1.status_code == 200 and p1.get("version_no") == 1,
                   f"http={rp1.status_code} v={p1.get('version_no')}")
            record("G6-08b", "同 Idempotency-Key 重放：返回原版本（idempotent_replay），不产生新版本",
                   rp2.status_code == 200 and p2.get("version_no") == 1
                   and p2.get("version_id") == p1.get("version_id")
                   and p2.get("idempotent_replay") is True
                   and len(versions) == 1,
                   f"replay_http={rp2.status_code} v2={p2.get('version_no')} "
                   f"replay_flag={p2.get('idempotent_replay')} versions_count={len(versions)}")

            # ====================================================
            # G6-09 Trace 完整性（AC-15/N4-6：seq 单调 + 覆盖 + SSE/trace 一致）
            # ====================================================
            print("\n===== G6-09 Trace 链路完整性 =====", flush=True)
            g9 = graph_linear_templates(3, "t{{query}}")
            wid9, _, _ = await create_wf(cli, headers, "G6-09Trace", g9)
            created_wfs.append(wid9)
            res9 = await dry_run_collect(cli, wid9, headers, inputs={"query": "trace"})
            exec9 = await get_exec(cli, headers, res9["exec_id"])
            trace9 = await get_trace(cli, headers, res9["exec_id"])

            sse_pairs = [(t, (d or {}).get("seq")) for t, d in res9["events"]]
            sse_types = [t for t, _ in sse_pairs]
            sse_seqs = [s for _, s in sse_pairs if isinstance(s, int)]
            seq_monotonic = all(b > a for a, b in zip(sse_seqs, sse_seqs[1:]))
            record("G6-09a", "SSE 事件序列：run_started 首 / run_completed 尾，每节点 started+completed",
                   res9["status"] == 200
                   and sse_types[0] == "run_started" and sse_types[-1] == "run_completed"
                   and all(sse_types.count(f) == 1 for f in ("run_started", "run_completed"))
                   and sum(1 for t in sse_types if t == "node_started") == 5
                   and sum(1 for t in sse_types if t == "node_completed") == 5,
                   f"sse_types={sse_types}")
            record("G6-09b", "SSE seq 全局严格单调递增",
                   len(sse_seqs) == len(sse_pairs) and seq_monotonic,
                   f"seqs={sse_seqs[:6]}...{sse_seqs[-3:]} monotonic={seq_monotonic}")

            tr_types = [e.get("event_type") for e in trace9]
            tr_seqs = [e.get("seq") for e in trace9]
            tr_nodes_started = [e.get("node_id") for e in trace9 if e.get("event_type") == "node_started"]
            record("G6-09c", "Trace API 事件与 SSE 一致：类型序列一致 + seq 集合一致（断线补齐可信）",
                   tr_types == sse_types and sorted(tr_seqs) == sorted(sse_seqs),
                   f"trace_len={len(trace9)} sse_len={len(sse_types)} types_equal={tr_types == sse_types}")
            record("G6-09d", "Trace 节点覆盖与拓扑序一致（s1→t1→t2→t3→e1），执行终态 success",
                   tr_nodes_started == ["s1", "t1", "t2", "t3", "e1"]
                   and exec9.get("status") == "success"
                   and exec9.get("started_at") and exec9.get("completed_at"),
                   f"trace_nodes={tr_nodes_started} exec_status={exec9.get('status')}")

        finally:
            print("\n===== 清理测试工作流 =====", flush=True)
            for wid in created_wfs:
                if wid:
                    try:
                        await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=headers)
                    except Exception:
                        pass
            print(f"[清理完成] 删除 {len([w for w in created_wfs if w])} 个工作流", flush=True)

    # ============================================================
    # 汇总
    # ============================================================
    print("\n===== G6 边界/非功能 汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")


asyncio.run(main())
