"""
T15 节点3 / G5 越权用例集（AZ-01~15）数据面执行脚本

用例定义（溯源 docs/arch/04 §F8 + PRD §7.1 归属与可见性规则）：
- F8: 越权 → 404（不暴露存在性）+ 审计 warn；同主体 1 分钟 >10 次 → 限流封禁 60s（429）
- 未认证 → 401；跨主体类型（cus 访问 usr 资源）→ 404

身份设计（避免越权计数器互相干扰，阈值 10 次/60s/主体）：
- usr:9001 → AZ-01~05（5 次）；usr:9002 → AZ-06~10（5 次）；usr:9003 → AZ-11~12（2 次）
- cus:9001 → AZ-13（1 次）；usr:{动态id} → AZ-15（14 次，专用身份）
- 被攻击资源：usr:1 新建的私有工作流 W（visibility=private 默认值）

运行: .venv/Scripts/python.exe tests/_t15_g5_authz.py
"""
import asyncio
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
    print(f"[{mark}] {case_id} {name} :: {detail}")


def make_token(typ: str, sub: str) -> str:
    return create_access_token({"typ": typ, "sub": sub}, expires_delta=timedelta(hours=2))


def minimal_graph() -> dict:
    return {
        "schema_version": 2,
        "nodes": [
            {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
             "data": {"outputs": [{"name": "query", "type": "string"}]}},
            {"id": "e1", "type": "end", "position": {"x": 300, "y": 0},
             "data": {"inputs": [{"name": "answer", "type": "string", "from": "s1.query"}]}},
        ],
        "edges": [
            {"id": "e1", "source": "s1", "target": "e1",
             "sourceHandle": "out", "targetHandle": "in"}
        ],
        "variables": [],
    }


def body_of(r: httpx.Response) -> dict:
    try:
        return r.json()
    except Exception:
        return {}


