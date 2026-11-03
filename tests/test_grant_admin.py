"""
资源授权管理（PRD docs/RequirementsAnalysis/resource-grant-admin-prd.md）单元测试

覆盖：
1. §6.3 主体有效性校验：不存在/禁用主体不放行，恢复后自动恢复（cus/usr/org）
2. §6.1 组织维度判定：org 授权 → 成员 cus 放行；移除成员/停用组织/授权过期 → 拒绝；组织间隔离
3. check_many / list_by_subject 的 org 合并与去重（选择器视图与判定语义一致）
4. org_ids 缓存：读穿命中 / 失效删除（mock RedisCache，不依赖真实 Redis）
5. admin_grant_router 校验分支：非法类型、过期时间校验、主体校验、batch 逐条独立（§6.4）、
   /list 筛选与 enrich（资源已删除标注）、/subjects、/resource-options

运行：.venv/Scripts/python.exe -m unittest tests.test_grant_admin -v
说明：DB 使用 sqlite 内存库；路由协程直接调用（admin_id 显式传入，绕过 require_superuser 依赖）。
"""
import importlib.util
import json
import os as _os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from tortoise import Tortoise

from base.common.setting import get_model_list
from base.common.authz.service import (
    ResourceGrantService,
    _customer_org_ids,
    invalidate_customer_org_cache,
    is_subject_active,
)

# admin_grant_router 所在包 __init__ 链导入 rag_service（模块级 asyncio.create_task 需运行中事件循环），
# 故按文件路径加载模块绕开包级副作用；模块级仅 fastapi/pydantic/tortoise/base.common 绝对导入，安全。
import importlib.util
import os as _os

_agr_path = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
    "base", "plugins", "agent", "api", "v1", "admin_grant_router.py",
)
_spec = importlib.util.spec_from_file_location(
    "base.plugins.agent.api.v1.admin_grant_router", _agr_path
)
agr = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = agr
_spec.loader.exec_module(agr)


def _body(resp) -> dict:
    """SuccessResponse/ErrorResponse 为 JSONResponse 子类，业务字段在序列化 body 中"""
    return json.loads(resp.body)

TEST_MODULES = get_model_list()


async def _init_db():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TEST_MODULES})
    await Tortoise.generate_schemas()


async def _close_db():
    await Tortoise.close_connections()


class GrantAdminTestCase(unittest.IsolatedAsyncioTestCase):
    """共享夹具：cus 9001/9002、usr 9003、org 901/902 + 成员关系"""

    async def asyncSetUp(self):
        await _init_db()
        from base.plugins.customer.models.customer import Customer
        from base.core.users.models.users import User
        from base.plugins.customer.models.customer_organization import (
            CustomerOrganization,
            CustomerOrganizationMember,
        )
        self.Customer = Customer
        self.User = User
        self.Org = CustomerOrganization
        self.Member = CustomerOrganizationMember

        await Customer.create(id=9001, username="cus9001", nickname="客户甲", is_active=True)
        await Customer.create(id=9002, username="cus9002", is_active=True)
        await User.create(id=9003, username="usr9003", email="a@t.com", is_active=True)
        await CustomerOrganization.create(id=901, name="组织一", owner_customer_id=9001, status="active")
        await CustomerOrganization.create(id=902, name="组织二", owner_customer_id=9002, status="active")
        # 9001 ∈ 901（active）；9002 ∉ 任何组织
        await CustomerOrganizationMember.create(org_id=901, customer_id=9001, role="owner", status="active")

        # 测试隔离（OB-N4-02 同类）：真实 Redis 启用时清空 org_ids 缓存，避免跨用例脏读。
        # 注意：单例 Redis client 绑定首个用例的 event loop，跨用例操作可能命中死连接静默失败，
        # 故先强制重连（在当前 loop 内新建连接）再清理，保证清理确定性。
        from base.common.cache import RedisCache
        await _reset_redis_client()
        if RedisCache.is_enabled():
            cache = await RedisCache.get_instance()
            await cache.delete_pattern("authz:org_ids:*")

    async def asyncTearDown(self):
        await _close_db()


