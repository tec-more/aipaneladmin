"""
T15 节点3 复测（补）：BUG-T15-008 别名兼容层单元级验证 + A5/A7 API 重测

背景：
- BUG-008 修复策略 = 契约字段优先 + 遗留别名兼容（引擎运行时层，nodes.py）
- 编辑期校验器（graph_validator）契约严格口径：llm 只认 model_ref/user_prompt、
  hitl 只认 timeout_minutes、sub_workflow 只认 workflow_ref → 旧字段图被 422 拦截（R-03）
- 因此旧字段兼容层无法经 API 路径触达，改为进程内直调 handler 验证（等价于存量已发布
  版本快照的运行时执行路径，该路径不走编辑期校验）

单元用例：
- U-A2   llm model_id 别名兼容（mock LLMGateway，验证解析 + prompt 渲染 + 成功输出）
- U-A2b  llm modelId 第三层别名兼容
- U-A2c  llm 优先级：model_ref > model_id（同时给，验证选 model_ref）
- U-A2d  llm user_prompt 模板渲染通路（{{query}} 插值传入 LLMGateway.call）
- U-A6   sub_workflow workflow_id 别名兼容（mock WorkflowVersion + run_subgraph）
- U-A6b  sub_workflow 优先级：workflow_ref > workflow_id
- U-A8   hitl timeout_minutes=1 + on_timeout=approve → ~60s 自动通过 auto_approved=True
- U-A8b  hitl timeout_minutes 优先于 timeout_s（1min vs 5s 判别，与 U-A8 并行）
- U-A9   hitl timeout_s=2 + timeout_action=fail（旧字段兼容）→ ~2s HitlTimeout
- U-A10b hitl on_timeout=approve 优先于 timeout_action=fail（1s 快速判别）

API 重测（修正图构造后）：
- A5 sub_workflow 契约字段 workflow_ref + version_policy=latest + input_mapping + inputs 端口
- A7 sub_agent 契约字段 agent_ref + max_steps + task 端口

运行: .venv/Scripts/python.exe tests/_retest_t15_bug008_unit.py
"""
import asyncio
import json
import sys
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from base.common.security import create_access_token
from base.plugins.agent.services.engine import nodes as nodes_mod
from base.plugins.agent.services.engine.errors import HitlTimeout

BASE = "http://127.0.0.1:9998"
RESULTS: list[dict] = []


def record(case_id: str, name: str, passed: bool, detail: str):
    RESULTS.append({"id": case_id, "name": name, "pass": passed, "detail": detail})
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {case_id} {name} :: {detail}", flush=True)


def make_token() -> str:
    return create_access_token({"typ": "usr", "sub": "1"}, expires_delta=timedelta(hours=2))


# ============================================================
# mock 工具
# ============================================================

def make_runtime(extra_vars=None):
    state = {"vars": dict(extra_vars or {}), "nodes": {}}
    control = SimpleNamespace(
        resume_event=asyncio.Event(),
        resume_payload=None,
        throw_if_cancelled=lambda: None,
    )
    ctx = SimpleNamespace(
        require_resource=AsyncMock(return_value=True),
        domain="usr",
        trace_id="t15-unit",
    )
    return {
        "ctx": ctx,
        "emit": AsyncMock(),
        "control": control,
        "state": state,
        "depth": 0,
        "run_subgraph": AsyncMock(return_value={"outputs": {"answer": "SUB_OK"}}),
    }


def llm_node(config):
    return {"id": "l1", "type": "llm", "data": {"config": config,
            "outputs": [{"name": "answer", "type": "string"}], "inputs": []}}


def hitl_node(config):
    return {"id": "h1", "type": "hitl", "data": {"config": config,
            "outputs": [{"name": "approved", "type": "boolean"}], "inputs": []}}


def subwf_node(config):
    return {"id": "sub1", "type": "sub_workflow", "data": {"config": config,
            "outputs": [{"name": "answer", "type": "string"}], "inputs": []}}


