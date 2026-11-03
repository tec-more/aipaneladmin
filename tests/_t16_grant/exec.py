"""测试节点3 主执行脚本：资源授权管理
用法: .venv/Scripts/python.exe tests/_t16_grant/exec.py [SEC|FUNC|CACHE|E2E|EXC|NFR|ALL]
输出: tests/_t16_grant/results.json + 控制台逐条 PASS/FAIL
"""
import asyncio
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import aiohttp

BASE = "http://127.0.0.1:9998/api"
GRANTS = f"{BASE}/v1/agent/admin/grants"
U_RES = f"{BASE}/v1/agent/u/resources"

HERE = os.path.dirname(__file__)
RESULTS_FILE = os.path.join(HERE, "results.json")
ADMIN_TOKEN = open(os.path.join(HERE, "token.txt")).read().strip()

# 测试数据 ID（见 seed.py）
CUS_A, CUS_B, CUS_C, CUS_D = 2, 3, 4, 5   # A∈org1, B∈org2, C无组织, D禁用
CUS_EXIST1 = 1                            # t15test ∈ org1
ORG_A, ORG_B, ORG_C = 1, 2, 3             # C 已停用
USR_ADMIN, USR_PLAIN = 1, 2
MODEL_ON, MODEL_OFF = "16", "18"
KB_ON, KB_OFF = "22", "21"
TOOL_ON, TOOL_OFF = "1", "2"
AGENT_ON, AGENT_OFF = "10", "11"

RESULTS = []


def rec(group, cid, desc, expected, actual, passed, note=""):
    verdict = "PASS" if passed else "FAIL"
    RESULTS.append(dict(group=group, id=cid, desc=desc, expected=expected,
                        actual=str(actual)[:400], verdict=verdict, note=note))
    print(f"[{group}] {cid} {verdict} | {desc} | 实际: {str(actual)[:180]}" + (f" | 注: {note}" if note else ""))


