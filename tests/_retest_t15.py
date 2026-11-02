"""
T15 节点3 复测脚本：BUG-T15-002（版本链路）+ BUG-T15-003（时区一致性）

环境约束（新发现）：openGauss 7.0.0 sql_compatibility=A（Oracle 兼容），空串 '' 等同 NULL。
- workflow_version.description 列当前 nullable=YES 无 default（迁移 DEFAULT '' 失败后的中间态）
- 模型 default="" 插入时 '' 会被存为 NULL

运行: .venv/Scripts/python.exe tests/_retest_t15.py
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from base.common.security import create_access_token

BASE = "http://127.0.0.1:9998"
WF_ID = 1

RESULTS: list[dict] = []


def record(case_id: str, name: str, passed: bool, detail: str):
    RESULTS.append({"id": case_id, "name": name, "pass": passed, "detail": detail})
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {case_id} {name} :: {detail}")


def make_token() -> str:
    return create_access_token(
        {"typ": "usr", "sub": "1"}, expires_delta=timedelta(hours=2)
    )


async def main():
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE, headers=headers, timeout=60.0) as cli:
        # ============================================================
        # Part 0: 认证自检
        # ============================================================
        r = await cli.get(f"/v1/agent/u/workflows/{WF_ID}")
        record("T15-AUTH", "usr:1 token 访问工作流详情", r.status_code == 200,
               f"status={r.status_code}")
        if r.status_code != 200:
            print("认证失败，终止:", r.text[:500])
            return

        # ============================================================
        # Part 1: BUG-T15-002 复测 —— 版本链路
        # ============================================================
        print("\n===== BUG-T15-002 复测：版本链路 =====")

        # 1.1 版本列表（基线 v1，迁移前发布，description 应为 null 或 ""）
        r = await cli.get(f"/v1/agent/u/workflows/{WF_ID}/versions")
        ok = r.status_code == 200
        body = r.json() if ok else {}
        versions = (body.get("data") or []) if ok else []
        has_desc_field = versions and ("description" in versions[0])
        record("T15-002-01", "GET versions 返回 200 且含 description 字段",
               ok and has_desc_field,
               f"status={r.status_code} count={len(versions)} "
               f"v1.description={versions[0].get('description')!r} (GaussDB空串->NULL预期)")
        baseline_v1_desc = versions[0].get("description") if versions else None

        # 1.2 版本快照 v1（含 graph_json + description）
        r = await cli.get(f"/v1/agent/u/workflows/{WF_ID}/versions/1")
        ok = r.status_code == 200
        snap = (r.json().get("data") or {}) if ok else {}
        record("T15-002-02", "GET versions/1 快照含 graph_json + description",
               ok and "graph_json" in snap and "description" in snap,
               f"status={r.status_code} has_graph={'graph_json' in snap} "
               f"has_desc={'description' in snap} desc={snap.get('description')!r}")

        # 1.3 发布 v2 带显式 description（非空，应正常存储与回读）
        pub_desc = "T15回归验证-v2：发布说明非空"
        r = await cli.post(f"/v1/agent/u/workflows/{WF_ID}/publish",
                           json={"description": pub_desc})
        ok = r.status_code == 200
        pub_data = (r.json().get("data") or {}) if ok else {}
        record("T15-002-03", "POST publish 带 description（非空）发布成功",
               ok, f"status={r.status_code} resp={json.dumps(pub_data, ensure_ascii=False)[:200]}")
        v2_no = pub_data.get("version_no")

        # 1.4 版本列表确认 v2 description 回读
        r = await cli.get(f"/v1/agent/u/workflows/{WF_ID}/versions")
        versions = (r.json().get("data") or []) if r.status_code == 200 else []
        v2 = next((v for v in versions if v.get("version_no") == v2_no), None)
        record("T15-002-04", "v2 description 回读正确（非空串不受GaussDB影响）",
               v2 is not None and v2.get("description") == pub_desc,
               f"v2.description={v2.get('description') if v2 else None!r} 期望={pub_desc!r}")

        # 1.5 边界：publish 空 body {} —— description 缺省 "" (GaussDB 下预期存 NULL)
        r = await cli.post(f"/v1/agent/u/workflows/{WF_ID}/publish", json={})
        ok = r.status_code == 200
        v3_no = ((r.json().get("data") or {}).get("version_no")) if ok else None
        record("T15-002-05", "POST publish 空 body（description 缺省）不报错",
               ok, f"status={r.status_code} version_no={v3_no}")

        # 回读 v3 description，验证 GaussDB 空串行为（暴露环境适配缺陷）
        if v3_no:
            r = await cli.get(f"/v1/agent/u/workflows/{WF_ID}/versions")
            versions = (r.json().get("data") or []) if r.status_code == 200 else []
            v3 = next((v for v in versions if v.get("version_no") == v3_no), None)
            desc3 = v3.get("description") if v3 else "N/A"
            # 契约期望 ""，GaussDB 实际 None —— 记录为环境适配缺陷证据
            record("T15-002-06", "v3 缺省 description 回读（契约'' vs GaussDB null）",
                   desc3 == "",  # 按契约判定；失败即 BUG-T15-004 证据
                   f"v3.description={desc3!r} 契约期望='' -> {'符合契约' if desc3 == '' else 'GaussDB空串->NULL，违反契约'}")

        # 1.7 回滚到 v1 → 应生成新版本（v4）
        r = await cli.post(f"/v1/agent/u/workflows/{WF_ID}/rollback",
                           json={"version_no": 1})
        ok = r.status_code == 200
        rb_data = (r.json().get("data") or {}) if ok else {}
        record("T15-002-07", "POST rollback version_no=1 生成新版本",
               ok, f"status={r.status_code} resp={json.dumps(rb_data, ensure_ascii=False)[:200]}")

        # 1.8 回滚后版本快照：新版本 graph_json 应与 v1 一致
        rb_vno = rb_data.get("version_no")
        if rb_vno:
            r1 = await cli.get(f"/v1/agent/u/workflows/{WF_ID}/versions/1")
            rN = await cli.get(f"/v1/agent/u/workflows/{WF_ID}/versions/{rb_vno}")
            g1 = (r1.json().get("data") or {}).get("graph_json")
            gN = (rN.json().get("data") or {}).get("graph_json")
            record("T15-002-08", f"回滚生成 v{rb_vno} graph_json 与 v1 一致",
                   g1 == gN and g1 is not None,
                   f"graph_equal={g1 == gN}")

        # ============================================================
        # Part 2: BUG-T15-003 复测 —— dry-run 时区一致性
        # ============================================================
        print("\n===== BUG-T15-003 复测：执行时间同基准 =====")
        exec_id = None
        t0 = datetime.utcnow()
        async with cli.stream(
            "POST", f"/v1/agent/u/workflows/{WF_ID}/dry-run",
            json={"inputs": {"query": "T15时区复测"}},
        ) as resp:
            exec_id = resp.headers.get("X-Execution-Id")
            sse_status = resp.status_code
            frames = []
            async for line in resp.aiter_lines():
                if line.startswith("event:") or line.startswith("data:"):
                    frames.append(line)
            # 简单统计事件类型
            event_types = [l[6:].strip() for l in frames if l.startswith("event:")]
        t1 = datetime.utcnow()
        wall_ms = (t1 - t0).total_seconds() * 1000

        record("T15-003-01", "dry-run SSE 流正常结束",
               sse_status == 200 and exec_id is not None,
               f"sse_status={sse_status} exec_id={exec_id} events={event_types[:8]} "
               f"wall={wall_ms:.0f}ms")

        # 等待终态落库
        await asyncio.sleep(1.0)
        if exec_id:
            r = await cli.get(f"/v1/agent/u/executions/{exec_id}")
            ok = r.status_code == 200
            e = (r.json().get("data") or {}) if ok else {}
            started = e.get("started_at")
            completed = e.get("completed_at")
            detail_extra = ""
            delta_s = None
            same_base = False
            if started and completed:
                # 解析 ISO（naive 视为 UTC per 修复说明）
                s = datetime.fromisoformat(str(started).replace("Z", ""))
                c = datetime.fromisoformat(str(completed).replace("Z", ""))
                delta_s = (c - s).total_seconds()
                # 同基准判定：差值应与墙钟同量级（<60s），而非 28800s
                same_base = 0 <= delta_s < 60
                detail_extra = f"delta={delta_s:.3f}s wall={wall_ms:.0f}ms"
            record("T15-003-02", "started_at 与 completed_at 同基准（差值=实际时长）",
                   ok and same_base,
                   f"status={e.get('status')} started={started} completed={completed} {detail_extra}")

    # ============================================================
    # 汇总
    # ============================================================
    print("\n===== 复测汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")


asyncio.run(main())
