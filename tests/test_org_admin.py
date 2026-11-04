"""
组织管理后台（A3 裁剪版）单元测试

覆盖（docs/arch/resource-grant-admin-tech.md §3.2 组织列表缺口）：
1. GET /admin/organizations 分页 / keyword / status 筛选 / member_count
2. GET /admin/organizations/{id} 详情 enrich（resource_name + resource_status active|deleted|inactive）
3. POST /admin/organizations 创建组织（owner 自动成为 owner 成员）
4. POST /{id}/members 加成员 → check_resource_access 对该成员立即放行（缓存失效生效）
5. DELETE /{id}/members/{cid} 删成员 → check_resource_access 立即失效
6. 错误语义：组织不存在 404、重复成员/已是 owner 409、非法 role 400

运行：.venv/Scripts/python.exe -m pytest tests/test_org_admin.py -v
      （或 -m unittest tests.test_org_admin -v）
说明：DB 使用 sqlite 内存库；路由协程直接调用（admin_id 显式传入，绕过 require_superuser）。
"""
import json
import unittest
from unittest.mock import AsyncMock, patch

from tortoise import Tortoise

from base.common.authz.service import ResourceGrantService
from base.common.setting import get_model_list
from base.plugins.customer.api.v1 import organization_admin as oa

TEST_MODULES = get_model_list()


def _body(resp) -> dict:
    """SuccessResponse/ErrorResponse 为 JSONResponse 子类，业务字段在序列化 body 中"""
    return json.loads(resp.body)


class _FakeCache:
    """最小 Redis 替身：验证 authz:org_ids: 的读穿/写回/失效是否真正发生"""

    def __init__(self):
        self.store = {}

    def is_enabled(self):
        return True

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, expire=None):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)


async def _init_db():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TEST_MODULES})
    await Tortoise.generate_schemas()


class OrgAdminTestCase(unittest.IsolatedAsyncioTestCase):
    """共享夹具：cus 9001(owner)/9002(普通)/9003、org 901/902/903"""

    async def asyncSetUp(self):
        await _init_db()
        from base.plugins.customer.models.customer import Customer
        from base.plugins.customer.models.customer_organization import (
            CustomerOrganization,
            CustomerOrganizationMember,
        )

        self.Customer = Customer
        self.Org = CustomerOrganization
        self.Member = CustomerOrganizationMember

        await Customer.create(id=9001, username="cus9001", nickname="客户甲", is_active=True)
        await Customer.create(id=9002, username="cus9002", is_active=True)
        await Customer.create(id=9003, username="cus9003", is_active=True)
        await Customer.create(id=9004, username="cus9004", is_active=False)

        await CustomerOrganization.create(id=901, name="组织一", owner_customer_id=9001, status="active")
        await CustomerOrganization.create(id=902, name="组织二", owner_customer_id=9001, status="active")
        await CustomerOrganization.create(id=903, name="已停用组织", owner_customer_id=9001, status="disabled")
        await CustomerOrganizationMember.create(org_id=901, customer_id=9001, role="owner", status="active")
        await CustomerOrganizationMember.create(org_id=902, customer_id=9001, role="owner", status="active")
        await CustomerOrganizationMember.create(org_id=903, customer_id=9001, role="owner", status="active")

        # 真实 Redis 启用时清空 org_ids 缓存，避免跨用例脏读（同 test_grant_admin 处理）
        from base.common.cache import RedisCache
        await _reset_redis_client()
        if RedisCache.is_enabled():
            cache = await RedisCache.get_instance()
            await cache.delete_pattern("authz:org_ids:*")

    async def asyncTearDown(self):
        await Tortoise.close_connections()


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
# 1. 列表
# ============================================================
class OrgListViewTest(OrgAdminTestCase):

    async def test_pagination(self):
        r = await oa.list_organizations(page=1, page_size=2, keyword=None, status_filter=None, admin_id=1)
        data = _body(r)["data"]
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 2)
        self.assertEqual(data["items"][0]["id"], 903)      # 按 id 倒序
        self.assertEqual(data["items"][0]["owner_username"], "cus9001")
        self.assertEqual(data["items"][0]["member_count"], 1)

        r = await oa.list_organizations(page=2, page_size=2, keyword=None, status_filter=None, admin_id=1)
        self.assertEqual(len(_body(r)["data"]["items"]), 1)

    async def test_keyword_and_status(self):
        r = await oa.list_organizations(page=1, page_size=20, keyword="组织一", status_filter=None, admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 1)
        self.assertEqual(_body(r)["data"]["items"][0]["name"], "组织一")

        r = await oa.list_organizations(page=1, page_size=20, keyword=None, status_filter="disabled", admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 1)
        self.assertEqual(_body(r)["data"]["items"][0]["id"], 903)

        r = await oa.list_organizations(page=1, page_size=20, keyword="组织", status_filter="active", admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 2)

        r = await oa.list_organizations(page=1, page_size=20, keyword="不存在xyz", status_filter=None, admin_id=1)
        self.assertEqual(_body(r)["data"]["total"], 0)

    async def test_invalid_status(self):
        r = await oa.list_organizations(page=1, page_size=20, keyword=None, status_filter="bad", admin_id=1)
        self.assertFalse(_body(r)["success"])


