"""
T15 节点3 / G4 发布与使用剩余场景（数据面）

- AC-22 版本生效与双版本并行：v1/v2 快照独立可取、current 指针正确、回滚生成新版本且图谱一致
- AC-23 模板复制：visibility=template 可复制、归属复制者、私有模板 404、复制内容与发布快照一致
- AC-24 停用：已发布工作流停用后 dry-run 被拒、详情状态正确、版本历史仍可读

运行: .venv/Scripts/python.exe tests/_t15_g4_publish.py
"""
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from tortoise import Tortoise

from base.common.security import create_access_token

BASE = "http://127.0.0.1:9998"
RESULTS: list[dict] = []


def record(case_id, name, passed, detail):
    RESULTS.append({"id": case_id, "name": name, "pass": passed, "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {case_id} {name} :: {detail}")


def make_token(sub="1") -> str:
    return create_access_token({"typ": "usr", "sub": sub}, expires_delta=timedelta(hours=2))


def graph(tag: str) -> dict:
    return {
        "schema_version": 2,
        "nodes": [
            {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
             "data": {"outputs": [{"name": "query", "type": "string"}]}},
            {"id": "e1", "type": "end", "position": {"x": 300, "y": 0},
             "data": {"inputs": [{"name": "answer", "type": "string", "from": "s1.query"}]}},
        ],
        "edges": [{"id": "e1", "source": "s1", "target": "e1",
                   "sourceHandle": "out", "targetHandle": "in"}],
        "variables": [{"name": f"tag_{tag}", "type": "string"}],
    }


async def main():
    from base.common.database import TORTOISE_ORM
    await Tortoise.init(config=TORTOISE_ORM)
    from base.plugins.agent.models.workflow import Workflow

    h1 = {"Authorization": f"Bearer {make_token('1')}"}
    h2 = {"Authorization": f"Bearer {make_token('9001')}"}
    h3 = {"Authorization": f"Bearer {make_token('9002')}"}  # 第三方非管理员（usr:1 为 data_scope=ALL，探测须用普通主体）
    created_wfs = []

    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
            # ====================================================
            # AC-22 版本生效与双版本并行
            # ====================================================
            print("\n===== AC-22 版本生效 / 双版本并行 =====")
            r = await cli.post("/v1/agent/u/workflows", headers=h1,
                               json={"name": "AC22版本靶场", "graph_json": graph("v1")})
            wid = (r.json().get("data") or {}).get("id")
            created_wfs.append(wid)

            r = await cli.post(f"/v1/agent/u/workflows/{wid}/publish", headers=h1,
                               json={"description": "v1"})
            v1 = (r.json().get("data") or {}).get("version_no")
            record("AC22-01", "发布 v1", r.status_code == 200 and v1 == 1,
                   f"status={r.status_code} v={v1}")

            # 修改草稿为 v2 图谱再发布
            r = await cli.get(f"/v1/agent/u/workflows/{wid}", headers=h1)
            dv = ((r.json().get("data") or {}).get("draft_version"))
            r = await cli.put(f"/v1/agent/u/workflows/{wid}/draft", headers=h1,
                              json={"graph_json": graph("v2"), "draft_version": dv})
            record("AC22-02", "草稿更新为 v2 图谱", r.status_code == 200,
                   f"status={r.status_code}")
            r = await cli.post(f"/v1/agent/u/workflows/{wid}/publish", headers=h1,
                               json={"description": "v2"})
            v2 = (r.json().get("data") or {}).get("version_no")
            v2_id = (r.json().get("data") or {}).get("version_id")
            record("AC22-03", "发布 v2", r.status_code == 200 and v2 == 2,
                   f"status={r.status_code} v={v2}")

            # 双版本快照独立可取且内容隔离
            r1 = await cli.get(f"/v1/agent/u/workflows/{wid}/versions/1", headers=h1)
            r2 = await cli.get(f"/v1/agent/u/workflows/{wid}/versions/2", headers=h1)
            g1 = (r1.json().get("data") or {}).get("graph_json") or {}
            g2 = (r2.json().get("data") or {}).get("graph_json") or {}
            iso = (any(v.get("name") == "tag_v1" for v in g1.get("variables", []))
                   and any(v.get("name") == "tag_v2" for v in g2.get("variables", [])))
            record("AC22-04", "v1/v2 快照独立可取且图谱内容隔离", iso,
                   f"v1_vars={[v.get('name') for v in g1.get('variables', [])]} "
                   f"v2_vars={[v.get('name') for v in g2.get('variables', [])]}")

            # current 指针指向 v2（契约字段 current_version_id，指向不可变版本主键）
            r = await cli.get(f"/v1/agent/u/workflows/{wid}", headers=h1)
            det = r.json().get("data") or {}
            cur = det.get("current_version_id")
            record("AC22-05", "发布后 current 指针=v2", cur == v2_id,
                   f"current_version_id={cur} expect_v2_id={v2_id}")

            # 回滚到 v1 → 生成 v3 且图谱==v1
            r = await cli.post(f"/v1/agent/u/workflows/{wid}/rollback", headers=h1,
                               json={"version_no": 1})
            v3 = (r.json().get("data") or {}).get("version_no")
            r3 = await cli.get(f"/v1/agent/u/workflows/{wid}/versions/{v3}", headers=h1)
            g3 = (r3.json().get("data") or {}).get("graph_json") or {}
            record("AC22-06", "回滚 v1 生成 v3 且图谱与 v1 一致",
                   v3 == 3 and any(v.get("name") == "tag_v1" for v in g3.get("variables", [])),
                   f"v3={v3} v3_vars={[v.get('name') for v in g3.get('variables', [])]}")

            # ====================================================
            # AC-23 模板复制
            # ====================================================
            print("\n===== AC-23 模板复制 =====")
            r = await cli.post("/v1/agent/u/workflows", headers=h1,
                               json={"name": "AC23模板源", "graph_json": graph("tpl")})
            tpl_id = (r.json().get("data") or {}).get("id")
            created_wfs.append(tpl_id)
            await cli.post(f"/v1/agent/u/workflows/{tpl_id}/publish", headers=h1,
                           json={"description": "模板v1"})
            # 置为 template 可见性（管理侧动作，测试经 ORM 直接置位模拟管理员发布模板）
            await Workflow.filter(id=tpl_id).update(visibility="template")

            r = await cli.post("/v1/agent/u/workflows", headers=h2,
                               json={"name": "AC23复制产物", "template_id": tpl_id})
            copy_id = (r.json().get("data") or {}).get("id")
            if copy_id:
                created_wfs.append(copy_id)
            record("AC23-01", "他人从 template 复制成功", r.status_code == 200 and copy_id is not None,
                   f"status={r.status_code} copy_id={copy_id}")

            if copy_id:
                # 归属判据（详情契约不暴露 owner 字段）：复制者可读 + 第三方非管理员 404 隔离 + 图谱一致
                # 注：usr:1 具备 data_scope=ALL（PRD §7.1 规则 4），探测须用普通主体 usr:9002
                r = await cli.get(f"/v1/agent/u/workflows/{copy_id}", headers=h2)
                cd = r.json().get("data") or {}
                cg = cd.get("definition") or {}
                r_x = await cli.get(f"/v1/agent/u/workflows/{copy_id}", headers=h3)
                record("AC23-02", "复制品归属复制者（usr:9001 可读 / usr:9002 访问 404）且图谱与发布快照一致",
                       r.status_code == 200
                       and any(v.get("name") == "tag_tpl" for v in cg.get("variables", []))
                       and r_x.status_code == 404,
                       f"copier_read={r.status_code} third_party_read={r_x.status_code} "
                       f"vars={[v.get('name') for v in cg.get('variables', [])]}")

            # 私有工作流不可作模板
            r = await cli.post("/v1/agent/u/workflows", headers=h1,
                               json={"name": "AC23私有源", "graph_json": graph("priv")})
            priv_id = (r.json().get("data") or {}).get("id")
            created_wfs.append(priv_id)
            r = await cli.post("/v1/agent/u/workflows", headers=h2,
                               json={"name": "越权复制", "template_id": priv_id})
            record("AC23-03", "私有工作流作为模板复制 → 404", r.status_code == 404,
                   f"status={r.status_code}")

            # ====================================================
            # AC-24 停用
            # ====================================================
            print("\n===== AC-24 停用 =====")
            r = await cli.post("/v1/agent/u/workflows", headers=h1,
                               json={"name": "AC24停用靶场", "graph_json": graph("dis")})
            dis_id = (r.json().get("data") or {}).get("id")
            created_wfs.append(dis_id)
            await cli.post(f"/v1/agent/u/workflows/{dis_id}/publish", headers=h1,
                           json={"description": "v1"})

            r = await cli.post(f"/v1/agent/u/workflows/{dis_id}/disable", headers=h1)
            record("AC24-01", "已发布工作流停用成功", r.status_code == 200,
                   f"status={r.status_code} body={str(r.json())[:150]}")

            # 停用后 dry-run 语义（BUG-T15-010 裁定口径）：
            # dry-run 是设计态（用草稿 wf.definition，kind=dry_run），不受发布态停用约束，
            # 预期 200 放行；「对话入口拒绝」由 DialogFlow chat 的 status != "active" 检查承担
            # 注意：必须完整消费 SSE 流（BUG-T15-012：中途断开会导致并发槽泄漏，污染后续用例）
            got_sse = False
            terminal = None
            code = None
            try:
                async with cli.stream("POST", f"/v1/agent/u/workflows/{dis_id}/dry-run",
                                      headers=h1, json={"inputs": {"query": "x"}},
                                      timeout=30.0) as resp:
                    code = resp.status_code
                    async for line in resp.aiter_lines():
                        if line.startswith("event:"):
                            got_sse = True
                            terminal = line[6:].strip()
            except Exception as e:
                code = f"exc:{type(e).__name__}"
            record("AC24-02", "停用后 dry-run 设计态放行（T15-010 裁定口径：发布态约束由对话入口承担）",
                   code == 200 and got_sse and terminal == "run_completed",
                   f"dry-run status={code} sse={got_sse} terminal={terminal}")

            # 停用后详情 status=inactive（与 G1-DIS-01 同口径）、版本历史仍可读
            r = await cli.get(f"/v1/agent/u/workflows/{dis_id}", headers=h1)
            det = r.json().get("data") or {}
            r2 = await cli.get(f"/v1/agent/u/workflows/{dis_id}/versions", headers=h1)
            vers = r2.json().get("data") or []
            record("AC24-03", "停用后详情 status=inactive 且版本历史仍可读",
                   det.get("status") == "inactive" and isinstance(vers, list) and len(vers) >= 1,
                   f"status={det.get('status')} versions={len(vers) if isinstance(vers, list) else '?'}")

    finally:
        print("\n===== 清理 =====")
        async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as cli:
            for wid in created_wfs:
                if wid:
                    await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=h1)
        await Tortoise.close_connections()
        print("[清理完成]")

    print("\n===== G4 汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")


asyncio.run(main())