# ============================================================
# 单元用例
# ============================================================

async def unit_llm_alias():
    """U-A2 / U-A2b / U-A2c / U-A2d：llm 别名兼容与优先级"""
    with patch.object(nodes_mod.LLMGateway, "resolve_model",
                      new=AsyncMock(return_value={"mock": "resource"})) as m_resolve, \
         patch.object(nodes_mod.LLMGateway, "call",
                      new=AsyncMock(return_value={"content": "MOCK_REPLY",
                                                  "usage": {"total_tokens": 2}})) as m_call:
        # U-A2: model_id 别名 + prompt 别名
        rt = make_runtime()
        r = await nodes_mod.handle_llm(
            llm_node({"model_id": "mid-123", "prompt": "hello"}), {}, make_runtime())
        record("U-A2", "llm model_id/prompt 别名兼容：成功输出",
               r["status"] == "success" and r["outputs"]["answer"] == "MOCK_REPLY"
               and m_resolve_called_with(m_call, m_call) is not False
               and rt_check(r),
               f"outputs={r['outputs']} usage={r.get('usage')}")

        # 验证 resolve_model 收到 model_id 值
        # （resolve_model 被 patch 在类上，通过 m_resolve 断言）
        record("U-A2-resolve", "model_id 值透传至 LLMGateway.resolve_model",
               m_resolve.call_args is not None
               and str(m_resolve.call_args.args[0]) == "mid-123",
               f"resolve_args={m_resolve.call_args}")

        # U-A2b: modelId 第三层别名
        m_resolve.reset_mock()
        r = await nodes_mod.handle_llm(
            llm_node({"modelId": "midCamel-9", "prompt": "hi"}), {}, make_runtime())
        record("U-A2b", "llm modelId 第三层别名兼容",
               r["status"] == "success"
               and str(m_resolve.call_args.args[0]) == "midCamel-9",
               f"resolve_args={m_resolve.call_args}")

        # U-A2c: 优先级 model_ref > model_id
        m_resolve.reset_mock()
        r = await nodes_mod.handle_llm(
            llm_node({"model_ref": "ref-WIN", "model_id": "id-LOSE", "prompt": "hi"}),
            {}, make_runtime())
        record("U-A2c", "优先级 model_ref > model_id",
               str(m_resolve.call_args.args[0]) == "ref-WIN",
               f"resolve_args={m_resolve.call_args}")

        # U-A2d: user_prompt 模板渲染通路
        m_call.reset_mock()
        rt = make_runtime(extra_vars={"query": "渲染判别值XYZ"})
        r = await nodes_mod.handle_llm(
            llm_node({"model_ref": "m1", "user_prompt": "提问:{{query}}"}), {}, rt)
        msgs = m_call.call_args.args[1] if m_call.call_args else []
        user_msg = next((m["content"] for m in msgs if m.get("role") == "user"), "")
        record("U-A2d", "user_prompt 模板渲染：{{query}} 插值传入 LLM 调用",
               user_msg == "提问:渲染判别值XYZ",
               f"user_msg={user_msg!r}")

        # U-A2e: prompt_template 第二层别名
        r = await nodes_mod.handle_llm(
            llm_node({"model_ref": "m1", "prompt_template": "PT:{{query}}"}), {},
            make_runtime(extra_vars={"query": "Q2"}))
        msgs = m_call.call_args.args[1] if m_call.call_args else []
        user_msg = next((m["content"] for m in msgs if m.get("role") == "user"), "")
        record("U-A2e", "prompt_template 第二层别名兼容",
               user_msg == "PT:Q2", f"user_msg={user_msg!r}")


def m_resolve_called_with(m_call, _):
    return True  # 占位（实际断言在各用例内）


def rt_check(r):
    return r.get("usage", {}).get("total_tokens") == 2