async def http(session, method, url, token=None, body=None, params=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    t0 = time.time()
    try:
        async with session.request(method, url, json=body, params=params, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
            elapsed = (time.time() - t0) * 1000
            try:
                data = await resp.json()
            except Exception:
                data = {"_text": (await resp.text())[:300]}
            return resp.status, data, elapsed
    except Exception as e:
        return -1, {"_error": str(e)}, (time.time() - t0) * 1000


def redis_cli(*args):
    r = subprocess.run(["docker", "exec", "aipanel-redis-test", "redis-cli", "-a", "Test@Redis123", *args],
                       capture_output=True, text=True, timeout=10)
    return r.stdout.strip()


async def login(session, path, payload):
    st, data, _ = await http(session, "POST", f"{BASE}{path}", body=payload)
    d = data.get("data") or {}
    token = d.get("access_token") or d.get("token")
    return token, st, data


async def setup_passwords():
    """ORM 重置测试账号密码"""
    from tortoise import Tortoise
    from base.common.setting import get_model_list
    from base.common.security import get_password_hash
    await Tortoise.init(db_url="postgres://admin:Admin@123@127.0.0.1:15432/aipaneladmin",
                        modules={"models": get_model_list()})
    from base.plugins.customer.models.customer import Customer
    from base.core.users.models.users import User
    for cid in (CUS_A, CUS_B, CUS_C, CUS_D, CUS_EXIST1):
        c = await Customer.get(id=cid)
        c.password = get_password_hash("T16@Cus123")
        await c.save()
    u = await User.get(id=USR_PLAIN)
    for f in ("password", "hashed_password", "password_hash"):
        if hasattr(u, f):
            setattr(u, f, get_password_hash("T16@User123"))
    await u.save()
    await Tortoise.close_connections()
    print("[setup] passwords reset")


async def db_scalar(sql):
    import asyncpg
    conn = await asyncpg.connect(host="127.0.0.1", port=15432, user="admin",
                                 password="Admin@123", database="aipaneladmin", timeout=10)
    try:
        return await conn.fetchval(sql)
    finally:
        await conn.close()


async def db_rows(sql):
    import asyncpg
    conn = await asyncpg.connect(host="127.0.0.1", port=15432, user="admin",
                                 password="Admin@123", database="aipaneladmin", timeout=10)
    try:
        return [dict(r) for r in await conn.fetch(sql)]
    finally:
        await conn.close()


# ================= SEC =================
async def run_sec(session, ctx):
    G = "SEC"
    # SEC-01 无 token
    st, d, _ = await http(session, "GET", f"{GRANTS}/list")
    rec(G, "SEC-01", "无token访问/list", "401", st, st == 401)
    # SEC-02 非superuser list（节点4：预期更新为 403/404，D7 裁定 API 层 403 安全语义等效已接受）
    st, d, _ = await http(session, "GET", f"{GRANTS}/list", token=ctx["user_tok"])
    rec(G, "SEC-02", "非superuser访问/list", "403/404(D7裁定)", st, st in (403, 404),
        note="" if st in (403, 404) else f"实际{st},预期403/404")
    # SEC-03 非superuser 单条授权
    st, d, _ = await http(session, "POST", GRANTS, token=ctx["user_tok"],
                          body={"owner_type": "cus", "owner_id": CUS_A, "resource_type": "kb", "resource_id": KB_ON})
    rec(G, "SEC-03", "非superuser POST /grants", "403/404(D7)", st, st in (403, 404))
    # SEC-04 非superuser 批量
    st, d, _ = await http(session, "POST", f"{GRANTS}/batch", token=ctx["user_tok"],
                          body={"resource_type": "kb", "resource_id": KB_ON,
                                "subjects": [{"owner_type": "cus", "owner_id": CUS_A}]})
    rec(G, "SEC-04", "非superuser POST /batch", "403/404(D7)", st, st in (403, 404))
    # SEC-05 非superuser 撤销
    st, d, _ = await http(session, "DELETE", GRANTS, token=ctx["user_tok"],
                          body={"owner_type": "cus", "owner_id": CUS_A, "resource_type": "kb", "resource_id": KB_ON})
    rec(G, "SEC-05", "非superuser DELETE /grants", "403/404(D7)", st, st in (403, 404))
    # SEC-06 非superuser subjects/resource-options/by-subject/GET""
    for name, url, params in [
        ("subjects", f"{GRANTS}/subjects", {"type": "cus"}),
        ("resource-options", f"{GRANTS}/resource-options", {"type": "kb"}),
        ("by-subject", f"{GRANTS}/by-subject", {"owner_type": "cus", "owner_id": CUS_A}),
        ("by-resource GET''", GRANTS, {"resource_type": "kb", "resource_id": KB_ON}),
    ]:
        st, d, _ = await http(session, "GET", url, token=ctx["user_tok"], params=params)
        rec(G, f"SEC-06-{name}", f"非superuser GET {name}", "403/404(D7)", st, st in (403, 404))
    # SEC-07 customer token 访问管理端
    st, d, _ = await http(session, "GET", f"{GRANTS}/list", token=ctx["cus_tok"])
    rec(G, "SEC-07", "customer token访问/list", "401/404", st, st in (401, 403, 404))
    # SEC-08 superuser 正常
    st, d, _ = await http(session, "GET", f"{GRANTS}/list", token=ctx["admin_tok"])
    rec(G, "SEC-08", "superuser访问/list", "200 success", f"{st}/{d.get('success')}", st == 200 and d.get("success"))


# ================= FUNC =================
async def run_func(session, ctx):
    G = "FUNC"
    tok = ctx["admin_tok"]
    # 清理：撤销本组可能残留的授权
    for ow, oid, rt, rid in [("cus", CUS_C, "kb", KB_ON), ("org", ORG_B, "model", MODEL_ON),
                             ("cus", CUS_A, "tool", TOOL_ON), ("org", ORG_A, "tool", TOOL_ON),
                             ("cus", CUS_C, "node_type", "hitl"), ("cus", CUS_D, "kb", KB_ON)]:
        await http(session, "DELETE", GRANTS, token=tok,
                   body={"owner_type": ow, "owner_id": oid, "resource_type": rt, "resource_id": rid})

    # FUNC-01 列表默认（含既有4条）
    st, d, _ = await http(session, "GET", f"{GRANTS}/list", token=tok)
    items = d["data"]["items"]
    rec(G, "FUNC-01", "列表默认查询(分页/倒序/enrich字段)", "200+items含enrich",
        f"total={d['data']['total']}, keys={sorted(items[0].keys()) if items else []}",
        st == 200 and d["data"]["total"] >= 0 and (not items or "owner_label" in items[0]))

    # FUNC-02 新建授权（单条，cus_C + kb22，无过期时间）
    st, d, _ = await http(session, "POST", GRANTS, token=tok,
                          body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": KB_ON})
    rec(G, "FUNC-02", "新建授权(长期有效)", "success+expires_at=null",
        f"{st}/{d.get('success')}/exp={d.get('data',{}).get('expires_at')}",
        st == 200 and d.get("success") and d["data"]["expires_at"] is None)

    # FUNC-03 幂等重复授权（不传expires）
    st, d, _ = await http(session, "POST", GRANTS, token=tok,
                          body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": KB_ON})
    cnt = await db_scalar(f"SELECT count(*) FROM resource_grant WHERE owner_type='cus' AND owner_id={CUS_C} "
                          f"AND resource_type='kb' AND resource_id='{KB_ON}'")
    rec(G, "FUNC-03", "重复授权幂等(无重复记录)", "200 success, DB count=1", f"{st}, count={cnt}",
        st == 200 and cnt == 1)

    # FUNC-04 Q4裁定：先带过期授权→再不带过期重复授权→原过期时间保持不变
    future = "2030-01-01T00:00:00"
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "node_type", "resource_id": "hitl"})
    await http(session, "POST", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "node_type",
                     "resource_id": "hitl", "expires_at": future})
    st, d, _ = await http(session, "POST", GRANTS, token=tok,
                          body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "node_type", "resource_id": "hitl"})
    exp = await db_scalar(f"SELECT expires_at FROM resource_grant WHERE owner_type='cus' AND owner_id={CUS_C} "
                          f"AND resource_type='node_type' AND resource_id='hitl'")
    # 节点4：断言由字符串包含改为瞬时等值比较（时区安全）：
    # 前端naive本地时间 2030-01-01T00:00:00+08 == 2029-12-31T16:00:00Z，同一时刻即视为保持
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    _expected = _dt(2030, 1, 1, 0, 0, tzinfo=_tz(_td(hours=8)))
    _actual = exp if exp is None or exp.tzinfo else exp.replace(tzinfo=_tz.utc)
    _keep = exp is not None and abs((_actual - _expected).total_seconds()) < 1
    rec(G, "FUNC-04", "Q4:重复授权不传expires→保持原过期时间", "expires_at保持2030-01-01+08同一时刻",
        str(exp), _keep)

    # FUNC-05 带新过期时间重复授权→刷新
    future2 = "2031-06-01T00:00:00"
    await http(session, "POST", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "node_type",
                     "resource_id": "hitl", "expires_at": future2})
    exp2 = await db_scalar(f"SELECT expires_at FROM resource_grant WHERE owner_type='cus' AND owner_id={CUS_C} "
                           f"AND resource_type='node_type' AND resource_id='hitl'")
    rec(G, "FUNC-05", "重复授权带expires→刷新过期时间", "expires_at=2031", str(exp2),
        exp2 is not None and "2031" in str(exp2))

    # FUNC-06 batch逐条独立（§6.4）
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_A, "resource_type": "tool", "resource_id": TOOL_ON})
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "org", "owner_id": ORG_A, "resource_type": "tool", "resource_id": TOOL_ON})
    st, d, _ = await http(session, "POST", f"{GRANTS}/batch", token=tok,
                          body={"resource_type": "tool", "resource_id": TOOL_ON,
                                "subjects": [{"owner_type": "cus", "owner_id": CUS_A},
                                             {"owner_type": "org", "owner_id": ORG_A},
                                             {"owner_type": "cus", "owner_id": 999999},
                                             {"owner_type": "bad", "owner_id": 1}]})
    dat = d.get("data", {})
    rec(G, "FUNC-06", "batch逐条独立(2成功2失败)", "succeeded=2 failed=2",
        f"s={len(dat.get('succeeded',[]))} f={len(dat.get('failed',[]))} reasons={[x.get('reason') for x in dat.get('failed',[])]}",
        st == 200 and len(dat.get("succeeded", [])) == 2 and len(dat.get("failed", [])) == 2)

    # FUNC-07 batch幂等created标志
    st, d, _ = await http(session, "POST", f"{GRANTS}/batch", token=tok,
                          body={"resource_type": "tool", "resource_id": TOOL_ON,
                                "subjects": [{"owner_type": "cus", "owner_id": CUS_A}]})
    created = d["data"]["succeeded"][0]["created"]
    rec(G, "FUNC-07", "batch幂等created=false", "created=false", created, created is False)

    # FUNC-08 撤销+重复撤销幂等
    st, d, _ = await http(session, "DELETE", GRANTS, token=tok,
                          body={"owner_type": "cus", "owner_id": CUS_A, "resource_type": "tool", "resource_id": TOOL_ON})
    d1 = d.get("data", {}).get("deleted")
    st2, d2, _ = await http(session, "DELETE", GRANTS, token=tok,
                            body={"owner_type": "cus", "owner_id": CUS_A, "resource_type": "tool", "resource_id": TOOL_ON})
    d2v = d2.get("data", {}).get("deleted")
    rec(G, "FUNC-08", "撤销幂等(deleted 1→0)", "1→0", f"{d1}→{d2v}", d1 == 1 and d2v == 0)

    # FUNC-09 筛选组合
    st, d, _ = await http(session, "GET", f"{GRANTS}/list", token=tok, params={"owner_type": "org"})
    org_total = d["data"]["total"]
    st2, d2, _ = await http(session, "GET", f"{GRANTS}/list", token=tok, params={"status": "expired"})
    exp_total = d2["data"]["total"]
    st3, d3, _ = await http(session, "GET", f"{GRANTS}/list", token=tok, params={"keyword": "T16组织A"})
    kw_total = d3["data"]["total"]
    st4, d4, _ = await http(session, "GET", f"{GRANTS}/list", token=tok, params={"keyword": "不存在xyz"})
    kw0 = d4["data"]["total"]
    rec(G, "FUNC-09", "筛选(owner_type/status/keyword/无命中)",
        "各自正确过滤", f"org={org_total},expired={exp_total},kw={kw_total},kw0={kw0}",
        org_total >= 1 and kw_total >= 1 and kw0 == 0)

    # FUNC-10 by-subject cus合并org（cus A∈org1；org1有tool授权残留? FUNC-06给org1授权过tool→已撤销cus部分,org部分保留）
    st, d, _ = await http(session, "GET", f"{GRANTS}/by-subject", token=tok,
                          params={"owner_type": "cus", "owner_id": CUS_A})
    rids = {(i["resource_type"], i["resource_id"], i["owner_type"]) for i in d["data"]["items"]}
    rec(G, "FUNC-10", "by-subject合并org授权", "含org tool记录",
        str(rids), ("tool", TOOL_ON, "org") in rids)

    # FUNC-11 按资源反查 GET ""
    st, d, _ = await http(session, "GET", GRANTS, token=tok,
                          params={"resource_type": "tool", "resource_id": TOOL_ON})
    owners = {(i["owner_type"], i["owner_id"]) for i in d["data"]["items"]}
    rec(G, "FUNC-11", "按资源反查被授权主体", "含(org,1)", str(owners), ("org", ORG_A) in owners)

    # FUNC-12 subjects选择器（含禁用排除）
    st, d, _ = await http(session, "GET", f"{GRANTS}/subjects", token=tok, params={"type": "cus", "page_size": 50})
    cus_ids = {i["id"] for i in d["data"]["items"]}
    st2, d2, _ = await http(session, "GET", f"{GRANTS}/subjects", token=tok, params={"type": "org", "page_size": 50})
    org_ids = {i["id"] for i in d2["data"]["items"]}
    st3, d3, _ = await http(session, "GET", f"{GRANTS}/subjects", token=tok, params={"type": "usr", "page_size": 50})
    usr_ids = {i["id"] for i in d3["data"]["items"]}
    st4, d4, _ = await http(session, "GET", f"{GRANTS}/subjects", token=tok,
                            params={"type": "cus", "keyword": "t16cusa"})
    kw_hit = d4["data"]["total"]
    rec(G, "FUNC-12", "subjects选择器(禁用排除/搜索)",
        "cus不含禁用5,org不含停用3,usr含1/2,搜索命中1",
        f"cus={sorted(cus_ids)},org={sorted(org_ids)},usr={sorted(usr_ids)},kw={kw_hit}",
        CUS_D not in cus_ids and ORG_C not in org_ids and ORG_A in org_ids
        and USR_ADMIN in usr_ids and kw_hit == 1)

    # FUNC-13 resource-options五类（停用排除）
    opts = {}
    for t in ("model", "kb", "tool", "agent", "node_type"):
        st, d, _ = await http(session, "GET", f"{GRANTS}/resource-options", token=tok, params={"type": t})
        opts[t] = {i["id"] for i in d.get("data", {}).get("items", [])} if st == 200 else f"HTTP{st}"
    ok = (MODEL_ON in opts["model"] and MODEL_OFF not in opts["model"]
          and KB_ON in opts["kb"] and KB_OFF not in opts["kb"]
          and TOOL_ON in opts["tool"] and TOOL_OFF not in opts["tool"]
          and AGENT_ON in opts["agent"] and AGENT_OFF not in opts["agent"]
          and opts["node_type"] == {"hitl", "sub_agent", "tool"})
    rec(G, "FUNC-13", "resource-options五类(停用排除/OB-3)", "停用资源均不出现",
        json.dumps({k: sorted(v) if isinstance(v, set) else v for k, v in opts.items()}, ensure_ascii=False), ok)

    # FUNC-14 向禁用主体授权→拒绝（§6.3）
    st, d, _ = await http(session, "POST", GRANTS, token=tok,
                          body={"owner_type": "cus", "owner_id": CUS_D, "resource_type": "kb", "resource_id": KB_ON})
    rec(G, "FUNC-14", "向禁用customer授权→拒绝", "success=false", f"{d.get('success')}/{d.get('msg')}",
        d.get("success") is False)

    # FUNC-15 向停用/不存在资源授权→拒绝（OB-1）
    st1, d1, _ = await http(session, "POST", GRANTS, token=tok,
                            body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": KB_OFF})
    st2, d2, _ = await http(session, "POST", GRANTS, token=tok,
                            body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": "999999"})
    st3, d3, _ = await http(session, "POST", GRANTS, token=tok,
                            body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "node_type", "resource_id": "ghost"})
    rec(G, "FUNC-15", "OB-1:停用/不存在/ghost资源→拒绝", "均success=false",
        f"停用:{d1.get('success')},不存在:{d2.get('success')},ghost:{d3.get('success')}",
        not d1.get("success") and not d2.get("success") and not d3.get("success"))

    # FUNC-16 过期时间校验
    st1, d1, _ = await http(session, "POST", GRANTS, token=tok,
                            body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb",
                                  "resource_id": KB_ON, "expires_at": "2020-01-01T00:00:00"})
    st2, d2, _ = await http(session, "POST", GRANTS, token=tok,
                            body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb",
                                  "resource_id": KB_ON, "expires_at": "not-a-date"})
    rec(G, "FUNC-16", "过期时间:过去/非法格式→拒绝", "均success=false",
        f"past:{d1.get('success')}/{d1.get('msg')}, invalid:{d2.get('success')}/{d2.get('msg')}",
        not d1.get("success") and not d2.get("success"))

    # FUNC-17 §6.2 资源已删除/已停用双标注（D4 复核；D8 裁定后改用非关键词路径查询）
    await db_scalar("DELETE FROM resource_grant WHERE owner_type='cus' AND owner_id=999")
    await db_scalar("INSERT INTO resource_grant (owner_type, owner_id, resource_type, resource_id, effect, "
                    "granted_by, created_at, updated_at) VALUES ('cus', 999, 'node_type', 'ghost_node', 'allow', "
                    "'admin:1', NOW(), NOW())")
    await db_scalar(f"INSERT INTO resource_grant (owner_type, owner_id, resource_type, resource_id, effect, "
                    f"granted_by, created_at, updated_at) VALUES ('cus', 999, 'kb', '{KB_OFF}', 'allow', "
                    f"'admin:1', NOW(), NOW())")
    await db_scalar(f"INSERT INTO resource_grant (owner_type, owner_id, resource_type, resource_id, effect, "
                    f"granted_by, created_at, updated_at) VALUES ('cus', 999, 'kb', '{KB_ON}', 'allow', "
                    f"'admin:1', NOW(), NOW())")
    st, d, _ = await http(session, "GET", f"{GRANTS}/list", token=tok,
                          params={"resource_type": "node_type", "page_size": 100})
    ghost = [i for i in d["data"]["items"] if i["resource_id"] == "ghost_node"]
    g_del = ghost[0]["resource_deleted"] if ghost else None
    g_ina = ghost[0]["resource_inactive"] if ghost else None
    st2, d2, _ = await http(session, "GET", f"{GRANTS}/list", token=tok,
                            params={"resource_type": "kb", "page_size": 100})
    kb_off = [i for i in d2["data"]["items"] if i["resource_id"] == KB_OFF and i["owner_id"] == 999]
    kb_on = [i for i in d2["data"]["items"] if i["resource_id"] == KB_ON and i["owner_id"] == 999]
    off_pair = (kb_off[0]["resource_deleted"], kb_off[0]["resource_inactive"]) if kb_off else None
    on_pair = (kb_on[0]["resource_deleted"], kb_on[0]["resource_inactive"]) if kb_on else None
    rec(G, "FUNC-17", "§6.2 已删除/已停用/正常三态标注(D4)",
        "ghost=(T,F) 停用kb=(F,T) 正常kb=(F,F)",
        f"ghost=({g_del},{g_ina}) off={off_pair} on={on_pair}",
        g_del is True and g_ina is False and off_pair == (False, True) and on_pair == (False, False))
    await db_scalar("DELETE FROM resource_grant WHERE owner_type='cus' AND owner_id=999")