async def _reset_redis_client() -> None:
    """重连 Redis 单例（消除跨 event loop 死连接），仅测试环境使用"""
    from base.common.cache import RedisCache
    inst = await RedisCache.get_instance()
    if getattr(inst, "_client", None) is not None:
        try:
            await inst._client.aclose()
        except Exception:
            pass
        inst._client = None
    from base.common.setting import settings
    if getattr(settings, "REDIS_ENABLED", False):
        await inst.connect()


# ============================================================
# 1. §6.3 主体有效性校验
# ============================================================
class SubjectActiveTest(GrantAdminTestCase):

    async def test_active_subjects(self):
        self.assertTrue(await is_subject_active("cus", 9001))
        self.assertTrue(await is_subject_active("usr", 9003))
        self.assertTrue(await is_subject_active("org", 901))

    async def test_missing_or_disabled_subject(self):
        self.assertFalse(await is_subject_active("cus", 99999))      # 不存在
        self.assertFalse(await is_subject_active("xyz", 1))          # 未知类型
        cus = await self.Customer.get(id=9002)
        cus.is_active = False
        await cus.save()
        self.assertFalse(await is_subject_active("cus", 9002))       # 已禁用
        org = await self.Org.get(id=902)
        org.status = "disabled"
        await org.save()
        self.assertFalse(await is_subject_active("org", 902))        # 组织停用

    async def test_disabled_subject_denied_even_with_grant(self):
        """有授权记录但主体被禁用 → 不放行；恢复后自动恢复（§6.3）"""
        await ResourceGrantService.grant(("cus", 9002), "kb", "1")
        self.assertTrue(await ResourceGrantService.check_resource_access(("cus", 9002), "kb", "1"))
        cus = await self.Customer.get(id=9002)
        cus.is_active = False
        await cus.save()
        self.assertFalse(await ResourceGrantService.check_resource_access(("cus", 9002), "kb", "1"))
        cus.is_active = True
        await cus.save()
        self.assertTrue(await ResourceGrantService.check_resource_access(("cus", 9002), "kb", "1"))


# ============================================================
# 2. §6.1 组织维度判定
# ============================================================
class OrgDimensionTest(GrantAdminTestCase):

    async def test_org_grant_allows_member(self):
        """组织获授权 → active 成员 customer 判定放行（自身无记录）"""
        await ResourceGrantService.grant(("org", 901), "model", "m1")
        self.assertTrue(await ResourceGrantService.check_resource_access(("cus", 9001), "model", "m1"))
        # 非成员不受影响
        self.assertFalse(await ResourceGrantService.check_resource_access(("cus", 9002), "model", "m1"))

    async def test_removed_member_denied(self):
        await ResourceGrantService.grant(("org", 901), "model", "m1")
        m = await self.Member.get(org_id=901, customer_id=9001)
        m.status = "removed"
        await m.save()
        self.assertFalse(await ResourceGrantService.check_resource_access(("cus", 9001), "model", "m1"))

    async def test_disabled_org_denied(self):
        await ResourceGrantService.grant(("org", 901), "model", "m1")
        org = await self.Org.get(id=901)
        org.status = "disabled"
        await org.save()
        self.assertFalse(await ResourceGrantService.check_resource_access(("cus", 9001), "model", "m1"))

    async def test_expired_org_grant_denied(self):
        await ResourceGrantService.grant(
            ("org", 901), "model", "m1", expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)
        )
        self.assertFalse(await ResourceGrantService.check_resource_access(("cus", 9001), "model", "m1"))

    async def test_org_isolation(self):
        """组织间隔离：org2 的授权不惠及 org1 成员"""
        await ResourceGrantService.grant(("org", 902), "kb", "5")
        self.assertFalse(await ResourceGrantService.check_resource_access(("cus", 9001), "kb", "5"))

    async def test_usr_no_org_dimension(self):
        """usr 主体不走组织维度（组织是 customer 域概念）"""
        await ResourceGrantService.grant(("org", 901), "tool", "t1")
        self.assertFalse(await ResourceGrantService.check_resource_access(("usr", 9003), "tool", "t1"))

    async def test_check_many_merges_org(self):
        """check_many：自身命中一部分，org 补查命中剩余，未授权排除"""
        await ResourceGrantService.grant(("cus", 9001), "agent", "11")
        await ResourceGrantService.grant(("org", 901), "agent", "22")
        await ResourceGrantService.grant(("org", 902), "agent", "33")  # 非所属组织
        allowed = await ResourceGrantService.check_many(("cus", 9001), "agent", ["11", "22", "33", "44"])
        self.assertEqual(allowed, {"11", "22"})

    async def test_list_by_subject_merges_org_dedup(self):
        """list_by_subject：cus 视图合并 org 授权，同资源自身记录优先（去重）"""
        await ResourceGrantService.grant(("cus", 9001), "kb", "1")
        await ResourceGrantService.grant(("org", 901), "kb", "1")   # 与自身重复 → 去重
        await ResourceGrantService.grant(("org", 901), "kb", "2")
        records = await ResourceGrantService.list_by_subject(("cus", 9001), "kb")
        pairs = {(r.resource_id, r.owner_type) for r in records}
        self.assertEqual(pairs, {("1", "cus"), ("2", "org")})

    async def test_list_by_subject_org_only_valid(self):
        """only_valid 对合并后的 org 记录同样生效（过期剔除）"""
        await ResourceGrantService.grant(
            ("org", 901), "kb", "9", expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)
        )
        records = await ResourceGrantService.list_by_subject(("cus", 9001), "kb", only_valid=True)
        self.assertEqual(records, [])
        records_all = await ResourceGrantService.list_by_subject(("cus", 9001), "kb", only_valid=False)
        self.assertEqual(len(records_all), 1)