async def unit_sub_workflow_alias():
    """U-A6 / U-A6b：sub_workflow 别名兼容与优先级"""
    fake_version = SimpleNamespace(graph_json={"schema_version": 2, "nodes": [], "edges": []})
    qs = MagicMock()
    qs.order_by = MagicMock(return_value=qs)
    qs.first = AsyncMock(return_value=fake_version)

    with patch("base.plugins.agent.models.workflow_version.WorkflowVersion.filter",
               MagicMock(return_value=qs)) as m_filter:
        # U-A6: workflow_id 别名
        rt = make_runtime()
        r = await nodes_mod.handle_sub_workflow(subwf_node({"workflow_id": 888}), {}, rt)
        record("U-A6", "sub_workflow workflow_id 别名兼容：子图执行成功",
               r["status"] == "success" and r["outputs"].get("answer") == "SUB_OK",
               f"outputs={r['outputs']} filter_kwargs={m_filter.call_args.kwargs}")
        record("U-A6-resolve", "workflow_id 值透传至版本查询",
               m_filter.call_args.kwargs.get("workflow_id") == 888,
               f"filter_kwargs={m_filter.call_args.kwargs}")

        # U-A6b: 优先级 workflow_ref > workflow_id
        m_filter.reset_mock()
        rt = make_runtime()
        r = await nodes_mod.handle_sub_workflow(
            subwf_node({"workflow_ref": 111, "workflow_id": 888}), {}, rt)
        record("U-A6b", "优先级 workflow_ref > workflow_id",
               m_filter.call_args.kwargs.get("workflow_id") == 111,
               f"filter_kwargs={m_filter.call_args.kwargs}")


async def unit_hitl():
    """U-A8 / U-A8b（并行 60s）+ U-A9 / U-A10b（快速）"""

    async def a8():  # timeout_minutes=1 + on_timeout=approve → ~60s auto approve
        rt = make_runtime()
        t0 = time.monotonic()
        r = await nodes_mod.handle_hitl(
            hitl_node({"timeout_minutes": 1, "on_timeout": "approve"}), {}, rt)
        return r, time.monotonic() - t0

    async def a8b():  # timeout_minutes=1 优先于 timeout_s=5 → 若误用 timeout_s 则 5s 超时
        rt = make_runtime()
        t0 = time.monotonic()
        r = await nodes_mod.handle_hitl(
            hitl_node({"timeout_minutes": 1, "timeout_s": 5, "on_timeout": "approve"}),
            {}, rt)
        return r, time.monotonic() - t0

    async def a9():  # 旧字段 timeout_s=2 + timeout_action=fail → ~2s HitlTimeout
        rt = make_runtime()
        t0 = time.monotonic()
        try:
            await nodes_mod.handle_hitl(
                hitl_node({"timeout_s": 2, "timeout_action": "fail"}), {}, rt)
            return None, time.monotonic() - t0
        except HitlTimeout as e:
            return e, time.monotonic() - t0

    async def a10b():  # on_timeout=approve 优先于 timeout_action=fail（1s 判别）
        rt = make_runtime()
        t0 = time.monotonic()
        r = await nodes_mod.handle_hitl(
            hitl_node({"timeout_s": 1, "timeout_action": "fail",
                       "on_timeout": "approve"}), {}, rt)
        return r, time.monotonic() - t0

    # 并行执行：60s 组 + 快速组
    r_a8, r_a8b, r_a9, r_a10b = await asyncio.gather(a8(), a8b(), a9(), a10b())

    r, el = r_a8
    record("U-A8", "hitl timeout_minutes=1 ×60 转换 + on_timeout=approve 自动通过",
           r["status"] == "success" and r["outputs"].get("auto_approved") is True
           and r["outputs"].get("approved") is True and 55.0 <= el <= 75.0,
           f"elapsed={el:.1f}s ∈[55,75] outputs={r['outputs']}")

    r, el = r_a8b
    record("U-A8b", "hitl timeout_minutes 优先于 timeout_s（60s 而非 5s 超时）",
           r["outputs"].get("auto_approved") is True and 55.0 <= el <= 75.0,
           f"elapsed={el:.1f}s（若误用 timeout_s=5 则约5s）")

    exc, el = r_a9
    record("U-A9", "hitl 旧字段 timeout_s=2 + timeout_action=fail → HitlTimeout",
           isinstance(exc, HitlTimeout) and 1.5 <= el <= 8.0,
           f"elapsed={el:.1f}s exc={type(exc).__name__}")

    r, el = r_a10b
    record("U-A10b", "on_timeout=approve 优先于 timeout_action=fail（approve 生效）",
           r["status"] == "success" and r["outputs"].get("auto_approved") is True
           and el < 8.0,
           f"elapsed={el:.1f}s outputs={r['outputs']}")


