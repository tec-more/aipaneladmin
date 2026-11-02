"""
T15 节点4 验收脚本：BUG-T15-011 错误包络契约矩阵 + O-01 校验器旧字段兼容矩阵

前置：服务已重启加载修复代码（logging_config.py / exceptions.py / graph_validator.py）

Part 1 BUG-011（契约 04-§2.3：{code: 业务码, msg: 字符串, data}）：
- E1 乐观锁 409     → 顶层 code=40901，msg str，data.current_draft_version 透传
- E2 并发拦截 429   → 顶层 code=42901，msg str，data.item=concurrency/remaining/estimated
- E3 发布阻断 422   → 顶层 code=42200，msg str，data.issues 为列表（detail 额外字段收拢）
- E4 试跑阻断 422   → 顶层 code=42200，msg str，data.issues 为列表
- E5 存量字符串 detail 行为不变：404 归属不可见 → code=404，msg str，data=null
- E6 未认证 401     → msg 为字符串（不回归成对象）

Part 2 O-01（graph_validator 对齐引擎「契约字段优先 + 旧字段兼容」）：
- V1 llm  legacy model_id + prompt_template → 无 model_ref/user_prompt 缺失 E-100
- V2 llm  legacy model_id + prompt          → 同上（prompt 别名兼容）
- V3 rag  legacy kb_ids                     → 无 knowledge_base_refs 缺失 E-100（E-110 未授权属预期放行）
- V4 rag  knowledge_base_refs=None + kb_ids → or 语义兜底（修复 get-default 不兜底瑕疵）
- V5 hitl legacy timeout_s=300 + timeout_action=fail → 换算 5min ∈[5,10080]，无 E-112
- V6 hitl legacy timeout_s=240（→4min <5）→ E-112 阻断（证明按换算值校验）
- V7 hitl legacy timeout_action=approve → 映射接受，无 on_timeout 类错误
- V8 hitl 契约字段 timeout_minutes/on_timeout 回归 → 通过（契约优先不被兼容逻辑破坏）
- V9 llm  契约字段 model_ref/user_prompt 回归 → 通过

运行: .venv/Scripts/python.exe tests/_t15_node4_accept.py
"""
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from base.common.security import create_access_token

BASE = "http://127.0.0.1:9998"
RESULTS: list[dict] = []