# ============================================================
# 3. org_ids 缓存（mock RedisCache）
# ============================================================
class OrgIdsCacheTest(GrantAdminTestCase):

    def _mock_cache(self, get_return=None, enabled=True):
        cache = AsyncMock()
        cache.is_enabled = MagicMock(return_value=enabled)  # is_enabled 为同步方法
        cache.get.return_value = get_return
        return cache

    def _patch_cache(self, cache):
        # get_instance 为 async classmethod，patch 需返回 awaitable
        return patch("base.common.cache.RedisCache.get_instance", new=AsyncMock(return_value=cache))

    async def test_cache_hit_skips_db(self):
        cache = self._mock_cache(get_return="901")
        with self._patch_cache(cache):
            ids = await _customer_org_ids(9001)
        self.assertEqual(ids, [901])
        cache.get.assert_awaited_once()

    async def test_cache_miss_writes_back(self):
        cache = self._mock_cache(get_return=None)
        with self._patch_cache(cache):
            ids = await _customer_org_ids(9001)
        self.assertEqual(ids, [901])
        cache.set.assert_awaited_once_with("authz:org_ids:9001", "901", expire=300)

    async def test_cache_disabled_falls_back_to_db(self):
        cache = self._mock_cache(enabled=False)
        with self._patch_cache(cache):
            ids = await _customer_org_ids(9001)
        self.assertEqual(ids, [901])
        cache.get.assert_not_awaited()

    async def test_cache_error_degrades_gracefully(self):
        cache = AsyncMock()
        cache.is_enabled = MagicMock(side_effect=RuntimeError("redis down"))
        with self._patch_cache(cache):
            ids = await _customer_org_ids(9001)
        self.assertEqual(ids, [901])  # 降级直查库，不阻断

    async def test_invalidate_deletes_key(self):
        cache = self._mock_cache()
        with self._patch_cache(cache):
            await invalidate_customer_org_cache(9001)
        cache.delete.assert_awaited_once_with("authz:org_ids:9001")