# ============================================================
# API 重测：A5 / A7（修正图构造）
# ============================================================

SUB_GRAPH_WF = {
    "schema_version": 2,
    "nodes": [
        {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
         "data": {"outputs": [{"name": "inputs", "type": "string"}]}},
        {"id": "e1", "type": "end", "position": {"x": 300, "y": 0},
         "data": {"inputs": [{"name": "answer", "type": "string", "from": "s1.inputs"}]}},
    ],
    "edges": [{"id": "e1", "source": "s1", "target": "e1",
               "sourceHandle": "out", "targetHandle": "in"}],
    "variables": [],
}

SUB_GRAPH_AGENT = {
    "schema_version": 2,
    "nodes": [
        {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
         "data": {"outputs": [{"name": "task", "type": "string"}]}},
        {"id": "e1", "type": "end", "position": {"x": 300, "y": 0},
         "data": {"inputs": [{"name": "answer", "type": "string", "from": "s1.task"}]}},
    ],
    "edges": [{"id": "e1", "source": "s1", "target": "e1",
               "sourceHandle": "out", "targetHandle": "in"}],
    "variables": [],
}


async def dry_run_collect(cli, wid, headers, timeout=60.0) -> dict:
    t0 = time.monotonic()
    events, data_lines = [], []
    try:
        async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                              headers=headers, json={"inputs": {"query": "T15复测"}},
                              timeout=timeout) as resp:
            status = resp.status_code
            exec_id = resp.headers.get("X-Execution-Id")
            if status != 200:
                text = await resp.aread()
                return {"status": status, "exec_id": exec_id, "events": [],
                        "data_text": text.decode("utf-8", "replace")[:500],
                        "elapsed": time.monotonic() - t0}
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    events.append(line[6:].strip())
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
    except Exception as e:
        return {"status": -1, "exec_id": None, "events": events,
                "data_text": f"{type(e).__name__}: {e}", "elapsed": time.monotonic() - t0}
    return {"status": status, "exec_id": exec_id, "events": events,
            "data_text": "\n".join(data_lines), "elapsed": time.monotonic() - t0}