# ================= CACHE =================
async def run_cache(session, ctx):
    G = "CACHE"
    tok_a = ctx["cus_a_tok"]
    # CACHE-01 读穿：customer A 触发判定后Redis应写入 org_ids 键
    redis_cli("DEL", f"authz:org_ids:{CUS_A}")
    st, d, _ = await http(session, "GET", U_RES, token=tok_a, params={"type": "kb"})
    time.sleep(0.3)
    keys = redis_cli("KEYS", f"authz:org_ids:{CUS_A}")
    val = redis_cli("GET", f"authz:org_ids:{CUS_A}")
    rec(G, "CACHE-01", "org_ids读穿写Redis", f"键存在,值含org{ORG_A}", f"keys={keys},val={val}",
        f"authz:org_ids:{CUS_A}" in keys and str(ORG_A) in val)

    # CACHE-02 TTL≈300
    ttl = redis_cli("TTL", f"authz:org_ids:{CUS_A}")
    rec(G, "CACHE-02", "TTL=300s兜底", "0<TTL<=300", ttl, ttl.isdigit() and 0 < int(ttl) <= 300)

    # CACHE-03 成员变动失效（remove_member→键删除）
    from tortoise import Tortoise
    from base.common.setting import get_model_list
    await Tortoise.init(db_url="postgres://admin:Admin@123@127.0.0.1:15432/aipaneladmin",
                        modules={"models": get_model_list()})
    from base.plugins.customer.services.organization_service import CustomerOrganizationService
    from base.plugins.customer.models.customer_organization import CustomerOrganizationMember
    # 先把 CUS_A 从 org1 移除（成员角色非owner? seed中CUS_A是org1 owner——不能移除owner；改用既有customer 1∈org1 member）
    redis_cli("DEL", f"authz:org_ids:{CUS_EXIST1}")
    # 触发customer 1的缓存（用customer1 token访问）
    await http(session, "GET", U_RES, token=ctx["cus1_tok"], params={"type": "kb"})
    time.sleep(0.3)
    k1 = redis_cli("KEYS", f"authz:org_ids:{CUS_EXIST1}")
    await CustomerOrganizationService.remove_member(ORG_A, CUS_A, CUS_EXIST1)
    time.sleep(0.3)
    k2 = redis_cli("KEYS", f"authz:org_ids:{CUS_EXIST1}")
    rec(G, "CACHE-03", "remove_member→缓存失效", "键被删除", f"前:{k1} 后:{k2}", k1 != "" and k2 == "")
    # 恢复成员关系
    m = await CustomerOrganizationMember.filter(org_id=ORG_A, customer_id=CUS_EXIST1).first()
    if m:
        m.status = "active"
        await m.save()
    from base.common.authz.service import invalidate_customer_org_cache
    await invalidate_customer_org_cache(CUS_EXIST1)

    # CACHE-04 add_member→失效（节点4：先清理节点3残留的 org2/customer4 成员关系，保证幂等）
    m_pre = await CustomerOrganizationMember.filter(org_id=ORG_B, customer_id=CUS_C).first()
    if m_pre:
        m_pre.status = "removed"
        await m_pre.save()
    redis_cli("DEL", f"authz:org_ids:{CUS_C}")
    await http(session, "GET", U_RES, token=ctx["cus_c_tok"], params={"type": "kb"})
    time.sleep(0.3)
    k1 = redis_cli("KEYS", f"authz:org_ids:{CUS_C}")
    await CustomerOrganizationService.add_member(ORG_B, CUS_B, CUS_C)
    time.sleep(0.3)
    k2 = redis_cli("KEYS", f"authz:org_ids:{CUS_C}")
    rec(G, "CACHE-04", "add_member→缓存失效", "键被删除", f"前:{k1} 后:{k2}", k1 != "" and k2 == "")

    # CACHE-05 Redis停用降级：停容器→u/resources仍可用
    subprocess.run(["docker", "stop", "aipanel-redis-test"], capture_output=True, timeout=30)
    time.sleep(1)
    st, d, _ = await http(session, "GET", U_RES, token=tok_a, params={"type": "kb"})
    rec(G, "CACHE-05", "Redis宕机降级(判定不受影响)", "200 success", f"{st}/{d.get('success')}",
        st == 200 and d.get("success"))
    subprocess.run(["docker", "start", "aipanel-redis-test"], capture_output=True, timeout=30)
    time.sleep(2)
    await Tortoise.close_connections()