def record(case_id: str, name: str, passed: bool, detail: str):
    RESULTS.append({"id": case_id, "name": name, "pass": passed, "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {case_id} {name} :: {detail}", flush=True)


def make_token(sub="1") -> str:
    return create_access_token({"typ": "usr", "sub": sub}, expires_delta=timedelta(hours=2))


def _start():
    return {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
            "data": {"outputs": [{"name": "query", "type": "string"}]}}


def _end():
    return {"id": "e1", "type": "end", "position": {"x": 400, "y": 0}, "data": {"inputs": []}}


def graph_with(node: dict) -> dict:
    nid = node["id"]
    return {
        "schema_version": 2,
        "nodes": [_start(), node, _end()],
        "edges": [
            {"id": "e1", "source": "s1", "target": nid, "sourceHandle": "out", "targetHandle": "in"},
            {"id": "e2", "source": nid, "target": "e1", "sourceHandle": "out", "targetHandle": "in"},
        ],
        "variables": [{"name": "query", "type": "string"}],
    }


def g_llm(cfg):
    return graph_with({"id": "l1", "type": "llm", "position": {"x": 200, "y": 0},
                       "data": {"config": cfg, "inputs": [],
                                "outputs": [{"name": "answer", "type": "string"}]}})


def g_rag(cfg):
    return graph_with({"id": "r1", "type": "rag_retrieval", "position": {"x": 200, "y": 0},
                       "data": {"config": {**cfg, "top_k": 5},
                                "inputs": [{"name": "query", "type": "string", "from": "s1.query"}],
                                "outputs": [{"name": "chunks", "type": "array<chunk>"}]}})


def g_hitl(cfg):
    return graph_with({"id": "h1", "type": "hitl", "position": {"x": 200, "y": 0},
                       "data": {"config": cfg,
                                "inputs": [{"name": "context", "type": "any", "from": "s1.query"}],
                                "outputs": [{"name": "approved", "type": "boolean"}]}})


def g_simple():
    return graph_with({"id": "t1", "type": "template", "position": {"x": 200, "y": 0},
                       "data": {"config": {"template": "x{{query}}"}, "inputs": [],
                                "outputs": [{"name": "output", "type": "string"}]}})


def g_blocking():
    """双 start → E-100 阻断"""
    g = g_simple()
    g["nodes"].append({"id": "s2", "type": "start", "position": {"x": 0, "y": 100},
                       "data": {"outputs": []}})
    return g


def has_issue(issues, code=None, field=None) -> bool:
    for i in issues or []:
        if code and i.get("code") != code:
            continue
        if field and i.get("field") != field:
            continue
        return True
    return False


async def main():
    headers = {"Authorization": f"Bearer {make_token()}"}
    created: list = []

    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as cli:
        try:
            # ================================================
            # Part 1 BUG-011 错误包络契约矩阵
            # ================================================
            print("\n===== Part 1 BUG-011 错误包络（契约 04-§2.3） =====", flush=True)

            # E1 乐观锁 409
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "N4-E1乐观锁", "graph_json": g_simple()})
            w1 = r.json()["data"]["id"]; created.append(w1)
            rg = await cli.get(f"/v1/agent/u/workflows/{w1}", headers=headers)
            dv0 = rg.json()["data"]["draft_version"]
            await cli.put(f"/v1/agent/u/workflows/{w1}/draft", headers=headers,
                          json={"graph_json": g_simple(), "draft_version": dv0})
            r2 = await cli.put(f"/v1/agent/u/workflows/{w1}/draft", headers=headers,
                               json={"graph_json": g_simple(), "draft_version": dv0})
            b = r2.json()
            record("E1", "乐观锁 409：顶层 code=40901 / msg 字符串 / data.current_draft_version",
                   r2.status_code == 409 and b.get("code") == 40901
                   and isinstance(b.get("msg"), str)
                   and (b.get("data") or {}).get("current_draft_version") == dv0 + 1,
                   f"http={r2.status_code} body={json.dumps(b, ensure_ascii=False)[:220]}")

            # E2 并发 429（hitl 占槽 → 第二试跑 42901）
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "N4-E2占槽", "graph_json": g_hitl(
                                   {"timeout_minutes": 5, "on_timeout": "approve"})})
            wA = r.json()["data"]["id"]; created.append(wA)
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "N4-E2简单", "graph_json": g_simple()})
            wB = r.json()["data"]["id"]; created.append(wB)

            paused = asyncio.Event()
            holder = {"exec": None}

            async def consume():
                async with cli.stream("POST", f"/v1/agent/u/workflows/{wA}/dry-run",
                                      headers=headers, json={"inputs": {"query": "h"}},
                                      timeout=90.0) as ra:
                    holder["exec"] = ra.headers.get("X-Execution-Id")
                    async for line in ra.aiter_lines():
                        if line.startswith("event:") and "run_paused" in line:
                            paused.set()

            task = asyncio.create_task(consume())
            try:
                await asyncio.wait_for(paused.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                pass
            rB = await cli.post(f"/v1/agent/u/workflows/{wB}/dry-run", headers=headers,
                                json={"inputs": {"query": "B"}})
            b2 = rB.json()
            record("E2", "并发拦截 429：顶层 code=42901 / msg 字符串 / data.item=concurrency",
                   rB.status_code == 429 and b2.get("code") == 42901
                   and isinstance(b2.get("msg"), str)
                   and (b2.get("data") or {}).get("item") == "concurrency",
                   f"http={rB.status_code} body={json.dumps(b2, ensure_ascii=False)[:220]}")
            if holder["exec"]:
                await cli.post(f"/v1/agent/u/executions/{holder['exec']}/cancel", headers=headers)
            await task

            # E3 发布阻断 422（双 start 图）
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "N4-E3阻断图", "graph_json": g_blocking()})
            w3 = r.json()["data"]["id"]; created.append(w3)
            rP = await cli.post(f"/v1/agent/u/workflows/{w3}/publish", headers=headers,
                                json={"description": "应被阻断"})
            b3 = rP.json()
            record("E3", "发布阻断 422：顶层 code=42200 / msg 字符串 / data.issues 列表",
                   rP.status_code == 422 and b3.get("code") == 42200
                   and isinstance(b3.get("msg"), str)
                   and isinstance((b3.get("data") or {}).get("issues"), list),
                   f"http={rP.status_code} body={json.dumps(b3, ensure_ascii=False)[:220]}")

            # E4 试跑阻断 422
            rD = await cli.post(f"/v1/agent/u/workflows/{w3}/dry-run", headers=headers,
                                json={"inputs": {"query": "x"}})
            b4 = rD.json()
            record("E4", "试跑阻断 422：顶层 code=42200 / msg 字符串 / data.issues 列表",
                   rD.status_code == 422 and b4.get("code") == 42200
                   and isinstance(b4.get("msg"), str)
                   and isinstance((b4.get("data") or {}).get("issues"), list),
                   f"http={rD.status_code} body={json.dumps(b4, ensure_ascii=False)[:220]}")

            # E5 存量字符串 detail 不变（404 归属不可见）
            r404 = await cli.get("/v1/agent/u/workflows/99999999", headers=headers)
            b5 = r404.json()
            record("E5", "字符串 detail 不变：404 code=404 / msg 字符串 / data=null",
                   r404.status_code == 404 and b5.get("code") == 404
                   and isinstance(b5.get("msg"), str) and b5.get("data") is None,
                   f"http={r404.status_code} body={json.dumps(b5, ensure_ascii=False)[:160]}")

            # E6 未认证 401（无 token）
            r401 = await cli.get("/v1/agent/u/workflows")
            b6 = r401.json()
            record("E6", "未认证 401：msg 为字符串（未回归成嵌套对象）",
                   r401.status_code == 401 and isinstance(b6.get("msg"), str),
                   f"http={r401.status_code} body={json.dumps(b6, ensure_ascii=False)[:160]}")

            # ================================================
            # Part 2 O-01 校验器旧字段兼容矩阵
            # ================================================
            print("\n===== Part 2 O-01 校验器旧字段兼容 =====", flush=True)
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "N4-O01校验宿主", "graph_json": g_simple()})
            host = r.json()["data"]["id"]; created.append(host)

            async def validate(graph) -> dict:
                rv = await cli.post(f"/v1/agent/u/workflows/{host}/validate",
                                    headers=headers, json={"graph_json": graph})
                return (rv.json().get("data") or {}) if rv.status_code == 200 else {}

            # V1 llm legacy model_id + prompt_template
            d = await validate(g_llm({"model_id": "1", "prompt_template": "hi {{query}}"}))
            record("V1", "llm legacy model_id/prompt_template：无 model_ref/user_prompt 缺失报错",
                   not has_issue(d.get("issues"), code="E-100", field="model_ref")
                   and not has_issue(d.get("issues"), code="E-100", field="user_prompt"),
                   f"valid={d.get('valid')} errors={d.get('error_count')}")

            # V2 llm legacy model_id + prompt（更老旧别名）
            d = await validate(g_llm({"model_id": "1", "prompt": "hi {{query}}"}))
            record("V2", "llm legacy model_id/prompt：无缺失报错",
                   not has_issue(d.get("issues"), code="E-100", field="model_ref")
                   and not has_issue(d.get("issues"), code="E-100", field="user_prompt"),
                   f"valid={d.get('valid')} errors={d.get('error_count')}")

            # V3 rag legacy kb_ids（E-110 未授权 kb:999 属预期，不算缺失问题）
            d = await validate(g_rag({"kb_ids": [999]}))
            record("V3", "rag legacy kb_ids：无 knowledge_base_refs 缺失报错（E-110 授权另计）",
                   not has_issue(d.get("issues"), code="E-100", field="knowledge_base_refs"),
                   f"issues={[ (i.get('code'), i.get('field')) for i in (d.get('issues') or []) ]}")

            # V4 rag knowledge_base_refs=None + kb_ids（or 兜底瑕疵修复验证）
            d = await validate(g_rag({"knowledge_base_refs": None, "kb_ids": [999]}))
            record("V4", "rag knowledge_base_refs=None 兜底 kb_ids：无缺失报错",
                   not has_issue(d.get("issues"), code="E-100", field="knowledge_base_refs"),
                   f"issues={[ (i.get('code'), i.get('field')) for i in (d.get('issues') or []) ]}")

            # V5 hitl legacy timeout_s=300（→5min）+ timeout_action=fail
            d = await validate(g_hitl({"timeout_s": 300, "timeout_action": "fail"}))
            record("V5", "hitl legacy timeout_s=300：换算 5min 通过，无 E-112",
                   not has_issue(d.get("issues"), code="E-112"),
                   f"valid={d.get('valid')} issues={[ (i.get('code'), i.get('field')) for i in (d.get('issues') or []) ]}")

            # V6 hitl legacy timeout_s=240（→4min <5）→ E-112 阻断
            d = await validate(g_hitl({"timeout_s": 240, "timeout_action": "fail"}))
            record("V6", "hitl legacy timeout_s=240：换算 4min <5 → E-112 阻断",
                   has_issue(d.get("issues"), code="E-112"),
                   f"valid={d.get('valid')} issues={[ (i.get('code'), i.get('message','')[:40]) for i in (d.get('issues') or []) ]}")

            # V7 hitl legacy timeout_action=approve → 映射接受
            d = await validate(g_hitl({"timeout_s": 300, "timeout_action": "approve"}))
            record("V7", "hitl legacy timeout_action=approve：映射接受，无 on_timeout 错误",
                   not has_issue(d.get("issues"), code="E-100", field="on_timeout")
                   and not has_issue(d.get("issues"), code="E-112"),
                   f"valid={d.get('valid')} issues={[ (i.get('code'), i.get('field')) for i in (d.get('issues') or []) ]}")

            # V8 hitl 契约字段回归
            d = await validate(g_hitl({"timeout_minutes": 5, "on_timeout": "approve"}))
            record("V8", "hitl 契约字段 timeout_minutes/on_timeout 回归通过",
                   not has_issue(d.get("issues"), code="E-112")
                   and not has_issue(d.get("issues"), code="E-100", field="on_timeout"),
                   f"valid={d.get('valid')}")

            # V9 llm 契约字段回归
            d = await validate(g_llm({"model_ref": "1", "user_prompt": "hi {{query}}"}))
            record("V9", "llm 契约字段 model_ref/user_prompt 回归通过",
                   not has_issue(d.get("issues"), code="E-100", field="model_ref")
                   and not has_issue(d.get("issues"), code="E-100", field="user_prompt"),
                   f"valid={d.get('valid')}")

        finally:
            print("\n===== 清理 =====", flush=True)
            for wid in created:
                try:
                    # 有发布态需先停用（E3 图发布被阻断未发布，直接删即可；兜底先尝试停用）
                    await cli.post(f"/v1/agent/u/workflows/{wid}/disable", headers=headers)
                    await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=headers)
                except Exception:
                    pass
            print(f"[清理完成] {len(created)} 个工作流", flush=True)

    print("\n===== 节点4 验收（BUG-011/O-01）汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")


asyncio.run(main())