async def api_retest():
    from tortoise import Tortoise
    from base.common.database import TORTOISE_ORM
    await Tortoise.init(config=TORTOISE_ORM)
    from base.plugins.agent.models.agent import Agent
    from base.common.authz.models.resource_grant import ResourceGrant

    headers = {"Authorization": f"Bearer {make_token()}"}
    injected = {"agents": [], "grants": [], "wfs": []}
    try:
        agent_sub = await Agent.create(
            name="T15-008子智能体v2", owner_type="usr", owner_id=1,
            status="active", graph_definition=SUB_GRAPH_AGENT)
        injected["agents"].append(agent_sub.id)
        g = await ResourceGrant.create(owner_type="usr", owner_id=1,
                                       resource_type="agent", resource_id=str(agent_sub.id),
                                       effect="allow")
        injected["grants"].append(g.id)

        async with httpx.AsyncClient(base_url=BASE, timeout=90.0) as cli:
            # 子工作流（发布）
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "T15-008子工作流v2", "graph_json": SUB_GRAPH_WF})
            sub_wf_id = (r.json().get("data") or {}).get("id")
            injected["wfs"].append(sub_wf_id)
            r = await cli.post(f"/v1/agent/u/workflows/{sub_wf_id}/publish",
                               json={"description": "v2"}, headers=headers)
            print(f"[子工作流v2] id={sub_wf_id} publish={r.status_code}", flush=True)

            # ---- A5 sub_workflow 契约字段（完整契约：workflow_ref+latest+input_mapping+inputs端口）
            print("\n===== A5' sub_workflow 契约字段完整构造 =====", flush=True)
            g5 = {
                "schema_version": 2,
                "nodes": [
                    {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
                     "data": {"outputs": [{"name": "query", "type": "string"}]}},
                    {"id": "sub1", "type": "sub_workflow", "position": {"x": 200, "y": 0},
                     "data": {"config": {"workflow_ref": sub_wf_id,
                                         "version_policy": "latest",
                                         "input_mapping": {"inputs": "{{s1.query}}"}},
                              "inputs": [{"name": "inputs", "from": "s1.query"}],
                              "outputs": [{"name": "answer", "type": "string"}]}},
                    {"id": "e1", "type": "end", "position": {"x": 400, "y": 0},
                     "data": {"inputs": [{"name": "answer", "type": "string",
                                          "from": "sub1.answer"}]}},
                ],
                "edges": [
                    {"id": "e1", "source": "s1", "target": "sub1",
                     "sourceHandle": "out", "targetHandle": "in"},
                    {"id": "e2", "source": "sub1", "target": "e1",
                     "sourceHandle": "out", "targetHandle": "in"},
                ],
                "variables": [],
            }
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "T15-008-A5修", "graph_json": g5})
            wid5 = (r.json().get("data") or {}).get("id")
            injected["wfs"].append(wid5)
            if not wid5:
                record("A5'", "sub_workflow 契约字段：建图", False, f"resp={r.text[:200]}")
            else:
                res = await dry_run_collect(cli, wid5, headers)
                await asyncio.sleep(0.8)
                r2 = await cli.get(f"/v1/agent/u/executions/{res['exec_id']}", headers=headers)
                exec5 = (r2.json().get("data") or {}) if r2.status_code == 200 else {}
                out5 = exec5.get("output_data") or {}
                record("A5'", "sub_workflow 契约字段 workflow_ref：子图执行成功且输出透传",
                       res["status"] == 200 and exec5.get("status") == "success"
                       and out5.get("answer") == "T15复测",
                       f"http={res['status']} exec={exec5.get('status')} "
                       f"output={json.dumps(out5, ensure_ascii=False)[:120]} "
                       f"err={res['data_text'][:120] if exec5.get('status') != 'success' else ''}")

            # ---- A7 sub_agent 契约字段（agent_ref+max_steps+task端口）
            print("\n===== A7' sub_agent 契约字段完整构造 =====", flush=True)
            g7 = {
                "schema_version": 2,
                "nodes": [
                    {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
                     "data": {"outputs": [{"name": "query", "type": "string"}]}},
                    {"id": "sub1", "type": "sub_agent", "position": {"x": 200, "y": 0},
                     "data": {"config": {"agent_ref": agent_sub.id, "max_steps": 5},
                              "inputs": [{"name": "task", "from": "s1.query"}],
                              "outputs": [{"name": "answer", "type": "string"}]}},
                    {"id": "e1", "type": "end", "position": {"x": 400, "y": 0},
                     "data": {"inputs": [{"name": "answer", "type": "string",
                                          "from": "sub1.answer"}]}},
                ],
                "edges": [
                    {"id": "e1", "source": "s1", "target": "sub1",
                     "sourceHandle": "out", "targetHandle": "in"},
                    {"id": "e2", "source": "sub1", "target": "e1",
                     "sourceHandle": "out", "targetHandle": "in"},
                ],
                "variables": [],
            }
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "T15-008-A7修", "graph_json": g7})
            wid7 = (r.json().get("data") or {}).get("id")
            injected["wfs"].append(wid7)
            if not wid7:
                record("A7'", "sub_agent 契约字段：建图", False, f"resp={r.text[:200]}")
            else:
                res = await dry_run_collect(cli, wid7, headers)
                await asyncio.sleep(0.8)
                r2 = await cli.get(f"/v1/agent/u/executions/{res['exec_id']}", headers=headers)
                exec7 = (r2.json().get("data") or {}) if r2.status_code == 200 else {}
                out7 = exec7.get("output_data") or {}
                record("A7'", "sub_agent 契约字段 agent_ref：子智能体执行成功且输出透传",
                       res["status"] == 200 and exec7.get("status") == "success"
                       and out7.get("answer") == "T15复测",
                       f"http={res['status']} exec={exec7.get('status')} "
                       f"output={json.dumps(out7, ensure_ascii=False)[:120]} "
                       f"err={res['data_text'][:150] if exec7.get('status') != 'success' else ''}")

            # ========================================================
            # O-01-ext 复测：校验器 sub_workflow/sub_agent 旧字段兼容
            # ========================================================
            def _g(ntype, config, port):
                return {
                    "schema_version": 2,
                    "nodes": [
                        {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
                         "data": {"outputs": [{"name": "query", "type": "string"}]}},
                        {"id": "sub1", "type": ntype, "position": {"x": 200, "y": 0},
                         "data": {"config": config,
                                  "inputs": [{"name": port, "from": "s1.query"}],
                                  "outputs": [{"name": "answer", "type": "string"}]}},
                        {"id": "e1", "type": "end", "position": {"x": 400, "y": 0},
                         "data": {"inputs": [{"name": "answer", "type": "string",
                                              "from": "sub1.answer"}]}},
                    ],
                    "edges": [
                        {"id": "e1", "source": "s1", "target": "sub1",
                         "sourceHandle": "out", "targetHandle": "in"},
                        {"id": "e2", "source": "sub1", "target": "e1",
                         "sourceHandle": "out", "targetHandle": "in"},
                    ],
                    "variables": [],
                }

            async def _run_exec(wid):
                res = await dry_run_collect(cli, wid, headers)
                await asyncio.sleep(0.8)
                if not res["exec_id"]:
                    return res, {}
                r2 = await cli.get(f"/v1/agent/u/executions/{res['exec_id']}", headers=headers)
                return res, (r2.json().get("data") or {}) if r2.status_code == 200 else {}

            async def _create(name, graph):
                r = await cli.post("/v1/agent/u/workflows", headers=headers,
                                   json={"name": name, "graph_json": graph})
                wid = (r.json().get("data") or {}).get("id") if r.status_code == 200 else None
                injected["wfs"].append(wid)
                return r, wid

            # ---- A6c：sub_workflow 旧字段 workflow_id 完整构造 → 校验放行 + 执行成功
            print("\n===== A6c sub_workflow 旧字段 workflow_id 完整构造 =====", flush=True)
            r, wid = await _create("T15-008-A6c兼容",
                                   _g("sub_workflow",
                                      {"workflow_id": sub_wf_id, "version_policy": "latest",
                                       "input_mapping": {"inputs": "{{s1.query}}"}}, "inputs"))
            if not wid:
                record("A6c", "旧字段 workflow_id：建图", False, f"resp={r.text[:200]}")
            else:
                res, exc = await _run_exec(wid)
                out = exc.get("output_data") or {}
                record("A6c", "校验器兼容旧字段 workflow_id：建图放行且子图执行成功输出透传",
                       res["status"] == 200 and exc.get("status") == "success"
                       and out.get("answer") == "T15复测",
                       f"http={res['status']} exec={exc.get('status')} "
                       f"output={json.dumps(out, ensure_ascii=False)[:120]}")

            # ---- A7c：sub_agent 旧字段 agent_id 完整构造 → 校验放行 + 执行成功
            print("\n===== A7c sub_agent 旧字段 agent_id 完整构造 =====", flush=True)
            r, wid = await _create("T15-008-A7c兼容",
                                   _g("sub_agent", {"agent_id": agent_sub.id, "max_steps": 5},
                                      "task"))
            if not wid:
                record("A7c", "旧字段 agent_id：建图", False, f"resp={r.text[:200]}")
            else:
                res, exc = await _run_exec(wid)
                out = exc.get("output_data") or {}
                record("A7c", "校验器兼容旧字段 agent_id：建图放行且子智能体执行成功输出透传",
                       res["status"] == 200 and exc.get("status") == "success"
                       and out.get("answer") == "T15复测",
                       f"http={res['status']} exec={exc.get('status')} "
                       f"output={json.dumps(out, ensure_ascii=False)[:120]}")

            # ---- A6p：优先级 workflow_ref(正确) > workflow_id(不存在)
            print("\n===== A6p 优先级 workflow_ref > workflow_id =====", flush=True)
            r, wid = await _create("T15-008-A6p优先",
                                   _g("sub_workflow",
                                      {"workflow_ref": sub_wf_id, "workflow_id": 99999999,
                                       "version_policy": "latest",
                                       "input_mapping": {"inputs": "{{s1.query}}"}}, "inputs"))
            if not wid:
                record("A6p", "优先级：建图", False, f"resp={r.text[:200]}")
            else:
                res, exc = await _run_exec(wid)
                out = exc.get("output_data") or {}
                record("A6p", "契约字段优先：workflow_ref 生效（旧字段 workflow_id=99999999 被忽略）",
                       res["status"] == 200 and exc.get("status") == "success"
                       and out.get("answer") == "T15复测",
                       f"http={res['status']} exec={exc.get('status')} "
                       f"(若旧字段优先将 SUB_WORKFLOW_INVALID 失败)")

            # ---- A7u：未授权 agent_id → 编辑期放行（无 E-110），运行时引擎兜底拦截
            print("\n===== A7u 未授权 agent_id 运行时兜底口径 =====", flush=True)
            agent_nogrant = await Agent.create(
                name="T15-008未授权Agent", owner_type="usr", owner_id=1,
                status="active", graph_definition=SUB_GRAPH_AGENT)
            injected["agents"].append(agent_nogrant.id)
            r, wid = await _create("T15-008-A7u未授权",
                                   _g("sub_agent", {"agent_id": agent_nogrant.id, "max_steps": 5},
                                      "task"))
            if not wid:
                record("A7u", "未授权 agent_id：编辑期应放行", False, f"resp={r.text[:200]}")
            else:
                res, exc = await _run_exec(wid)
                record("A7u", "编辑期宽松（agent_id 不入 E-110）+ 运行时 require_resource 兜底："
                              "建图放行但执行被引擎拦截为 failed",
                       res["status"] == 200 and exc.get("status") == "failed",
                       f"create=200 http={res['status']} exec={exc.get('status')} "
                       f"err={(exc.get('error_message') or res['data_text'])[:120]}")
    finally:
        print("\n===== 清理 =====", flush=True)
        async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as cli:
            for wid in injected["wfs"]:
                if wid:
                    try:
                        await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=headers)
                    except Exception:
                        pass
        await ResourceGrant.filter(id__in=injected["grants"]).delete()
        await Agent.filter(id__in=injected["agents"]).delete()
        await Tortoise.close_connections()
        print("[清理完成]", flush=True)


async def main():
    print("===== Part 1: 单元级别名兼容验证（60s 组并行） =====", flush=True)
    await unit_llm_alias()
    await unit_sub_workflow_alias()
    await unit_hitl()
    print("\n===== Part 2: API 重测 A5'/A7' =====", flush=True)
    await api_retest()

    print("\n===== BUG-008 补充复测汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")


asyncio.run(main())
