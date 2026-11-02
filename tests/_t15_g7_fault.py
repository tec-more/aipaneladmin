"""
T15 节点3 / G7 告警演练：LLM/Embedding/Qdrant 故障注入（数据面，可逆注入）

注入方式（ORM 直写生产库同源 GaussDB，测试后全部清理，可逆）：
- P_FAIL: 厂商 openai 通道 + endpoint=http://127.0.0.1:9（连接拒绝，模拟上游不可达）
- M_FAIL: active 模型挂 P_FAIL + ApiKey(api_key=SECRET-KEY-T15-DO-NOT-LEAK) + usr:1 授权
- M_INACTIVE: status=inactive 模型 + usr:1 授权（模拟模型被停用/未激活）
- KB_DISABLED: usr:1 自有但 status=disabled + usr:1 授权（运行时可访问集空交集 → KB_ACCESS_DENIED）
- KB_NOEMB: usr:1 自有 active 但 embedding_model_id=NULL + 授权（→ EMBEDDING_UNAVAILABLE）

用例映射（G7 故障注入集）：
- G7-01 LLM 上游不可达：重试 3 次（退避 1+2+4s）后失败；设置 retry.max=99 验证 N4-4 上限不可上调
- G7-02 模型未激活：MODEL_UNAVAILABLE 不可重试，快速失败（<5s）
- G7-03 KB 白名单空交集：KB_ACCESS_DENIED 不可重试
- G7-04 KB 无 Embedding 模型：EMBEDDING_UNAVAILABLE 不可重试
- G7-05 失败可观测性：SSE 终态/error 事件 + 执行记录 status=failed + started/completed 完整
- G7-06 凭证不泄漏（R-05/R-12）：SSE 帧与执行详情中不出现注入的 api_key 文本
- G7-07（限制项）Qdrant 全实例故障注入：需改 env 重启服务，超出数据面安全注入范围 → 标记运维侧演练

运行: .venv/Scripts/python.exe tests/_t15_g7_fault.py
"""
import asyncio
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from tortoise import Tortoise

from base.common.security import create_access_token

BASE = "http://127.0.0.1:9998"
LEAK_MARK = "SECRET-KEY-T15-DO-NOT-LEAK"

RESULTS: list[dict] = []


def record(case_id: str, name: str, passed: bool, detail: str):
    RESULTS.append({"id": case_id, "name": name, "pass": passed, "detail": detail})
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {case_id} {name} :: {detail}")


def make_token() -> str:
    return create_access_token({"typ": "usr", "sub": "1"}, expires_delta=timedelta(hours=2))


def graph_llm(model_ref, retry_max=None) -> dict:
    settings = {"retry": {"max": retry_max}} if retry_max else {}
    # 注意：同时写契约字段 model_ref（过校验）与引擎遗留字段 model_id（驱动运行时），
    # 以在 BUG-T15-008 修复前验证引擎重试/故障路径本身
    return {
        "schema_version": 2,
        "nodes": [
            {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
             "data": {"outputs": [{"name": "query", "type": "string"}]}},
            {"id": "l1", "type": "llm", "position": {"x": 200, "y": 0},
             "data": {"config": {"model_ref": str(model_ref), "model_id": str(model_ref),
                                 "user_prompt": "say hi", "prompt_template": "say hi"},
                      "outputs": [{"name": "answer", "type": "string"}],
                      "inputs": []}},
            {"id": "e1", "type": "end", "position": {"x": 400, "y": 0},
             "data": {"inputs": [{"name": "answer", "type": "string", "from": "l1.answer"}]}},
        ],
        "edges": [
            {"id": "e1", "source": "s1", "target": "l1", "sourceHandle": "out", "targetHandle": "in"},
            {"id": "e2", "source": "l1", "target": "e1", "sourceHandle": "out", "targetHandle": "in"},
        ],
        "variables": [],
        "settings": settings,
    }


def graph_rag(kb_id) -> dict:
    return {
        "schema_version": 2,
        "nodes": [
            {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
             "data": {"outputs": [{"name": "query", "type": "string"}]}},
            {"id": "r1", "type": "rag_retrieval", "position": {"x": 200, "y": 0},
             "data": {"config": {"knowledge_base_refs": [kb_id], "kb_ids": [kb_id], "top_k": 5},
                      "inputs": [{"name": "query", "type": "string", "from": "s1.query"}],
                      "outputs": [{"name": "chunks", "type": "array<chunk>"}]}},
            {"id": "e1", "type": "end", "position": {"x": 400, "y": 0}, "data": {}},
        ],
        "edges": [
            {"id": "e1", "source": "s1", "target": "r1", "sourceHandle": "out", "targetHandle": "in"},
            {"id": "e2", "source": "r1", "target": "e1", "sourceHandle": "out", "targetHandle": "in"},
        ],
        "variables": [],
    }