async def main():
    t_start = time.time()
    owner_headers = {"Authorization": f"Bearer {make_token('usr', '1')}"}

    async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as cli:
        # ============================================================
        # Phase 0: 构造被攻击资源（usr:1 私有工作流 + 一条执行记录）
        # ============================================================
        r = await cli.post("/v1/agent/u/workflows", headers=owner_headers,
                           json={"name": "AZ越权靶场-T15", "description": "G5越权用例临时资源",
                                 "graph_json": minimal_graph()})
        ok = r.status_code == 200
        wid = (r.json().get("data") or {}).get("id") if ok else None
        record("AZ-00a", "前置：usr:1 创建私有工作流靶标", ok and wid is not None,
               f"status={r.status_code} wid={wid}")
        if not wid:
            print("前置失败，终止")
            return

        # 取 usr:1 的一条执行记录（用于 AZ-10/11/12）
        exec_id = None
        r = await cli.get("/v1/agent/u/executions?page=1&page_size=1", headers=owner_headers)
        if r.status_code == 200:
            data = r.json().get("data")
            if isinstance(data, dict):
                items = data.get("items") or []
            elif isinstance(data, list):
                items = data
            else:
                items = []
            if items:
                exec_id = items[0].get("id")
        if not exec_id:
            # 兜底：对 WF1 触发一次 dry-run 生成执行
            async with cli.stream("POST", "/v1/agent/u/workflows/1/dry-run",
                                  headers=owner_headers,
                                  json={"inputs": {"query": "AZ前置"}}) as resp:
                exec_id = resp.headers.get("X-Execution-Id")
                async for _ in resp.aiter_lines():
                    pass
        record("AZ-00b", "前置：usr:1 拥有执行记录（供越权攻击）", exec_id is not None,
               f"exec_id={exec_id}")

        # ============================================================
        # AZ-01~05 攻击者 usr:9001（5 次越权，低于阈值 10）
        # ============================================================
        print("\n===== AZ-01~05 usr:9001 越权 =====")
        h1 = {"Authorization": f"Bearer {make_token('usr', '9001')}"}
        bad_graph = minimal_graph()

        r = await cli.get(f"/v1/agent/u/workflows/{wid}", headers=h1)
        record("AZ-01", "usr:9001 读他人工作流详情 → 404", r.status_code == 404,
               f"status={r.status_code} body={str(body_of(r))[:120]}")

        r = await cli.put(f"/v1/agent/u/workflows/{wid}/draft", headers=h1,
                          json={"graph_json": bad_graph, "draft_version": 1})
        record("AZ-02", "usr:9001 存他人草稿 → 404", r.status_code == 404,
               f"status={r.status_code}")

        r = await cli.post(f"/v1/agent/u/workflows/{wid}/validate", headers=h1,
                           json={"graph_json": bad_graph})
        record("AZ-03", "usr:9001 校验他人工作流 → 404", r.status_code == 404,
               f"status={r.status_code}")

        r = await cli.post(f"/v1/agent/u/workflows/{wid}/publish", headers=h1,
                           json={"description": "越权发布"})
        record("AZ-04", "usr:9001 发布他人工作流 → 404", r.status_code == 404,
               f"status={r.status_code}")

        r = await cli.get(f"/v1/agent/u/workflows/{wid}/versions", headers=h1)
        record("AZ-05", "usr:9001 读他人版本列表 → 404", r.status_code == 404,
               f"status={r.status_code}")

        # ============================================================
        # AZ-06~10 攻击者 usr:9002（5 次越权）
        # ============================================================
        print("\n===== AZ-06~10 usr:9002 越权 =====")
        h2 = {"Authorization": f"Bearer {make_token('usr', '9002')}"}

        r = await cli.get(f"/v1/agent/u/workflows/{wid}/versions/1", headers=h2)
        record("AZ-06", "usr:9002 读他人版本快照 → 404", r.status_code == 404,
               f"status={r.status_code}")

        r = await cli.post(f"/v1/agent/u/workflows/{wid}/rollback", headers=h2,
                           json={"version_no": 1})
        record("AZ-07", "usr:9002 回滚他人工作流 → 404", r.status_code == 404,
               f"status={r.status_code}")

        r = await cli.post(f"/v1/agent/u/workflows/{wid}/disable", headers=h2)
        record("AZ-08", "usr:9002 停用他人工作流 → 404", r.status_code == 404,
               f"status={r.status_code}")

        r = await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=h2)
        record("AZ-09", "usr:9002 删除他人工作流 → 404", r.status_code == 404,
               f"status={r.status_code}")

        if exec_id:
            r = await cli.get(f"/v1/agent/u/executions/{exec_id}", headers=h2)
            record("AZ-10", "usr:9002 读他人执行详情 → 404", r.status_code == 404,
                   f"status={r.status_code}")
        else:
            record("AZ-10", "usr:9002 读他人执行详情 → 404", False, "无 exec_id，跳过")

        # ============================================================
        # AZ-11~12 攻击者 usr:9003（2 次越权）
        # ============================================================
        print("\n===== AZ-11~12 usr:9003 越权 =====")
        h3 = {"Authorization": f"Bearer {make_token('usr', '9003')}"}
        if exec_id:
            r = await cli.get(f"/v1/agent/u/executions/{exec_id}/trace", headers=h3)
            record("AZ-11", "usr:9003 读他人执行 Trace → 404", r.status_code == 404,
                   f"status={r.status_code}")

            r = await cli.post(f"/v1/agent/u/executions/{exec_id}/cancel", headers=h3)
            record("AZ-12", "usr:9003 取消他人执行 → 404", r.status_code == 404,
                   f"status={r.status_code}")
        else:
            record("AZ-11", "usr:9003 读他人执行 Trace → 404", False, "无 exec_id，跳过")
            record("AZ-12", "usr:9003 取消他人执行 → 404", False, "无 exec_id，跳过")

        # ============================================================
        # AZ-13 跨主体类型：cus:9001 访问 usr:1 资源 → 404
        # ============================================================
        print("\n===== AZ-13 cus:9001 跨主体类型越权 =====")
        hc = {"Authorization": f"Bearer {make_token('cus', '9001')}"}
        r = await cli.get(f"/v1/agent/u/workflows/{wid}", headers=hc)
        record("AZ-13", "cus:9001 读 usr 工作流 → 404（跨主体类型隔离）",
               r.status_code == 404, f"status={r.status_code}")

        # ============================================================
        # AZ-14 未认证 → 401
        # ============================================================
        print("\n===== AZ-14 未认证访问 =====")
        r = await cli.get(f"/v1/agent/u/workflows/{wid}")
        record("AZ-14", "无 token 访问用户侧端点 → 401", r.status_code == 401,
               f"status={r.status_code}")

        # ============================================================
        # AZ-15 F8 限流：同主体 1 分钟 >10 次越权 → 429 封禁 + 恢复
        # ============================================================
        print("\n===== AZ-15 高频越权限流封禁 =====")
        atk_id = str(91000 + int(time.time()) % 8000)  # 动态身份避免历史计数干扰
        ha = {"Authorization": f"Bearer {make_token('usr', atk_id)}"}
        statuses = []
        for i in range(14):
            r = await cli.get(f"/v1/agent/u/workflows/{wid}", headers=ha)
            statuses.append(r.status_code)
        # 前 11 次：404（第 11 次越权记录后 count=11>10 置封禁，当次仍走完 404 流程）
        # 第 12 次起：中间件命中封禁 → 429
        first_404 = all(s == 404 for s in statuses[:11])
        later_429 = all(s == 429 for s in statuses[11:])
        record("AZ-15a", "前 11 次越权均 404（不暴露存在性）", first_404,
               f"statuses[:11]={statuses[:11]}")
        record("AZ-15b", "第 12 次起 429（封禁生效）", later_429,
               f"statuses[11:]={statuses[11:]}")

        # 封禁期任意请求均 429（中间件级，含合法资源）
        r = await cli.get("/v1/agent/u/workflows?page=1&page_size=1", headers=ha)
        record("AZ-15c", "封禁期主体任意请求 429（中间件闸门）", r.status_code == 429,
               f"status={r.status_code} body={str(body_of(r))[:120]}")

        # 封禁 60s 后自动解除
        print("等待 62s 验证封禁自动解除...")
        await asyncio.sleep(62)
        r = await cli.get(f"/v1/agent/u/workflows/{wid}", headers=ha)
        record("AZ-15d", "封禁 60s 后自动解除（恢复 404 而非持续 429）",
               r.status_code == 404, f"status={r.status_code}")

        # ============================================================
        # 清理：usr:1 删除靶标工作流
        # ============================================================
        r = await cli.delete(f"/v1/agent/u/workflows/{wid}", headers=owner_headers)
        record("AZ-99", "清理：usr:1 删除靶标工作流", r.status_code == 200,
               f"status={r.status_code}")

    # ============================================================
    # 汇总
    # ============================================================
    print("\n===== G5 AZ 用例集汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}  耗时 {time.time()-t_start:.1f}s")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")


asyncio.run(main())