# ================= E2E =================
async def run_e2e(session, ctx):
    G = "E2E"
    tok = ctx["admin_tok"]
    tok_c = ctx["cus_c_tok"]   # CUS_C 现属 org B（CACHE-04 加入）
    tok_a = ctx["cus_a_tok"]

    def res_ids(d):
        return {i.get("id") or i.get("resource_id") for i in (d.get("data") or {}).get("items", [])}

    # E2E-01 授权→web-user选择器可见→撤销→消失
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": KB_ON})
    st, d, _ = await http(session, "GET", U_RES, token=tok_c, params={"type": "kb"})
    before = res_ids(d)
    await http(session, "POST", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": KB_ON})
    st2, d2, _ = await http(session, "GET", U_RES, token=tok_c, params={"type": "kb"})
    after = res_ids(d2)
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": KB_ON})
    st3, d3, _ = await http(session, "GET", U_RES, token=tok_c, params={"type": "kb"})
    gone = res_ids(d3)
    rec(G, "E2E-01", "授权→选择器可见→撤销→消失", "∅→含22→∅",
        f"前:{sorted(map(str,before))} 中:{sorted(map(str,after))} 后:{sorted(map(str,gone))}",
        KB_ON not in {str(x) for x in before} and KB_ON in {str(x) for x in after}
        and KB_ON not in {str(x) for x in gone})

    # E2E-02 组织授权→成员可见/非成员不可见
    await http(session, "POST", GRANTS, token=tok,
               body={"owner_type": "org", "owner_id": ORG_B, "resource_type": "model", "resource_id": MODEL_ON})
    st, d, _ = await http(session, "GET", U_RES, token=tok_c, params={"type": "model"})
    member_view = res_ids(d)
    st2, d2, _ = await http(session, "GET", U_RES, token=tok_a, params={"type": "model"})
    nonmember_view = res_ids(d2)
    rec(G, "E2E-02", "org授权→orgB成员(C)可见/A非成员不可见", "C含16,A不含16",
        f"C:{sorted(map(str,member_view))} A:{sorted(map(str,nonmember_view))}",
        MODEL_ON in {str(x) for x in member_view} and MODEL_ON not in {str(x) for x in nonmember_view})

    # E2E-03 成员加入即时生效（Q8：服务端判定即时）
    from tortoise import Tortoise
    from base.common.setting import get_model_list
    await Tortoise.init(db_url="postgres://admin:Admin@123@127.0.0.1:15432/aipaneladmin",
                        modules={"models": get_model_list()})
    from base.plugins.customer.services.organization_service import CustomerOrganizationService
    from base.plugins.customer.models.customer_organization import CustomerOrganizationMember
    # 预热 D 的缓存（D已禁用，改用既有customer1? 用CUS_EXIST1，属orgA；先对其查model → 缓存orgA）
    # 更简单：把 customer1 加入 orgB → 即时可见 model16（orgB有授权）
    cus1_tok = ctx["cus1_tok"]
    st0, d0, _ = await http(session, "GET", U_RES, token=cus1_tok, params={"type": "model"})
    pre = res_ids(d0)
    await CustomerOrganizationService.add_member(ORG_B, CUS_B, CUS_EXIST1)
    st1, d1, _ = await http(session, "GET", U_RES, token=cus1_tok, params={"type": "model"})
    post = res_ids(d1)
    rec(G, "E2E-03", "成员加入orgB→即时获得org授权(Q8)", "加入后立即可见16",
        f"前:{sorted(map(str,pre))} 后:{sorted(map(str,post))}",
        MODEL_ON not in {str(x) for x in pre} and MODEL_ON in {str(x) for x in post})

    # E2E-04 成员移除即时失效
    await CustomerOrganizationService.remove_member(ORG_B, CUS_B, CUS_EXIST1)
    st2, d2, _ = await http(session, "GET", U_RES, token=cus1_tok, params={"type": "model"})
    gone = res_ids(d2)
    rec(G, "E2E-04", "成员移出orgB→即时失去授权(Q8)", "移除后不可见16",
        f"{sorted(map(str,gone))}", MODEL_ON not in {str(x) for x in gone})

    # E2E-05 禁用主体不放行（§6.3）：禁用CUS_C→选择器空；恢复→恢复
    from base.plugins.customer.models.customer import Customer
    await http(session, "POST", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": KB_ON})
    c = await Customer.get(id=CUS_C)
    c.is_active = False
    await c.save()
    st3, d3, _ = await http(session, "GET", U_RES, token=tok_c, params={"type": "kb"})
    disabled_view = res_ids(d3)
    c.is_active = True
    await c.save()
    st4, d4, _ = await http(session, "GET", U_RES, token=tok_c, params={"type": "kb"})
    restored = res_ids(d4)
    rec(G, "E2E-05", "§6.3禁用不放行/恢复自动恢复", "禁用∅→恢复含22",
        f"禁用:{sorted(map(str,disabled_view))} 恢复:{sorted(map(str,restored))}",
        KB_ON not in {str(x) for x in disabled_view} and KB_ON in {str(x) for x in restored})
    await Tortoise.close_connections()

    # E2E-06 过期授权不放行
    await db_scalar(f"UPDATE resource_grant SET expires_at=NOW()-INTERVAL '1 hour' WHERE owner_type='cus' "
                    f"AND owner_id={CUS_C} AND resource_type='kb' AND resource_id='{KB_ON}'")
    st5, d5, _ = await http(session, "GET", U_RES, token=tok_c, params={"type": "kb"})
    expired_view = res_ids(d5)
    rec(G, "E2E-06", "过期授权不放行(§5.2)", "不含22", f"{sorted(map(str,expired_view))}",
        KB_ON not in {str(x) for x in expired_view})
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": KB_ON})


# ================= EXC/BND =================
async def run_exc(session, ctx):
    G = "EXC"
    tok = ctx["admin_tok"]
    # EXC-01 非法类型
    st1, d1, _ = await http(session, "POST", GRANTS, token=tok,
                            body={"owner_type": "bad", "owner_id": 1, "resource_type": "kb", "resource_id": "22"})
    st2, d2, _ = await http(session, "POST", GRANTS, token=tok,
                            body={"owner_type": "cus", "owner_id": 1, "resource_type": "bad", "resource_id": "22"})
    st3, d3, _ = await http(session, "GET", f"{GRANTS}/list", token=tok, params={"resource_type": "bad"})
    st4, d4, _ = await http(session, "GET", f"{GRANTS}/subjects", token=tok, params={"type": "bad"})
    st5, d5, _ = await http(session, "GET", f"{GRANTS}/resource-options", token=tok, params={"type": "bad"})
    rec(G, "EXC-01", "非法owner/resource类型全端点拒绝", "均success=false",
        f"grant-owner:{d1.get('success')},grant-res:{d2.get('success')},list:{d3.get('success')},subj:{d4.get('success')},opt:{d5.get('success')}",
        all(not x.get("success") for x in (d1, d2, d3, d4, d5)))

    # BND-01 resource_id 超长(65)
    st, d, _ = await http(session, "POST", GRANTS, token=tok,
                          body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": "x" * 65})
    rec("BND", "BND-01", "resource_id 65字符→422(schema max64)", "422", st, st == 422)

    # BND-02 resource_id 空
    st, d, _ = await http(session, "POST", GRANTS, token=tok,
                          body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "kb", "resource_id": ""})
    rec("BND", "BND-02", "resource_id空→422", "422", st, st == 422)

    # BND-03 subjects 空/101
    st1, d1, _ = await http(session, "POST", f"{GRANTS}/batch", token=tok,
                            body={"resource_type": "kb", "resource_id": KB_ON, "subjects": []})
    subs = [{"owner_type": "cus", "owner_id": CUS_C}] * 101
    st2, d2, _ = await http(session, "POST", f"{GRANTS}/batch", token=tok,
                            body={"resource_type": "kb", "resource_id": KB_ON, "subjects": subs})
    rec("BND", "BND-03", "subjects空/超100→422", "422/422", f"{st1}/{st2}", st1 == 422 and st2 == 422)

    # BND-04 owner_id=0/负
    st1, d1, _ = await http(session, "POST", GRANTS, token=tok,
                            body={"owner_type": "cus", "owner_id": 0, "resource_type": "kb", "resource_id": KB_ON})
    st2, d2, _ = await http(session, "POST", GRANTS, token=tok,
                            body={"owner_type": "cus", "owner_id": -5, "resource_type": "kb", "resource_id": KB_ON})
    rec("BND", "BND-04", "owner_id=0/负数→422", "422/422", f"{st1}/{st2}", st1 == 422 and st2 == 422)

    # BND-05 分页参数越界
    st1, d1, _ = await http(session, "GET", f"{GRANTS}/list", token=tok, params={"page": 0})
    st2, d2, _ = await http(session, "GET", f"{GRANTS}/list", token=tok, params={"page_size": 101})
    rec("BND", "BND-05", "page=0/page_size=101→422", "422/422", f"{st1}/{st2}", st1 == 422 and st2 == 422)

    # BND-06 关键词特殊字符
    st, d, _ = await http(session, "GET", f"{GRANTS}/list", token=tok, params={"keyword": "%_'\"\\;DROP"})
    rec("BND", "BND-06", "关键词特殊字符不报错", "200", st, st == 200)

    # EXC-02 batch重复主体（幂等语义观察）
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "agent", "resource_id": AGENT_ON})
    st, d, _ = await http(session, "POST", f"{GRANTS}/batch", token=tok,
                          body={"resource_type": "agent", "resource_id": AGENT_ON,
                                "subjects": [{"owner_type": "cus", "owner_id": CUS_C},
                                             {"owner_type": "cus", "owner_id": CUS_C}]})
    dat = d.get("data", {})
    cnt = await db_scalar(f"SELECT count(*) FROM resource_grant WHERE owner_type='cus' AND owner_id={CUS_C} "
                          f"AND resource_type='agent' AND resource_id='{AGENT_ON}'")
    rec(G, "EXC-02", "batch同主体重复→幂等", "2成功(1创1刷),DB=1",
        f"s={len(dat.get('succeeded',[]))},created={[x.get('created') for x in dat.get('succeeded',[])]},db={cnt}",
        len(dat.get("succeeded", [])) == 2 and cnt == 1)
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "agent", "resource_id": AGENT_ON})

    # EXC-03 撤销不存在记录（幂等）
    st, d, _ = await http(session, "DELETE", GRANTS, token=tok,
                          body={"owner_type": "cus", "owner_id": 777777, "resource_type": "kb", "resource_id": KB_ON})
    rec(G, "EXC-03", "撤销不存在记录→幂等deleted=0", "success,deleted=0",
        f"{d.get('success')}/{d.get('data',{}).get('deleted')}",
        d.get("success") and d.get("data", {}).get("deleted") == 0)


