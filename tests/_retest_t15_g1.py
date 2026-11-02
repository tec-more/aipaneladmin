"""
T15 G1 剩余用例：删除保护 / 停用 / 归属隔离 / 发布幂等 / 版本不可变

用例:
- G1-DEL-01: active+已发布 工作流删除被拒（409）
- G1-DEL-02: 临时工作流 停用后删除成功
- G1-DEL-03: 跨主体删除（usr:2 删 usr:1）→ 404
- G1-DIS-01: 停用语义（status active→inactive）
- G1-DIS-02: 停用后 dry-run 行为观测（记录实际行为）
- G1-IDEM-01: publish 同 Idempotency-Key 重放返回原响应
- G1-IMMUT-01: 版本不可变（v1 快照在后续发布后保持不变）
"""
import asyncio
import json
import sys
import uuid
from datetime import timedelta
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


def token_for(uid: str) -> str:
    return create_access_token({"typ": "usr", "sub": uid}, expires_delta=timedelta(hours=2))


async def main():
    h1 = {"Authorization": f"Bearer {token_for('1')}"}
    h2 = {"Authorization": f"Bearer {token_for('2')}"}

    async with httpx.AsyncClient(base_url=BASE, timeout=60.0) as cli:
        # ---- G1-IMMUT-01: 版本不可变（先取 v1 快照基线） ----
        r = await cli.get(f"/v1/agent/u/workflows/{WF_ID}/versions/1", headers=h1)
        snap_before = (r.json().get("data") or {}) if r.status_code == 200 else {}
        g_before = json.dumps(snap_before.get("graph_json"), sort_keys=True, ensure_ascii=False)

        # ---- G1-IDEM-01: 发布幂等 ----
        idem = f"t15-idem-{uuid.uuid4().hex[:12]}"
        ra = await cli.post(f"/v1/agent/u/workflows/{WF_ID}/publish",
                            json={"description": "幂等第一次"}, headers={**h1, "Idempotency-Key": idem})
        rb = await cli.post(f"/v1/agent/u/workflows/{WF_ID}/publish",
                            json={"description": "幂等第二次"}, headers={**h1, "Idempotency-Key": idem})
        da = (ra.json().get("data") or {}) if ra.status_code == 200 else {}
        db = (rb.json().get("data") or {}) if rb.status_code == 200 else {}
        record("G1-IDEM-01", "同 Idempotency-Key 重放返回原版本（不重复生成）",
               ra.status_code == 200 and rb.status_code == 200
               and da.get("version_no") == db.get("version_no"),
               f"first={da.get('version_no')} replay={db.get('version_no')} equal={da.get('version_no') == db.get('version_no')}")

        # 幂等重放后 v1 快照不应变化
        r = await cli.get(f"/v1/agent/u/workflows/{WF_ID}/versions/1", headers=h1)
        snap_after = (r.json().get("data") or {}) if r.status_code == 200 else {}
        g_after = json.dumps(snap_after.get("graph_json"), sort_keys=True, ensure_ascii=False)
        record("G1-IMMUT-01", "v1 快照不可变（多次发布后 graph_json 不变）",
               g_before == g_after and g_before not in ("", "null"),
               f"graph_equal={g_before == g_after}")

        # ---- G1-DEL-01: active 删除保护 ----
        r = await cli.delete(f"/v1/agent/u/workflows/{WF_ID}", headers=h1)
        record("G1-DEL-01", "active+已发布工作流删除被拒（409）",
               r.status_code == 409,
               f"status={r.status_code} body={r.text[:150]}")
        # 确认数据仍在
        r2 = await cli.get(f"/v1/agent/u/workflows/{WF_ID}", headers=h1)
        record("G1-DEL-01b", "删除被拒后工作流数据完整保留",
               r2.status_code == 200, f"status={r2.status_code}")

        # ---- G1-DEL-03: 跨主体删除隔离 ----
        r = await cli.delete(f"/v1/agent/u/workflows/{WF_ID}", headers=h2)
        record("G1-DEL-03", "usr:2 删除 usr:1 工作流 → 404（不暴露存在性）",
               r.status_code == 404, f"status={r.status_code}")
        # 跨主体读
        r = await cli.get(f"/v1/agent/u/workflows/{WF_ID}", headers=h2)
        record("G1-ISO-01", "跨主体读取详情 → 404",
               r.status_code == 404, f"status={r.status_code}")
        # 跨主体发布
        r = await cli.post(f"/v1/agent/u/workflows/{WF_ID}/publish", json={}, headers=h2)
        record("G1-ISO-02", "跨主体发布 → 404",
               r.status_code == 404, f"status={r.status_code}")
        # 跨主体版本列表
        r = await cli.get(f"/v1/agent/u/workflows/{WF_ID}/versions", headers=h2)
        record("G1-ISO-03", "跨主体版本列表 → 404",
               r.status_code == 404, f"status={r.status_code}")

        # ---- G1-DIS/DEL-02: 临时工作流全生命周期 ----
        # 新建
        r = await cli.post("/v1/agent/u/workflows",
                           json={"name": "T15-TEMP-停用删除"}, headers=h1)
        tmp = (r.json().get("data") or {}) if r.status_code == 200 else {}
        tmp_id = tmp.get("id")
        record("G1-LC-01", "临时工作流新建成功", r.status_code == 200 and tmp_id,
               f"status={r.status_code} id={tmp_id}")

        if tmp_id:
            # 发布（骨架图应可直接发布）
            r = await cli.post(f"/v1/agent/u/workflows/{tmp_id}/publish",
                               json={"description": "临时发布"}, headers=h1)
            pub_ok = r.status_code == 200
            record("G1-LC-02", "临时工作流骨架直接发布成功", pub_ok,
                   f"status={r.status_code} body={r.text[:150]}")

            # 停用
            r = await cli.post(f"/v1/agent/u/workflows/{tmp_id}/disable", headers=h1)
            dis = (r.json().get("data") or {}) if r.status_code == 200 else {}
            record("G1-DIS-01", "停用 active→inactive",
                   r.status_code == 200 and dis.get("status") == "inactive",
                   f"status={r.status_code} data={dis}")

            # 停用后 dry-run 行为观测
            r = await cli.post(f"/v1/agent/u/workflows/{tmp_id}/dry-run",
                               json={"inputs": {}}, headers=h1)
            record("G1-DIS-02", "停用后 dry-run 行为观测（记录实际行为）",
                   True,  # 观测性用例，不判定
                   f"status={r.status_code}（观测：{'允许试跑' if r.status_code == 200 else '拒绝:' + r.text[:80]}）")

            # 停用后删除成功
            r = await cli.delete(f"/v1/agent/u/workflows/{tmp_id}", headers=h1)
            record("G1-DEL-02", "停用后删除成功",
                   r.status_code == 200, f"status={r.status_code} body={r.text[:120]}")
            # 删除后 404
            r = await cli.get(f"/v1/agent/u/workflows/{tmp_id}", headers=h1)
            record("G1-DEL-02b", "删除后访问 404", r.status_code == 404,
                   f"status={r.status_code}")

    print("\n===== G1 剩余用例汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    for x in RESULTS:
        if not x["pass"]:
            print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")


asyncio.run(main())
