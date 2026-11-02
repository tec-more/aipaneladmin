"""
T15 节点3 复测脚本：BUG-T15-008（契约字段优先）+ BUG-T15-009（disabled KB 静默空召回）

复测策略（判别信号 = 失败类型/时序差异，可明确区分「字段被解析」vs「字段未被解析」）：

Part A: BUG-008 契约字段优先
- A1 llm 仅契约字段 model_ref/user_prompt → M_FAIL(127.0.0.1:9) 重试3次 ≈7s+ 后失败
  （若未生效：model_ref=None → "LLM 节点未配置模型" <1s 快速失败）
- A2 llm 旧字段兼容 model_id/prompt → 同样走真实调用重试路径
- A3 rag 仅契约字段 knowledge_base_refs=[KB_NOEMB] → EMBEDDING_UNAVAILABLE
  （若未生效：kb_ids=[] → 交集为空 KB_ACCESS_DENIED）
- A4 rag 旧字段兼容 kb_ids=[KB_NOEMB] → EMBEDDING_UNAVAILABLE
- A5 sub_workflow 仅契约字段 workflow_ref+version_policy=latest+input_mapping+inputs 端口 → 子图成功执行并透出输出
- A6 sub_workflow 旧字段 workflow_id → 校验器契约严格口径（O-01 裁定仅覆盖 llm/rag/hitl）编辑期 422 拦截，
  记录为 O-01-ext 观察项；引擎级兼容由 _retest_t15_bug008_unit.py U-A6/U-A6b 覆盖
- A7 sub_agent 仅契约字段 agent_ref+max_steps+task 端口 → agent 图成功执行
- A8 hitl timeout_minutes=5 + on_timeout=approve → ~300s 超时自动通过 auto_approved=True
  （auto_approved 经 h1→end 端口连线透出到 output_data 直接断言）
- A9 hitl 旧字段兼容 timeout_s=300 + timeout_action=fail → run_paused 且 deadline≈now+300s
  （证明引擎解析旧字段），随后协作式取消快速终态 cancelled（换算边界由单元 U-A9 覆盖）
- A10 on_timeout=escalate → fail 映射（源码静态核对，L294 同一分支，免动态执行）

Part B: BUG-009 disabled KB 显式失败
- B1 disabled KB + 授权 → KB_ACCESS_DENIED 显式快速失败
  （修复前：校验通过 → 运行成功 → chunks=[] 静默空召回）
- B2 混合 [disabled, active] KB → active 保留（不误伤）→ EMBEDDING_UNAVAILABLE
  （证明 granted 路径的 active 过滤精准：剔除 disabled、保留 active）

运行: .venv/Scripts/python.exe tests/_retest_t15_bug008_009.py
"""
import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
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


# ============================================================
# 图构造（Schema v2）
# ============================================================

def _start_node():
    return {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
            "data": {"outputs": [{"name": "query", "type": "string"}]}}


def _end_node(x=400, inputs=None):
    return {"id": "e1", "type": "end", "position": {"x": x, "y": 0},
            "data": {"inputs": inputs or []}}


def graph_llm(config: dict) -> dict:
    return {
        "schema_version": 2,
        "nodes": [
            _start_node(),
            {"id": "l1", "type": "llm", "position": {"x": 200, "y": 0},
             "data": {"config": config,
                      "outputs": [{"name": "answer", "type": "string"}],
                      "inputs": []}},
            _end_node(inputs=[{"name": "answer", "type": "string", "from": "l1.answer"}]),
        ],
        "edges": [
            {"id": "e1", "source": "s1", "target": "l1", "sourceHandle": "out", "targetHandle": "in"},
            {"id": "e2", "source": "l1", "target": "e1", "sourceHandle": "out", "targetHandle": "in"},
        ],
        "variables": [],
    }