# ============================================================
# 2. 详情 enrich
# ============================================================
class OrgDetailViewTest(OrgAdminTestCase):

    async def test_detail_with_grants_enrich(self):
        from base.plugins.agent.models.tool import Tool

        await Tool.create(id=7001, name="tool_on", display_name="在线工具", enabled=True)
        await Tool.create(id=7002, name="tool_off", display_name="停用工具", enabled=False)
        await ResourceGrantService.grant(("org", 901), "node_type", "hitl", granted_by="admin:1")
        await ResourceGrantService.grant(("org", 901), "node_type", "ghost_node", granted_by="admin:1")
        await ResourceGrantService.grant(("org", 901), "tool", "7001", granted_by="admin:1")
        await ResourceGrantService.grant(("org", 901), "tool", "7002", granted_by="admin:1")

        r = await oa.get_organization_detail(901, admin_id=1)
        data = _body(r)["data"]
        self.assertEqual(data["name"], "组织一")
        self.assertEqual(data["owner"], {"customer_id": 9001, "username": "cus9001"})
        self.assertEqual(len(data["members"]), 1)
        self.assertEqual(data["members"][0]["role"], "owner")
        self.assertIsNotNone(data["members"][0]["joined_at"])

        by_res = {(g["resource_type"], g["resource_id"]): g for g in data["grants"]}
        self.assertEqual(by_res[("node_type", "hitl")]["resource_name"], "人工节点")
        self.assertEqual(by_res[("node_type", "hitl")]["resource_status"], "active")
        self.assertEqual(by_res[("node_type", "ghost_node")]["resource_status"], "deleted")
        self.assertEqual(by_res[("tool", "7001")]["resource_name"], "在线工具")
        self.assertEqual(by_res[("tool", "7001")]["resource_status"], "active")
        self.assertEqual(by_res[("tool", "7002")]["resource_status"], "inactive")

    async def test_detail_not_found(self):
        r = await oa.get_organization_detail(99999, admin_id=1)
        self.assertFalse(_body(r)["success"])
        self.assertEqual(r.status_code, 404)


# ============================================================
# 3. 创建组织
# ============================================================
class OrgCreateTest(OrgAdminTestCase):

    async def test_create_organization_with_owner_member(self):
        r = await oa.create_organization(oa.CreateOrganizationSchema(name="新组织", owner_customer_id=9003), admin_id=1)
        body = _body(r)
        self.assertTrue(body["success"])
        org_id = body["data"]["id"]
        self.assertEqual(body["data"]["status"], "active")

        org = await self.Org.get(id=org_id)
        self.assertEqual(org.name, "新组织")
        self.assertEqual(org.owner_customer_id, 9003)
        membership = await self.Member.get(org_id=org_id, customer_id=9003)
        self.assertEqual(membership.role, "owner")
        self.assertEqual(membership.status, "active")

    async def test_create_rejects_inactive_owner(self):
        r = await oa.create_organization(
            oa.CreateOrganizationSchema(name="新组织2", owner_customer_id=9004), admin_id=1
        )
        self.assertFalse(_body(r)["success"])

    async def test_create_rejects_blank_name(self):
        r = await oa.create_organization(
            oa.CreateOrganizationSchema(name="   ", owner_customer_id=9001), admin_id=1
        )
        self.assertFalse(_body(r)["success"])


