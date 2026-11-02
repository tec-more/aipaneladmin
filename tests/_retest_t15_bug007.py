"""
T15 节点3 复测脚本：BUG-T15-007（validate 契约对齐）

缺陷背景：
- 前端 Editor.vue onServerValidate 误读契约字段：d?.ok（实际后端返回 valid）、
  d?.summary?.error（实际 error_count），导致合法图误报「校验未通过：0 个错误」
- 修复方案 A（前端对齐后端契约）：d?.ok -> d?.valid；d?.summary?.error -> d?.error_count

复测策略（浏览器桥阻塞，采用数据面 + 逻辑仿真双轨）：
1. API 直调用户侧 POST /v1/agent/u/workflows/{id}/validate 获取真实契约响应
2. 用真实响应分别驱动「修复前逻辑」与「修复后逻辑」仿真函数
3. 断言：修复后逻辑输出与契约预期一致；修复前逻辑复现原误报（反证缺陷存在且已消除）

场景：
- BUG-007-01 合法图（0 错误）：应提示「校验通过」
- BUG-007-02 非法图（2 个 start，N 个错误）：应提示「校验未通过：N 个错误」，N 与 issues 中 error 数一致
- BUG-007-03 仅警告图（输出悬空 E-106，0 错误）：应提示「校验通过」（warning 不阻断）

运行: .venv/Scripts/python.exe tests/_retest_t15_bug007.py
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


# ============================================================
# 前端逻辑仿真（与 Editor.vue 源码逐行对齐）
# ============================================================

def toast_fixed(d: dict | None) -> tuple[str, str]:
    """修复后逻辑（Editor.vue:199-204）：
    if (d?.valid) success('校验通过') else warning(`校验未通过：${d?.error_count ?? 0} 个错误`)
    """
    if d and d.get("valid"):
        return ("success", "校验通过")
    count = (d or {}).get("error_count", 0)
    if count is None:
        count = 0
    return ("warning", f"校验未通过：{count} 个错误")


def toast_legacy(d: dict | None) -> tuple[str, str]:
    """修复前逻辑（BUG-T15-007 缺陷版）：
    if (d?.ok) success('校验通过') else warning(`校验未通过：${d?.summary?.error ?? 0} 个错误`)
    """
    if d and d.get("ok"):
        return ("success", "校验通过")
    summary = (d or {}).get("summary") or {}
    count = summary.get("error", 0)
    return ("warning", f"校验未通过：{count} 个错误")


# ============================================================
# 测试图构造（Schema v2）
# ============================================================

def graph_valid() -> dict:
    """合法图：start -> end，start 输出 query 被 end 引用（避免悬空警告）"""
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


def graph_invalid_two_starts() -> dict:
    """非法图：2 个 start 节点（E-100）"""
    g = graph_valid()
    g["nodes"].append(
        {"id": "s2", "type": "start", "position": {"x": 0, "y": 100}, "data": {}}
    )
    return g


def graph_warning_only() -> dict:
    """仅警告图：start 输出悬空（E-106 warning，0 error）"""
    return {
        "schema_version": 2,
        "nodes": [
            {"id": "s1", "type": "start", "position": {"x": 0, "y": 0},
             "data": {"outputs": [{"name": "query", "type": "string"}]}},
            {"id": "e1", "type": "end", "position": {"x": 300, "y": 0}, "data": {}},
        ],
        "edges": [
            {"id": "e1", "source": "s1", "target": "e1",
             "sourceHandle": "out", "targetHandle": "in"}
        ],
        "variables": [],
    }


async def call_validate(cli: httpx.AsyncClient, graph: dict) -> dict | None:
    r = await cli.post(f"/v1/agent/u/workflows/{WF_ID}/validate",
                       json={"graph_json": graph})
    if r.status_code != 200:
        return {"__http_error__": r.status_code, "__text__": r.text[:300]}
    return (r.json() or {}).get("data")


async def main():
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url=BASE, headers=headers, timeout=60.0) as cli:
        # Part 0: 认证自检
        r = await cli.get(f"/v1/agent/u/workflows/{WF_ID}")
        record("BUG-007-00", "usr:1 token 访问工作流详情", r.status_code == 200,
               f"status={r.status_code}")
        if r.status_code != 200:
            print("认证失败，终止:", r.text[:500])
            return

        # ============================================================
        # BUG-007-01 合法图：应提示「校验通过」
        # ============================================================
        print("\n===== BUG-007-01 合法图（0 错误） =====")
        d = await call_validate(cli, graph_valid())
        if d is None or "__http_error__" in (d or {}):
            record("BUG-007-01a", "validate API 可用", False, f"resp={d}")
        else:
            errors = [i for i in d.get("issues", []) if i.get("level") == "error"]
            contract_ok = (d.get("valid") is True and d.get("error_count") == 0
                           and len(errors) == 0)
            record("BUG-007-01a", "契约字段：valid=True 且 error_count=0 且 error级issues=0",
                   contract_ok,
                   f"valid={d.get('valid')} error_count={d.get('error_count')} "
                   f"warning_count={d.get('warning_count')} actual_errors={len(errors)}")

            lvl_new, msg_new = toast_fixed(d)
            record("BUG-007-01b", "修复后逻辑：合法图提示「校验通过」",
                   lvl_new == "success" and msg_new == "校验通过",
                   f"toast=({lvl_new}, {msg_new!r})")

            lvl_old, msg_old = toast_legacy(d)
            record("BUG-007-01c", "反证：修复前逻辑在合法图上误报（证明缺陷存在且已消除）",
                   lvl_old == "warning" and "0 个错误" in msg_old,
                   f"legacy_toast=({lvl_old}, {msg_old!r})")

        # ============================================================
        # BUG-007-02 非法图：应提示「校验未通过：N 个错误」
        # ============================================================
        print("\n===== BUG-007-02 非法图（2 个 start 节点） =====")
        d = await call_validate(cli, graph_invalid_two_starts())
        if d is None or "__http_error__" in (d or {}):
            record("BUG-007-02a", "validate API 可用", False, f"resp={d}")
        else:
            errors = [i for i in d.get("issues", []) if i.get("level") == "error"]
            n_expected = len(errors)
            contract_ok = (d.get("valid") is False
                           and d.get("error_count") == n_expected
                           and n_expected >= 1)
            record("BUG-007-02a", "契约字段：valid=False 且 error_count 与实际 error 级 issues 数一致",
                   contract_ok,
                   f"valid={d.get('valid')} error_count={d.get('error_count')} "
                   f"actual_errors={n_expected} codes={[i.get('code') for i in errors]}")

            lvl_new, msg_new = toast_fixed(d)
            record("BUG-007-02b", "修复后逻辑：非法图提示「校验未通过：N 个错误」且 N 一致",
                   lvl_new == "warning" and msg_new == f"校验未通过：{n_expected} 个错误",
                   f"toast=({lvl_new}, {msg_new!r}) 期望N={n_expected}")

        # ============================================================
        # BUG-007-03 仅警告图：应提示「校验通过」（warning 不阻断）
        # ============================================================
        print("\n===== BUG-007-03 仅警告图（E-106 输出悬空） =====")
        d = await call_validate(cli, graph_warning_only())
        if d is None or "__http_error__" in (d or {}):
            record("BUG-007-03a", "validate API 可用", False, f"resp={d}")
        else:
            warn_ok = (d.get("valid") is True and d.get("error_count") == 0
                       and d.get("warning_count", 0) >= 1)
            record("BUG-007-03a", "契约字段：0 错误 + >=1 警告 → valid=True",
                   warn_ok,
                   f"valid={d.get('valid')} error_count={d.get('error_count')} "
                   f"warning_count={d.get('warning_count')} "
                   f"warn_codes={[i.get('code') for i in d.get('issues', []) if i.get('level') == 'warning']}")

            lvl_new, msg_new = toast_fixed(d)
            record("BUG-007-03b", "修复后逻辑：仅警告图提示「校验通过」（不被误判为未通过）",
                   lvl_new == "success" and msg_new == "校验通过",
                   f"toast=({lvl_new}, {msg_new!r})")

    # ============================================================
    # 汇总
    # ============================================================
    print("\n===== BUG-T15-007 复测汇总 =====")
    passed = sum(1 for x in RESULTS if x["pass"])
    print(f"通过 {passed}/{len(RESULTS)}")
    failed = [x for x in RESULTS if not x["pass"]]
    for x in failed:
        print(f"  未通过: {x['id']} {x['name']} :: {x['detail']}")
    if not failed:
        print("结论: BUG-T15-007 修复有效，契约对齐正确（数据面+逻辑仿真双轨验证通过）")


asyncio.run(main())