def graph_rag(config: dict) -> dict:
    return {
        "schema_version": 2,
        "nodes": [
            _start_node(),
            {"id": "r1", "type": "rag_retrieval", "position": {"x": 200, "y": 0},
             "data": {"config": {**config, "top_k": 5},
                      "inputs": [{"name": "query", "type": "string", "from": "s1.query"}],
                      "outputs": [{"name": "chunks", "type": "array<chunk>"}]}},
            _end_node(),
        ],
        "edges": [
            {"id": "e1", "source": "s1", "target": "r1", "sourceHandle": "out", "targetHandle": "in"},
            {"id": "e2", "source": "r1", "target": "e1", "sourceHandle": "out", "targetHandle": "in"},
        ],
        "variables": [],
    }


def graph_sub(node_type: str, config: dict, input_port: str) -> dict:
    """sub_workflow 必填输入端口 inputs / sub_agent 必填端口 task（校验器 _NODE_REQUIRED_INPUTS）"""
    return {
        "schema_version": 2,
        "nodes": [
            _start_node(),
            {"id": "sub1", "type": node_type, "position": {"x": 200, "y": 0},
             "data": {"config": config,
                      "inputs": [{"name": input_port, "type": "string", "from": "s1.query"}],
                      "outputs": [{"name": "answer", "type": "string"}]}},
            _end_node(inputs=[{"name": "answer", "type": "string", "from": "sub1.answer"}]),
        ],
        "edges": [
            {"id": "e1", "source": "s1", "target": "sub1", "sourceHandle": "out", "targetHandle": "in"},
            {"id": "e2", "source": "sub1", "target": "e1", "sourceHandle": "out", "targetHandle": "in"},
        ],
        "variables": [],
    }


def graph_hitl(config: dict) -> dict:
    """hitl 必填输入端口 context；approved/auto_approved 经 end 连线透出供 output_data 直接断言"""
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


# 子图按父节点必填端口分别声明 start 输出：sub_workflow→inputs、sub_agent→task
SUB_GRAPH_WF = {
    "schema_version": 2,
    "nodes": [
        {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
         "data": {"outputs": [{"name": "inputs", "type": "string"}]}},
        _end_node(x=300, inputs=[{"name": "answer", "type": "string", "from": "s1.inputs"}]),
    ],
    "edges": [
        {"id": "e1", "source": "s1", "target": "e1", "sourceHandle": "out", "targetHandle": "in"},
    ],
    "variables": [],
}

SUB_GRAPH_AGENT = {
    "schema_version": 2,
    "nodes": [
        {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
         "data": {"outputs": [{"name": "task", "type": "string"}]}},
        _end_node(x=300, inputs=[{"name": "answer", "type": "string", "from": "s1.task"}]),
    ],
    "edges": [
        {"id": "e1", "source": "s1", "target": "e1", "sourceHandle": "out", "targetHandle": "in"},
    ],
    "variables": [],
}


# ============================================================
# dry-run SSE 收集
# ============================================================

async def dry_run_collect(cli, wid, headers, timeout=150.0) -> dict:
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
                        "data_text": text.decode("utf-8", "replace")[:2000],
                        "elapsed": time.monotonic() - t0}
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    events.append(line[6:].strip())
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
    except Exception as e:
        return {"status": -1, "exec_id": None, "events": events,
                "data_text": f"{type(e).__name__}: {e}" + "\n".join(data_lines),
                "elapsed": time.monotonic() - t0}
    return {"status": status, "exec_id": exec_id, "events": events,
            "data_text": "\n".join(data_lines), "elapsed": time.monotonic() - t0}


async def create_wf(cli, headers, name, graph) -> int:
    r = await cli.post("/v1/agent/u/workflows", headers=headers,
                       json={"name": name, "graph_json": graph})
    wid = (r.json().get("data") or {}).get("id") if r.status_code == 200 else None
    if not wid:
        print(f"  [建图失败] {name}: {r.status_code} {r.text[:200]}")
    return wid


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
                      params={"limit": 500})
    return ((r.json().get("data") or {}).get("events") or []) if r.status_code == 200 else []


# ============================================================
# 主流程
# ============================================================