# ============================================================
# 4. admin_grant_router 校验分支与端点
# ============================================================
class AdminGrantRouterTest(GrantAdminTestCase):

    # ---------- 入参校验 ----------
    def test_parse_expires(self):
        self.assertIsNone(agr._parse_expires(None))
        self.assertEqual(agr._parse_expires("not-a-date"), "invalid")
        past = (datetime.now() - timedelta(minutes=1)).isoformat()
        self.assertEqual(agr._parse_expires(past), "past")
        future = (datetime.now() + timedelta(days=1)).isoformat()
        self.assertIsInstance(agr._parse_expires(future), datetime)

    async def test_grant_invalid_types(self):
        r = await agr.grant_resource(
            agr.GrantSchema(owner_type="cus", owner_id=9001, resource_type="bad", resource_id="1"), admin_id=1)
        self.assertFalse(_body(r)["success"])
        r = await agr.grant_resource(
            agr.GrantSchema(owner_type="bad", owner_id=9001, resource_type="kb", resource_id="1"), admin_id=1)
        self.assertFalse(_body(r)["success"])

    async def test_grant_rejects_inactive_subject(self):
        """§6.3：不允许向不存在/已禁用主体发放授权"""
        r = await agr.grant_resource(
            agr.GrantSchema(owner_type="cus", owner_id=99999, resource_type="kb", resource_id="1"), admin_id=1)
        self.assertFalse(_body(r)["success"])

    async def test_grant_rejects_past_expires(self):
        r = await agr.grant_resource(
            agr.GrantSchema(owner_type="cus", owner_id=9001, resource_type="kb", resource_id="1",
                            expires_at=(datetime.now() - timedelta(minutes=5)).isoformat()), admin_id=1)
        self.assertFalse(_body(r)["success"])

    async def test_grant_org_ok(self):
        r = await agr.grant_resource(
            agr.GrantSchema(owner_type="org", owner_id=901, resource_type="node_type", resource_id="hitl"), admin_id=1)
        self.assertTrue(_body(r)["success"])
        self.assertEqual(_body(r)["data"]["owner_type"], "org")

    async def test_grant_rejects_missing_resource(self):
        """OB-1：资源不存在/已停用 → 拒绝授权"""
        r = await agr.grant_resource(
            agr.GrantSchema(owner_type="cus", owner_id=9001, resource_type="kb", resource_id="999999"), admin_id=1)
        self.assertFalse(_body(r)["success"])
        r = await agr.grant_resource(
            agr.GrantSchema(owner_type="cus", owner_id=9001, resource_type="node_type", resource_id="ghost"), admin_id=1)
        self.assertFalse(_body(r)["success"])

    # ---------- batch 逐条独立（§6.4） ----------
    async def test_batch_partial_failure(self):
        payload = agr.BatchGrantSchema(
            resource_type="node_type", resource_id="hitl",
            subjects=[
                agr.SubjectItem(owner_type="cus", owner_id=9001),   # 成功
                agr.SubjectItem(owner_type="org", owner_id=901),    # 成功
                agr.SubjectItem(owner_type="cus", owner_id=99999),  # 失败：主体不存在
                agr.SubjectItem(owner_type="bad", owner_id=1),      # 失败：非法类型
            ],
        )
        r = await agr.batch_grant(payload, admin_id=1)
        self.assertTrue(_body(r)["success"])
        self.assertEqual(len(_body(r)["data"]["succeeded"]), 2)
        self.assertEqual(len(_body(r)["data"]["failed"]), 2)
        reasons = [f["reason"] for f in _body(r)["data"]["failed"]]
        self.assertTrue(any("不存在" in x or "禁用" in x for x in reasons))
        self.assertTrue(any("非法主体类型" in x for x in reasons))
        # 成功条真实落库
        self.assertTrue(await ResourceGrantService.check_resource_access(("cus", 9001), "node_type", "hitl"))

    async def test_batch_rejects_missing_resource(self):
        """OB-1：batch 同样校验资源有效性"""
        payload = agr.BatchGrantSchema(
            resource_type="kb", resource_id="999999",
            subjects=[agr.SubjectItem(owner_type="cus", owner_id=9001)],
        )
        r = await agr.batch_grant(payload, admin_id=1)
        self.assertFalse(_body(r)["success"])

    async def test_batch_idempotent_created_flag(self):
        payload = agr.BatchGrantSchema(
            resource_type="node_type", resource_id="sub_agent",
            subjects=[agr.SubjectItem(owner_type="cus", owner_id=9001)],
        )
        r1 = await agr.batch_grant(payload, admin_id=1)
        self.assertTrue(_body(r1)["data"]["succeeded"][0]["created"])
        r2 = await agr.batch_grant(payload, admin_id=1)
        self.assertFalse(_body(r2)["data"]["succeeded"][0]["created"])  # 幂等刷新，非新增

    # ---------- /list 筛选与 enrich ----------
    async def test_list_filters_and_enrich(self):
        await ResourceGrantService.grant(("cus", 9001), "node_type", "hitl", granted_by="admin:1")
        await ResourceGrantService.grant(("org", 901), "node_type", "tool", granted_by="admin:1",
                                         expires_at=datetime.now() + timedelta(days=1))

        r = await agr.list_grants(page=1, page_size=20, resource_type="node_type",
                                  owner_type=None, status=None, keyword=None, admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 2)
        item = [i for i in _body(r)["data"]["items"] if i["owner_type"] == "cus"][0]
        self.assertEqual(item["owner_label"], "客户甲")           # cus 昵称 enrich
        self.assertEqual(item["resource_label"], "人工节点")       # node_type 标签 enrich
        self.assertFalse(item["resource_deleted"])
        self.assertEqual(item["status"], "valid")

        # 状态筛选
        r = await agr.list_grants(page=1, page_size=20, resource_type=None, owner_type=None,
                                  status="expired", keyword=None, admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 0)
        # 主体类型筛选
        r = await agr.list_grants(page=1, page_size=20, resource_type=None, owner_type="org",
                                  status=None, keyword=None, admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 1)
        # 关键词命中主体名称
        r = await agr.list_grants(page=1, page_size=20, resource_type=None, owner_type=None,
                                  status=None, keyword="客户甲", admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 1)
        # 关键词无命中 → 空页
        r = await agr.list_grants(page=1, page_size=20, resource_type=None, owner_type=None,
                                  status=None, keyword="不存在xyz", admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 0)

    async def test_list_resource_deleted_flag(self):
        """§6.2：资源编码不在受限映射内 → 标注已删除"""
        await ResourceGrantService.grant(("cus", 9001), "node_type", "ghost_node", granted_by="admin:1")
        r = await agr.list_grants(page=1, page_size=20, resource_type="node_type",
                                  owner_type=None, status=None, keyword=None, admin_id=1)
        item = _body(r)["data"]["items"][0]
        self.assertTrue(item["resource_deleted"])

    # ---------- /by-subject ----------
    async def test_by_subject_merges_org(self):
        await ResourceGrantService.grant(("cus", 9001), "kb", "1")
        await ResourceGrantService.grant(("org", 901), "kb", "2")
        r = await agr.list_grants_by_subject(owner_type="cus", owner_id=9001, admin_id=1)
        self.assertEqual({i["resource_id"] for i in _body(r)["data"]["items"]}, {"1", "2"})
        r = await agr.list_grants_by_subject(owner_type="bad", owner_id=1, admin_id=1)
        self.assertFalse(_body(r)["success"])

    # ---------- /subjects ----------
    async def test_subjects_options(self):
        r = await agr.list_subject_options(type="cus", keyword="客户甲", page=1, page_size=20, admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 1)
        self.assertEqual(_body(r)["data"]["items"][0]["label"], "客户甲")
        r = await agr.list_subject_options(type="org", keyword=None, page=1, page_size=20, admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 2)
        r = await agr.list_subject_options(type="usr", keyword=None, page=1, page_size=20, admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 1)
        # 禁用主体不出现在选择器（§6.3）
        cus = await self.Customer.get(id=9002)
        cus.is_active = False
        await cus.save()
        r = await agr.list_subject_options(type="cus", keyword=None, page=1, page_size=20, admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 1)
        r = await agr.list_subject_options(type="bad", keyword=None, page=1, page_size=20, admin_id=1)
        self.assertFalse(_body(r)["success"])

    # ---------- /resource-options ----------
    async def test_resource_options_node_type(self):
        r = await agr.list_resource_options(type="node_type", keyword=None, admin_id=1)
        codes = {i["id"] for i in _body(r)["data"]["items"]}
        self.assertEqual(codes, {"hitl", "sub_agent", "tool"})
        r = await agr.list_resource_options(type="node_type", keyword="人工", admin_id=1)
        self.assertEqual([i["id"] for i in _body(r)["data"]["items"]], ["hitl"])
        r = await agr.list_resource_options(type="bad", keyword=None, admin_id=1)
        self.assertFalse(_body(r)["success"])

    # ---------- revoke ----------
    async def test_revoke_idempotent(self):
        schema = agr.GrantSchema(owner_type="org", owner_id=901, resource_type="node_type", resource_id="tool")
        await agr.grant_resource(schema, admin_id=1)
        r = await agr.revoke_resource(schema, admin_id=1)
        self.assertEqual(_body(r)["data"]["deleted"], 1)
        r = await agr.revoke_resource(schema, admin_id=1)
        self.assertEqual(_body(r)["data"]["deleted"], 0)


if __name__ == "__main__":
    unittest.main()