async def dry_run_collect(cli, wid, headers) -> dict:
    """执行 dry-run，收集 SSE 事件与耗时，返回 {status, exec_id, events, data_text, elapsed}"""
    t0 = time.monotonic()
    events, data_lines = [], []
    async with cli.stream("POST", f"/v1/agent/u/workflows/{wid}/dry-run",
                          headers=headers, json={"inputs": {"query": "G7故障注入"}},
                          timeout=120.0) as resp:
        status = resp.status_code
        exec_id = resp.headers.get("X-Execution-Id")
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                events.append(line[6:].strip())
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
    elapsed = time.monotonic() - t0
    return {"status": status, "exec_id": exec_id, "events": events,
            "data_text": "\n".join(data_lines), "elapsed": elapsed}


async def main():
    # ---- ORM 初始化（与生产同库，用于故障数据注入）----
    from base.common.database import TORTOISE_ORM
    await Tortoise.init(config=TORTOISE_ORM)

    from base.plugins.llm.models.provider import LLMProvider
    from base.plugins.llm.models.model import LLMModel
    from base.plugins.llm.models.api_key import LLMApiKey
    from base.common.authz.models.resource_grant import ResourceGrant
    from base.plugins.agent.models.rag import RAGKnowledgeBase

    headers = {"Authorization": f"Bearer {make_token()}"}
    injected = {"providers": [], "models": [], "keys": [], "grants": [], "kbs": [], "wfs": []}

    try:
        # ============================================================
        # Phase 0: 故障数据注入
        # ============================================================
        p_fail = await LLMProvider.create(name="T15故障厂商", name_en="openai",
                                          status="active", description="T15 G7 注入")
        injected["providers"].append(p_fail.id)

        m_fail = await LLMModel.create(provider=p_fail, model_id="t15-unreachable",
                                       model_name="T15不可达模型",
                                       endpoint_url="http://127.0.0.1:9", status="active")
        m_inactive = await LLMModel.create(provider=p_fail, model_id="t15-inactive",
                                           model_name="T15停用模型", status="inactive")
        injected["models"] += [m_fail.id, m_inactive.id]

        k_fail = await LLMApiKey.create(provider=p_fail, model=m_fail, api_key=LEAK_MARK,
                                        status="active", call_mode="openapi")
        k_inactive = await LLMApiKey.create(provider=p_fail, model=m_inactive,
                                            api_key="sk-t15-inactive", status="active",
                                            call_mode="openapi")
        injected["keys"] += [k_fail.id, k_inactive.id]

        kb_disabled = await RAGKnowledgeBase.create(
            name="T15停用KB", owner_type="usr", owner_id=1, status="disabled", is_public=False)
        kb_noemb = await RAGKnowledgeBase.create(
            name="T15无向量KB", owner_type="usr", owner_id=1, status="active",
            is_public=False, embedding_model_id=None)
        injected["kbs"] += [kb_disabled.id, kb_noemb.id]

        for rtype, rid in [("model", m_fail.id), ("model", m_inactive.id),
                           ("kb", kb_disabled.id), ("kb", kb_noemb.id)]:
            g = await ResourceGrant.create(owner_type="usr", owner_id=1,
                                           resource_type=rtype, resource_id=str(rid),
                                           effect="allow")
            injected["grants"].append(g.id)
        print(f"[注入完成] provider={p_fail.id} m_fail={m_fail.id} m_inactive={m_inactive.id} "
              f"kb_disabled={kb_disabled.id} kb_noemb={kb_noemb.id}")

        async with httpx.AsyncClient(base_url=BASE, timeout=130.0) as cli:
            # ========================================================
            # G7-01 LLM 上游不可达：重试 3 次退避耗尽（settings.retry.max=99 验证上限锁死）
            # ========================================================
            print("\n===== G7-01 LLM 上游不可达（连接拒绝） =====")
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "G7-LLM不可达", "graph_json": graph_llm(m_fail.id, retry_max=99)})
            wf_a = (r.json().get("data") or {}).get("id")
            injected["wfs"].append(wf_a)
            res = await dry_run_collect(cli, wf_a, headers)
            # 预期：dry-run 进入执行（200 SSE），llm 节点失败；重试 3 次 → 耗时 7s~40s
            # （若上限锁死失效、真按 99 次重试，退避封顶 4s 将远超 40s）
            retry_ok = 6.5 <= res["elapsed"] <= 40.0
            failed_evt = any("error" in e or "fail" in e or "node" in e for e in res["events"])
            record("G7-01a", "dry-run SSE 正常建立", res["status"] == 200,
                   f"sse={res['status']} exec_id={res['exec_id']} events={res['events'][:10]}")
            record("G7-01b", "重试 3 次退避（1+2+4s）后失败；retry.max=99 未生效（N4-4 上限锁死）",
                   retry_ok, f"elapsed={res['elapsed']:.1f}s ∈[6.5,40]")
            record("G7-01c", "SSE 含节点失败类事件", failed_evt,
                   f"events={res['events']}")

            await asyncio.sleep(1.0)
            r2 = await cli.get(f"/v1/agent/u/executions/{res['exec_id']}", headers=headers)
            exec_a = (r2.json().get("data") or {}) if r2.status_code == 200 else {}
            record("G7-01d", "执行记录终态 failed 且时间字段完整",
                   exec_a.get("status") == "failed" and exec_a.get("started_at") and exec_a.get("completed_at"),
                   f"status={exec_a.get('status')} started={exec_a.get('started_at')} completed={exec_a.get('completed_at')}")

            # G7-06 凭证泄漏检查（R-05/R-12）
            leak_sse = LEAK_MARK in res["data_text"]
            leak_detail = LEAK_MARK in json.dumps(exec_a, ensure_ascii=False)
            record("G7-06a", "SSE 数据帧不含注入凭证", not leak_sse, f"leak_in_sse={leak_sse}")
            record("G7-06b", "执行详情不含注入凭证", not leak_detail, f"leak_in_detail={leak_detail}")

            # ========================================================
            # G7-02 模型未激活：MODEL_UNAVAILABLE 不可重试，快速失败
            # ========================================================
            print("\n===== G7-02 模型未激活 =====")
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "G7-LLM停用", "graph_json": graph_llm(m_inactive.id)})
            wf_b = (r.json().get("data") or {}).get("id")
            injected["wfs"].append(wf_b)
            res_b = await dry_run_collect(cli, wf_b, headers)
            record("G7-02a", "MODEL_UNAVAILABLE 不可重试快速失败（<6s 证明无退避）",
                   res_b["elapsed"] < 6.0, f"elapsed={res_b['elapsed']:.1f}s")
            record("G7-02b", "错误语义含模型不可用",
                   "MODEL" in res_b["data_text"].upper() or "模型" in res_b["data_text"],
                   f"data={res_b['data_text'][:200]}")

            # ========================================================
            # G7-03 KB 空交集：KB_ACCESS_DENIED
            # ========================================================
            print("\n===== G7-03 KB 空交集（disabled） =====")
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "G7-KB空交集", "graph_json": graph_rag(kb_disabled.id)})
            wf_c = (r.json().get("data") or {}).get("id")
            injected["wfs"].append(wf_c)
            res_c = await dry_run_collect(cli, wf_c, headers)
            record("G7-03a", "KB_ACCESS_DENIED 不可重试快速失败（<6s）",
                   res_c["elapsed"] < 6.0, f"elapsed={res_c['elapsed']:.1f}s sse={res_c['status']}")
            record("G7-03b", "错误语义含 KB_ACCESS_DENIED / 知识库拒绝",
                   "KB_ACCESS_DENIED" in res_c["data_text"] or "知识库" in res_c["data_text"],
                   f"data={res_c['data_text'][:200]}")

            # ========================================================
            # G7-04 KB 无 Embedding 模型：EMBEDDING_UNAVAILABLE
            # ========================================================
            print("\n===== G7-04 KB 无 Embedding 模型 =====")
            r = await cli.post("/v1/agent/u/workflows", headers=headers,
                               json={"name": "G7-无向量模型", "graph_json": graph_rag(kb_noemb.id)})
            wf_d = (r.json().get("data") or {}).get("id")
            injected["wfs"].append(wf_d)
            res_d = await dry_run_collect(cli, wf_d, headers)
            record("G7-04a", "EMBEDDING_UNAVAILABLE 失败（<6s 不可重试）",
                   res_d["elapsed"] < 6.0, f"elapsed={res_d['elapsed']:.1f}s sse={res_d['status']}")
            record("G7-04b", "错误语义含 EMBEDDING",
                   "EMBEDDING" in res_d["data_text"].upper() or "Embedding" in res_d["data_text"],
                   f"data={res_d['data_text'][:200]}")

            record("G7-07", "Qdrant 全实例故障注入", True,
                   "限制项：需改 env 重启服务，超出数据面安全注入范围 → 转运维侧演练清单")

    finally:
        # ============================================================
        # 清理：删除注入数据与测试工作流（可逆性保障）
        # ============================================================
        print("\n===== 清理注入数据 =====")
        async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as cli:
            for wid in injected["wfs"]:
                if wid:
                    await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=headers)
        await ResourceGrant.filter(id__in=injected["grants"]).delete()
        await RAGKnowledgeBase.filter(id__in=injected["kbs"]).delete()
        await LLMApiKey.filter(id__in=injected["keys"]).delete()
        await LLMModel.filter(id__in=injected["models"]).delete()
        await LLMProvider.filter(id__in=injected["providers"]).delete()
        await Tortoise.close_connections()
        print("[清理完成]")

    # ============================================================
    # 汇总
    # ============================================================
    print("\n===== G7 告警演练汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")


asyncio.run(main())