async def main():
    from base.common.database import TORTOISE_ORM
    await Tortoise.init(config=TORTOISE_ORM)

    from base.plugins.llm.models.provider import LLMProvider
    from base.plugins.llm.models.model import LLMModel
    from base.plugins.llm.models.api_key import LLMApiKey
    from base.common.authz.models.resource_grant import ResourceGrant
    from base.plugins.agent.models.rag import RAGKnowledgeBase
    from base.plugins.agent.models.agent import Agent
    from base.plugins.agent.models.workflow import WorkflowExecution

    # 预检：试跑并发=1，存在 running/paused 实例说明槽位被占（或 BUG-012 泄漏），先中止
    busy = await WorkflowExecution.filter(
        owner_type="usr", owner_id=1, status__in=["running", "paused"]).all()
    if busy:
        print(f"[预检中止] usr:1 存在 {len(busy)} 个 running/paused 执行实例: "
              f"{[e.id for e in busy]}，请先重启服务清槽再复测", flush=True)
        await Tortoise.close_connections()
        return
    print("[预检通过] 无 running/paused 执行实例，试跑槽位空闲", flush=True)

    headers = {"Authorization": f"Bearer {make_token()}"}
    injected = {"providers": [], "models": [], "keys": [], "grants": [], "kbs": [],
                "agents": [], "wfs": []}

    try:
        # ============================================================
        # Phase 0: 测试数据注入（可逆）
        # ============================================================
        p_fail = await LLMProvider.create(name="T15-008厂商", name_en="openai",
                                          status="active", description="BUG-008 复测注入")
        injected["providers"].append(p_fail.id)
        m_fail = await LLMModel.create(provider=p_fail, model_id="t15-008-unreachable",
                                       model_name="T15-008不可达模型",
                                       endpoint_url="http://127.0.0.1:9", status="active")
        injected["models"].append(m_fail.id)
        k_fail = await LLMApiKey.create(provider=p_fail, model=m_fail,
                                        api_key="sk-t15-008-retest", status="active",
                                        call_mode="openapi")
        injected["keys"].append(k_fail.id)

        kb_disabled = await RAGKnowledgeBase.create(
            name="T15-009停用KB", owner_type="usr", owner_id=1, status="disabled", is_public=False)
        kb_noemb = await RAGKnowledgeBase.create(
            name="T15-008无向量KB", owner_type="usr", owner_id=1, status="active",
            is_public=False, embedding_model_id=None)
        injected["kbs"] += [kb_disabled.id, kb_noemb.id]

        agent_sub = await Agent.create(
            name="T15-008子智能体", owner_type="usr", owner_id=1,
            status="active", graph_definition=SUB_GRAPH_AGENT)
        injected["agents"].append(agent_sub.id)

        for rtype, rid in [("model", m_fail.id), ("kb", kb_disabled.id),
                           ("kb", kb_noemb.id), ("agent", agent_sub.id)]:
            g = await ResourceGrant.create(owner_type="usr", owner_id=1,
                                           resource_type=rtype, resource_id=str(rid),
                                           effect="allow")
            injected["grants"].append(g.id)
        print(f"[注入完成] m_fail={m_fail.id} kb_disabled={kb_disabled.id} "
              f"kb_noemb={kb_noemb.id} agent={agent_sub.id}", flush=True)

        async with httpx.AsyncClient(base_url=BASE, timeout=180.0) as cli:
            # 子工作流：创建 + 发布（供 A5/A6 引用）
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "T15-008子工作流", "graph_json": SUB_GRAPH_WF})
            sub_wf_id = (r.json().get("data") or {}).get("id")
            injected["wfs"].append(sub_wf_id)
            r = await cli.post(f"/v1/agent/u/workflows/{sub_wf_id}/publish",
                               json={"description": "子工作流发布"}, headers=headers)
            sub_pub_ok = r.status_code == 200
            print(f"[子工作流] id={sub_wf_id} publish={r.status_code}", flush=True)
            record("A0", "前置：子工作流创建并发布成功", bool(sub_wf_id) and sub_pub_ok,
                   f"sub_wf_id={sub_wf_id} publish_status={r.status_code}")

            # ========================================================
            # A1 llm 仅契约字段：model_ref / user_prompt
            # ========================================================
            print("\n===== A1 llm 仅契约字段 model_ref/user_prompt =====", flush=True)
            wid = await create_wf(cli, headers, "T15-008-A1契约llm",
                                  graph_llm({"model_ref": str(m_fail.id),
                                             "user_prompt": "say hi"}))
            injected["wfs"].append(wid)
            res = await dry_run_collect(cli, wid, headers)
            # 契约生效 → 走到真实调用 → 连接拒绝 → 重试3次退避 ≈7s+
            record("A1a", "dry-run SSE 建立", res["status"] == 200,
                   f"http={res['status']} exec_id={res['exec_id']}")
            record("A1b", "model_ref 被解析：走真实 LLM 调用并重试（elapsed≥6s），"
                          "而非「未配置模型」快速失败",
                   res["elapsed"] >= 6.0 and "未配置模型" not in res["data_text"],
                   f"elapsed={res['elapsed']:.1f}s data={res['data_text'][:160]}")
            exec_a1 = await get_exec(cli, headers, res["exec_id"])
            record("A1c", "终态 failed（调用不可达模型预期失败，字段解析正确）",
                   exec_a1.get("status") == "failed",
                   f"status={exec_a1.get('status')} err={(exec_a1.get('error_message') or '')[:120]}")

            # ========================================================
            # A2 llm 旧字段兼容：model_id / prompt
            # ========================================================
            print("\n===== A2 llm 旧字段兼容 model_id/prompt =====", flush=True)
            wid = await create_wf(cli, headers, "T15-008-A2兼容llm",
                                  graph_llm({"model_id": str(m_fail.id),
                                             "prompt": "say hi"}))
            injected["wfs"].append(wid)
            res = await dry_run_collect(cli, wid, headers)
            record("A2", "旧字段 model_id/prompt 兼容：走真实调用重试路径（elapsed≥6s）",
                   res["status"] == 200 and res["elapsed"] >= 6.0
                   and "未配置模型" not in res["data_text"],
                   f"http={res['status']} elapsed={res['elapsed']:.1f}s")

            # ========================================================
            # A3 rag 仅契约字段：knowledge_base_refs=[KB_NOEMB]
            # ========================================================
            print("\n===== A3 rag 仅契约字段 knowledge_base_refs =====", flush=True)
            wid = await create_wf(cli, headers, "T15-008-A3契约rag",
                                  graph_rag({"knowledge_base_refs": [kb_noemb.id]}))
            injected["wfs"].append(wid)
            res = await dry_run_collect(cli, wid, headers)
            # 契约生效 → kb_ids=[KB_NOEMB] → 通过访问检查 → EMBEDDING_UNAVAILABLE
            # 契约未生效 → kb_ids=[] → KB_ACCESS_DENIED
            record("A3", "knowledge_base_refs 被解析：报 EMBEDDING_UNAVAILABLE（非 KB_ACCESS_DENIED）",
                   res["status"] == 200 and "EMBEDDING" in res["data_text"].upper()
                   and "KB_ACCESS_DENIED" not in res["data_text"],
                   f"http={res['status']} elapsed={res['elapsed']:.1f}s data={res['data_text'][:160]}")

            # ========================================================
            # A4 rag 旧字段兼容：kb_ids=[KB_NOEMB]
            # ========================================================
            print("\n===== A4 rag 旧字段兼容 kb_ids =====", flush=True)
            wid = await create_wf(cli, headers, "T15-008-A4兼容rag",
                                  graph_rag({"kb_ids": [kb_noemb.id]}))
            injected["wfs"].append(wid)
            res = await dry_run_collect(cli, wid, headers)
            record("A4", "旧字段 kb_ids 兼容：EMBEDDING_UNAVAILABLE",
                   res["status"] == 200 and "EMBEDDING" in res["data_text"].upper(),
                   f"http={res['status']} data={res['data_text'][:160]}")

            # ========================================================
            # A5 sub_workflow 仅契约字段 workflow_ref（PRD §5.8 完整构造）
            # ========================================================
            print("\n===== A5 sub_workflow 仅契约字段 workflow_ref =====", flush=True)
            wid = await create_wf(cli, headers, "T15-008-A5契约subwf",
                                  graph_sub("sub_workflow",
                                            {"workflow_ref": sub_wf_id,
                                             "version_policy": "latest",
                                             "input_mapping": {"inputs": "{{s1.query}}"}},
                                            input_port="inputs"))
            injected["wfs"].append(wid)
            res = await dry_run_collect(cli, wid, headers)
            exec_a5 = await get_exec(cli, headers, res["exec_id"])
            out_a5 = exec_a5.get("output_data") or {}
            record("A5", "workflow_ref 被解析：子工作流执行成功且输出端到端透传 answer=T15复测",
                   res["status"] == 200 and exec_a5.get("status") == "success"
                   and out_a5.get("answer") == "T15复测"
                   and "SUB_WORKFLOW_INVALID" not in res["data_text"],
                   f"http={res['status']} exec_status={exec_a5.get('status')} "
                   f"elapsed={res['elapsed']:.1f}s output={json.dumps(out_a5, ensure_ascii=False)[:150]}")

            # ========================================================
            # A6 sub_workflow 旧字段 workflow_id（O-01-ext 观察项）
            # ========================================================
            print("\n===== A6 sub_workflow 旧字段 workflow_id（校验器契约严格口径记录） =====", flush=True)
            # 创建为草稿非阻断（PRD：问题草稿可保存，试跑/发布才阻断）；契约拦截在 dry-run 前置校验断言
            r6 = await cli.post("/v1/agent/u/workflows", headers=headers,
                                json={"name": "T15-008-A6兼容subwf",
                                      "graph_json": graph_sub("sub_workflow",
                                                              {"workflow_id": sub_wf_id},
                                                              input_port="inputs")})
            wid6 = (r6.json().get("data") or {}).get("id") if r6.status_code == 200 else None
            injected["wfs"].append(wid6)
            res6 = await dry_run_collect(cli, wid6, headers) if wid6 else {"status": -1, "data_text": "create failed"}
            try:
                body6 = json.loads(res6["data_text"]) if res6.get("status") != 200 else {}
            except Exception:
                body6 = {}
            issues6 = ((body6.get("data") or {}).get("issues")) or []
            # O-01-ext 修复后：workflow_id 被兼容 → 不应再有 workflow_ref 缺失项；
            # 仍缺契约必填项 input_mapping/pinned_version → 422 口径保持（兼容精准性）
            no_ref_issue = not any(i.get("code") == "E-100" and i.get("field") == "workflow_ref"
                                   for i in issues6)
            still_strict = {"input_mapping", "pinned_version"}.issubset(
                {str(i.get("field")) for i in issues6})
            record("A6", "O-01-ext 兼容精准性：旧字段 workflow_id 被兼容（不再报 workflow_ref 缺失），"
                         "仍缺契约必填项 input_mapping/pinned_version（422 拦截口径保持）；"
                         "正向兼容与优先级由单元脚本 A6c/A7c/A6p/A7u 覆盖",
                   r6.status_code == 200 and res6.get("status") == 422
                   and body6.get("code") == 42200 and no_ref_issue and still_strict,
                   f"create_http={r6.status_code} dryrun_http={res6.get('status')} "
                   f"code={body6.get('code')} "
                   f"issue_fields={sorted({str(i.get('field')) for i in issues6})}")

            # ========================================================
            # A7 sub_agent 仅契约字段 agent_ref（PRD：max_steps 必填 1-30）
            # ========================================================
            print("\n===== A7 sub_agent 仅契约字段 agent_ref =====", flush=True)
            wid = await create_wf(cli, headers, "T15-008-A7契约subagent",
                                  graph_sub("sub_agent",
                                            {"agent_ref": agent_sub.id, "max_steps": 10},
                                            input_port="task"))
            injected["wfs"].append(wid)
            res = await dry_run_collect(cli, wid, headers)
            exec_a7 = await get_exec(cli, headers, res["exec_id"])
            out_a7 = exec_a7.get("output_data") or {}
            record("A7", "agent_ref 被解析：子智能体执行成功且输出端到端透传 answer=T15复测",
                   res["status"] == 200 and exec_a7.get("status") == "success"
                   and out_a7.get("answer") == "T15复测"
                   and "SUB_AGENT_INVALID" not in res["data_text"],
                   f"http={res['status']} exec_status={exec_a7.get('status')} "
                   f"output={json.dumps(out_a7, ensure_ascii=False)[:150]} "
                   f"data={res['data_text'][:120] if exec_a7.get('status') != 'success' else ''}")

            # ========================================================
            # A8 hitl timeout_minutes=5 + on_timeout=approve → ~300s 自动通过
            # ========================================================
            print("\n===== A8 hitl timeout_minutes=5 + on_timeout=approve（约300s） =====", flush=True)
            wid = await create_wf(cli, headers, "T15-008-A8超时approve",
                                  graph_hitl({"timeout_minutes": 5, "on_timeout": "approve"}))
            injected["wfs"].append(wid)
            res = await dry_run_collect(cli, wid, headers, timeout=400.0)
            exec_a8 = await get_exec(cli, headers, res["exec_id"])
            out_a8 = exec_a8.get("output_data") or {}
            record("A8a", "timeout_minutes=5 被解析：~300s 后超时（非默认72h挂起）",
                   res["status"] == 200 and 290.0 <= res["elapsed"] <= 380.0,
                   f"http={res['status']} elapsed={res['elapsed']:.1f}s ∈[290,380]")
            record("A8b", "on_timeout=approve 生效：超时自动通过 approved/auto_approved=True，执行成功",
                   exec_a8.get("status") == "success" and out_a8.get("auto_approved") is True
                   and out_a8.get("approved") is True,
                   f"exec_status={exec_a8.get('status')} output={json.dumps(out_a8, ensure_ascii=False)[:150]}")

            # ========================================================
            # A9 hitl 旧字段 timeout_s=300 + timeout_action=fail → run_paused 后取消
            # ========================================================
            print("\n===== A9 hitl 旧字段兼容 timeout_s=300 / timeout_action=fail"
                  "（run_paused 后协作式取消） =====", flush=True)
            wid = await create_wf(cli, headers, "T15-008-A9兼容hitl",
                                  graph_hitl({"timeout_s": 300, "timeout_action": "fail"}))
            injected["wfs"].append(wid)
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
                            rc = await cli.post(f"/v1/agent/u/executions/{exec_id_a9}/cancel",
                                                headers=headers)
                            cancel_http = rc.status_code
            elapsed_a9 = time.monotonic() - t0
            exec_a9 = await get_exec(cli, headers, exec_id_a9)
            dl_ok = False
            if paused_deadline:
                try:
                    delta = (datetime.fromisoformat(paused_deadline) - datetime.now()).total_seconds()
                    dl_ok = 240.0 <= delta <= 330.0
                except Exception:
                    pass
            record("A9a", "旧字段 timeout_s=300 被引擎解析：进入 run_paused 且 deadline≈now+300s",
                   http_a9 == 200 and paused_deadline is not None and dl_ok,
                   f"http={http_a9} deadline={paused_deadline} events={events_a9[:6]}")
            record("A9b", "paused 态协作式取消生效：快速终态 cancelled（无需等待 300s 超时）",
                   cancel_http == 200 and exec_a9.get("status") == "cancelled"
                   and elapsed_a9 < 60.0,
                   f"cancel_http={cancel_http} exec_status={exec_a9.get('status')} "
                   f"elapsed={elapsed_a9:.1f}s")

            # ========================================================
            # A10 on_timeout=escalate → fail 映射（源码静态核对）
            # ========================================================
            src = Path("base/plugins/agent/services/engine/nodes.py").read_text(encoding="utf-8")
            record("A10", "on_timeout=escalate → fail 降级映射存在（与 reject 同分支）",
                   'on_timeout in ("reject", "escalate")' in src,
                   "nodes.py L294 静态核对")

            # ========================================================
            # B1 BUG-009：disabled KB + 授权 → 显式 KB_ACCESS_DENIED
            # ========================================================
            print("\n===== B1 disabled KB + 授权 → 显式失败 =====", flush=True)
            wid = await create_wf(cli, headers, "T15-009-B1停用KB",
                                  graph_rag({"knowledge_base_refs": [kb_disabled.id]}))
            injected["wfs"].append(wid)
            res = await dry_run_collect(cli, wid, headers)
            exec_b1 = await get_exec(cli, headers, res["exec_id"])
            # 修复前：运行成功 chunks=[]（静默）；修复后：KB_ACCESS_DENIED 显式失败
            record("B1a", "disabled KB 显式失败 KB_ACCESS_DENIED（非静默空召回）",
                   res["status"] == 200
                   and ("KB_ACCESS_DENIED" in res["data_text"] or "不可访问" in res["data_text"]),
                   f"http={res['status']} elapsed={res['elapsed']:.1f}s data={res['data_text'][:200]}")
            record("B1b", "执行记录终态 failed（非 success+空chunks）",
                   exec_b1.get("status") == "failed",
                   f"exec_status={exec_b1.get('status')} output={json.dumps(exec_b1.get('output_data'), ensure_ascii=False)[:100]}")

            # ========================================================
            # B2 BUG-009 无误伤：混合 [disabled, active] → active 保留
            # ========================================================
            print("\n===== B2 混合KB：disabled剔除、active保留 =====", flush=True)
            wid = await create_wf(cli, headers, "T15-009-B2混合KB",
                                  graph_rag({"knowledge_base_refs": [kb_disabled.id, kb_noemb.id]}))
            injected["wfs"].append(wid)
            res = await dry_run_collect(cli, wid, headers)
            # active(kb_noemb) 保留 → 通过访问检查 → EMBEDDING_UNAVAILABLE
            # 若整体拒绝则 KB_ACCESS_DENIED（说明 active 被误伤）
            record("B2", "active KB 未被误过滤：EMBEDDING_UNAVAILABLE（非整体 KB_ACCESS_DENIED）",
                   res["status"] == 200 and "EMBEDDING" in res["data_text"].upper()
                   and "KB_ACCESS_DENIED" not in res["data_text"],
                   f"http={res['status']} data={res['data_text'][:200]}")

    finally:
        # ============================================================
        # 清理（可逆性保障）
        # ============================================================
        print("\n===== 清理注入数据 =====", flush=True)
        async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as cli:
            for wid in injected["wfs"]:
                if wid:
                    try:
                        await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=headers)
                    except Exception:
                        pass
        await ResourceGrant.filter(id__in=injected["grants"]).delete()
        await Agent.filter(id__in=injected["agents"]).delete()
        await RAGKnowledgeBase.filter(id__in=injected["kbs"]).delete()
        await LLMApiKey.filter(id__in=injected["keys"]).delete()
        await LLMModel.filter(id__in=injected["models"]).delete()
        await LLMProvider.filter(id__in=injected["providers"]).delete()
        await Tortoise.close_connections()
        print("[清理完成]", flush=True)

    # ============================================================
    # 汇总
    # ============================================================
    print("\n===== BUG-008/009 复测汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")
    if passed == len(RESULTS):
        print("结论: BUG-T15-008 契约字段优先修复有效（API 级 6 处 + A6 校验器严格口径记录为 "
              "O-01-ext 观察项，引擎级兼容由单元用例覆盖），"
              "BUG-T15-009 disabled KB 显式失败修复有效且无误伤")


asyncio.run(main())