# ============================================================
# 4. 成员增删 + 缓存失效真实生效
# ============================================================
class OrgMemberCacheTest(OrgAdminTestCase):

    def _patch_cache(self, cache):
        return patch("base.common.cache.RedisCache.get_instance", new=AsyncMock(return_value=cache))

    async def test_add_member_immediately_grants_and_remove_revokes(self):
        """加成员 → org 授权立即对成员放行；删成员 → 立即失效（验证缓存失效而非等 TTL）"""
        cache = _FakeCache()
        with self._patch_cache(cache):
            await ResourceGrantService.grant(("org", 901), "model", "m1")
            # 预热：9002 尚未入组 → 判定 False，并把 org_ids=[] 写入缓存
            self.assertFalse(await ResourceGrantService.check_resource_access(("cus", 9002), "model", "m1"))
            self.assertEqual(cache.store.get("authz:org_ids:9002"), "")

            r = await oa.add_org_member(901, oa.AddMemberSchema(customer_id=9002, role="member"), admin_id=1)
            body = _body(r)
            self.assertTrue(body["success"])
            self.assertEqual(body["data"]["role"], "member")
            self.assertEqual(body["data"]["username"], "cus9002")
            # 缓存键被主动删除 → 下次判定回源命中所属组织
            self.assertNotIn("authz:org_ids:9002", cache.store)
            self.assertTrue(await ResourceGrantService.check_resource_access(("cus", 9002), "model", "m1"))
            self.assertEqual(cache.store.get("authz:org_ids:9002"), "901")

            r = await oa.remove_org_member(901, 9002, admin_id=1)
            self.assertTrue(_body(r)["success"])
            self.assertNotIn("authz:org_ids:9002", cache.store)
            self.assertFalse(await ResourceGrantService.check_resource_access(("cus", 9002), "model", "m1"))

    async def test_detail_reflects_new_member(self):
        await oa.add_org_member(901, oa.AddMemberSchema(customer_id=9002, role="admin"), admin_id=1)
        r = await oa.get_organization_detail(901, admin_id=1)
        roles = {m["customer_id"]: m["role"] for m in _body(r)["data"]["members"]}
        self.assertEqual(roles, {9001: "owner", 9002: "admin"})


# ============================================================
# 5. 成员接口错误语义
# ============================================================
class OrgMemberErrorTest(OrgAdminTestCase):

    async def test_org_not_found_404(self):
        r = await oa.add_org_member(99999, oa.AddMemberSchema(customer_id=9002, role="member"), admin_id=1)
        self.assertEqual(r.status_code, 404)
        r = await oa.remove_org_member(99999, 9002, admin_id=1)
        self.assertEqual(r.status_code, 404)

    async def test_owner_is_member_conflict_409(self):
        r = await oa.add_org_member(901, oa.AddMemberSchema(customer_id=9001, role="member"), admin_id=1)
        self.assertEqual(r.status_code, 409)
        self.assertFalse(_body(r)["success"])

    async def test_duplicate_member_conflict_409(self):
        await oa.add_org_member(901, oa.AddMemberSchema(customer_id=9002, role="member"), admin_id=1)
        r = await oa.add_org_member(901, oa.AddMemberSchema(customer_id=9002, role="admin"), admin_id=1)
        self.assertEqual(r.status_code, 409)

    async def test_invalid_role_400(self):
        r = await oa.add_org_member(901, oa.AddMemberSchema(customer_id=9002, role="owner"), admin_id=1)
        self.assertEqual(r.status_code, 400)
        r = await oa.add_org_member(901, oa.AddMemberSchema(customer_id=9002, role="superman"), admin_id=1)
        self.assertEqual(r.status_code, 400)

    async def test_remove_owner_conflict_409(self):
        r = await oa.remove_org_member(901, 9001, admin_id=1)
        self.assertEqual(r.status_code, 409)

    async def test_remove_non_member_400(self):
        r = await oa.remove_org_member(901, 9003, admin_id=1)
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