# ================= NFR =================
async def run_nfr(session, ctx):
    G = "NFR"
    tok = ctx["admin_tok"]
    # NFR-01 并发幂等：10并发同主体同资源授权→DB仅1条
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "node_type", "resource_id": "sub_agent"})
    payload = {"resource_type": "node_type", "resource_id": "sub_agent",
               "subjects": [{"owner_type": "cus", "owner_id": CUS_C}]}
    tasks = [http(session, "POST", f"{GRANTS}/batch", token=tok, body=payload) for _ in range(10)]
    results = await asyncio.gather(*tasks)
    codes = [r[0] for r in results]
    created_cnt = sum(1 for r in results if r[1].get("data", {}).get("succeeded", [{}])[0].get("created"))
    cnt = await db_scalar(f"SELECT count(*) FROM resource_grant WHERE owner_type='cus' AND owner_id={CUS_C} "
                          f"AND resource_type='node_type' AND resource_id='sub_agent'")
    rec(G, "NFR-01", "10并发同组合授权→DB唯一/幂等", "count=1", f"codes={codes},created_true={created_cnt},db={cnt}",
        all(c == 200 for c in codes) and cnt == 1)
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "cus", "owner_id": CUS_C, "resource_type": "node_type", "resource_id": "sub_agent"})

    # NFR-02 审计留痕（含Q6实测）：清理→grant→revoke→查data_change_log
    await db_scalar("DELETE FROM resource_grant WHERE owner_type='org' AND owner_id=2 AND resource_type='node_type' AND resource_id='hitl'")
    mark_before = await db_scalar("SELECT count(*) FROM data_change_log WHERE table_name='resource_grant'")
    await http(session, "POST", GRANTS, token=tok,
               body={"owner_type": "org", "owner_id": ORG_B, "resource_type": "node_type", "resource_id": "hitl"})
    time.sleep(1.5)
    after_create = await db_scalar("SELECT count(*) FROM data_change_log WHERE table_name='resource_grant'")
    rows_c = await db_rows("SELECT change_type, record_id FROM data_change_log WHERE table_name='resource_grant' "
                           "ORDER BY id DESC LIMIT 5")
    await http(session, "DELETE", GRANTS, token=tok,
               body={"owner_type": "org", "owner_id": ORG_B, "resource_type": "node_type", "resource_id": "hitl"})
    time.sleep(1.5)
    after_delete = await db_scalar("SELECT count(*) FROM data_change_log WHERE table_name='resource_grant'")
    rows_d = await db_rows("SELECT change_type, record_id FROM data_change_log WHERE table_name='resource_grant' "
                           "ORDER BY id DESC LIMIT 5")
    create_captured = after_create > mark_before
    delete_captured = after_delete > after_create
    rec(G, "NFR-02a", "审计:grant发放留痕(PRD§5.4)", "CREATE被捕获",
        f"before={mark_before},after_create={after_create},rows={rows_c}", create_captured)
    rec(G, "NFR-02b", "Q6实测:revoke撤销留痕", "DELETE被捕获(若否则缺陷)",
        f"after_delete={after_delete},rows={rows_d}", delete_captured,
        note="revoke走QuerySet.delete()，monkey-patch仅覆盖Model实例delete" if not delete_captured else "")

    # NFR-03 列表接口耗时
    times = []
    for _ in range(10):
        st, d, ms = await http(session, "GET", f"{GRANTS}/list", token=tok)
        times.append(ms)
    times.sort()
    p50, p95 = times[len(times) // 2], times[int(len(times) * 0.95) - 1]
    rec(G, "NFR-03", "list接口耗时(10次)", "P50<500ms", f"P50={p50:.0f}ms P95={p95:.0f}ms max={times[-1]:.0f}ms",
        p50 < 500)


async def main():
    groups = sys.argv[1].upper().split(",") if len(sys.argv) > 1 else ["ALL"]
    await setup_passwords()
    async with aiohttp.ClientSession() as session:
        ctx = {"admin_tok": ADMIN_TOKEN}
        # 登录非superuser与customers
        ctx["user_tok"], st, d = await login(session, "/v1/auth/login",
                                             {"username": "test_wf_user", "password": "T16@User123"})
        print(f"[setup] test_wf_user login: {st} token={'OK' if ctx['user_tok'] else 'FAIL'}")
        for key, email in [("cus_a_tok", "t16cusa@t.com"), ("cus_b_tok", "t16cusb@t.com"),
                           ("cus_c_tok", "t16cusc@t.com"), ("cus1_tok", "t15test@example.com")]:
            ctx[key], st, d = await login(session, "/v1/customer/auth/login",
                                          {"email": email, "password": "T16@Cus123"})
            print(f"[setup] {email} login: {st} token={'OK' if ctx[key] else f'FAIL {d}'}")
        ctx["cus_tok"] = ctx["cus_a_tok"]

        run_all = "ALL" in groups
        if run_all or "SEC" in groups:
            await run_sec(session, ctx)
        if run_all or "FUNC" in groups:
            await run_func(session, ctx)
        if run_all or "CACHE" in groups:
            await run_cache(session, ctx)
        if run_all or "E2E" in groups:
            await run_e2e(session, ctx)
        if run_all or "EXC" in groups:
            await run_exc(session, ctx)
        if run_all or "NFR" in groups:
            await run_nfr(session, ctx)

    json.dump(RESULTS, open(RESULTS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    passed = sum(1 for r in RESULTS if r["verdict"] == "PASS")
    print(f"\n===== 汇总: {passed}/{len(RESULTS)} PASS =====")
    for r in RESULTS:
        if r["verdict"] == "FAIL":
            print(f"FAIL: [{r['group']}] {r['id']} {r['desc']} | 实际: {r['actual']}")


asyncio.run(main())
