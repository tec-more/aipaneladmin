"""
T2 / M8 权限与归属 单元测试与自测

覆盖（对应任务验证要求）：
1. ResourceGrantService：授权/判定/撤销/按主体查/按资源反查/过期与幂等
2. resolve_scope：cus 恒 self；usr 四档 data_scope（all/dept_tree/dept/custom/self）
3. L2 声明式过滤：双主体隔离、usr 四档叠加、公开只读并入、写操作严格归属
4. F8：越权 404（不暴露存在性）+ 审计 warn + 同主体 1 分钟 >10 次限流封禁 + alert
5. 自测 E2E：构造 cus/usr 双 token 交叉访问验证 404，本人访问 200，未认证 401

运行：.venv/Scripts/python.exe -m unittest tests.test_authz_m8 -v
说明：DB 使用 sqlite 内存库；Redis 未连接时自动退化进程内计数（与生产降级路径一致）；
审计落库通道以 mock 截获验证（不依赖 audit 表）。
"""
import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from tortoise import Tortoise

from base.common.setting import get_model_list
from base.common.authz.constants import (
    OwnerType,
    DataScope,
    ResourceType,
    RL_THRESHOLD,
)
from base.common.authz.context import OwnerContext, parse_owner_token
from base.common.authz.scope import resolve_scope, resolve_scope_user_ids
from base.common.authz.service import ResourceGrantService
from base.common.authz.filter import (
    OwnedResourceNotFound,
    get_owned_or_404,
    owned_queryset,
)
from base.common.authz.guard import assert_owner_access, recheck_owner
from base.common.authz.models.resource_grant import ResourceGrant
from base.common.security import create_access_token

# 与生产一致的完整模型注册（Tortoise 继承字段共享绑定要求，避免 default_connection=None）
TEST_MODULES = get_model_list()


async def _init_db():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TEST_MODULES})
    await Tortoise.generate_schemas()


async def _close_db():
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


class AuthzTestCase(unittest.IsolatedAsyncioTestCase):
    """共享 sqlite 内存库的测试基类"""

    async def asyncSetUp(self):
        await _init_db()

    async def asyncTearDown(self):
        await _close_db()


# ============================================================
# 1. ResourceGrantService
# ============================================================
class ResourceGrantServiceTest(AuthzTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        # §6.3 主体有效性校验落地后，判定要求主体真实存在且有效——补建测试主体
        from base.plugins.customer.models.customer import Customer
        from base.core.users.models.users import User
        for cid in (1001, 1002, 1003, 2001):
            await Customer.create(id=cid, username=f"cus{cid}", is_active=True)
        for uid in (7, 8, 9, 21):
            await User.create(id=uid, username=f"usr{uid}", email=f"u{uid}@t.com", is_active=True)

    async def test_grant_and_check(self):
        owner = OwnerContext(owner_type=OwnerType.CUS.value, owner_id=1001)
        await ResourceGrantService.grant(owner, ResourceType.MODEL.value, "m_gpt4o")
        self.assertTrue(
            await ResourceGrantService.check_resource_access(
                owner, ResourceType.MODEL.value, "m_gpt4o"
            )
        )

    async def test_check_denied_without_grant(self):
        owner = OwnerContext(owner_type=OwnerType.USR.value, owner_id=7)
        self.assertFalse(
            await ResourceGrantService.check_resource_access(
                owner, ResourceType.TOOL.value, "12"
            )
        )

    async def test_grant_idempotent(self):
        owner = ("cus", 1002)
        await ResourceGrantService.grant(owner, "kb", "3")
        await ResourceGrantService.grant(owner, "kb", "3")
        count = await ResourceGrant.filter(
            owner_type="cus", owner_id=1002, resource_type="kb", resource_id="3"
        ).count()
        self.assertEqual(count, 1)

    async def test_revoke(self):
        owner = ("usr", 8)
        await ResourceGrantService.grant(owner, "tool", "t1")
        deleted = await ResourceGrantService.revoke(owner, "tool", "t1")
        self.assertEqual(deleted, 1)
        self.assertFalse(
            await ResourceGrantService.check_resource_access(owner, "tool", "t1")
        )
        # 幂等撤销
        self.assertEqual(await ResourceGrantService.revoke(owner, "tool", "t1"), 0)

    async def test_expired_grant_denied(self):
        owner = ("cus", 1003)
        await ResourceGrantService.grant(
            owner, "model", "m_old",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        self.assertFalse(
            await ResourceGrantService.check_resource_access(owner, "model", "m_old")
        )

    async def test_check_many(self):
        owner = ("usr", 9)
        await ResourceGrantService.grant(owner, "node_type", "llm")
        await ResourceGrantService.grant(owner, "node_type", "rag_retrieval")
        allowed = await ResourceGrantService.check_many(
            owner, "node_type", ["llm", "rag_retrieval", "code", "http"]
        )
        self.assertEqual(allowed, {"llm", "rag_retrieval"})

    async def test_list_by_subject_and_resource(self):
        await ResourceGrantService.grant(("cus", 2001), "kb", "10")
        await ResourceGrantService.grant(("cus", 2001), "kb", "11")
        await ResourceGrantService.grant(("usr", 21), "kb", "10")

        subject_grants = await ResourceGrantService.list_by_subject(("cus", 2001), "kb")
        self.assertEqual({g.resource_id for g in subject_grants}, {"10", "11"})

        resource_grants = await ResourceGrantService.list_by_resource("kb", "10")
        self.assertEqual(
            {(g.owner_type, g.owner_id) for g in resource_grants},
            {("cus", 2001), ("usr", 21)},
        )


# ============================================================
# 2. resolve_scope（usr 四档 + cus）
# ============================================================
class ResolveScopeTest(AuthzTestCase):

    async def test_cus_scope_always_self(self):
        owner = OwnerContext(owner_type="cus", owner_id=5001)
        scope = await resolve_scope(owner)
        self.assertEqual(scope["data_scope"], DataScope.SELF.value)
        self.assertEqual(scope["org_ids"], [])

    async def _usr_scope(self, rbac_scope: dict):
        """以 mock 的 RBAC 结果驱动 resolve_scope"""
        with patch(
            "base.core.users.services.rbac_service.DataPermissionService.get_user_data_scope",
            new=AsyncMock(return_value=rbac_scope),
        ), patch(
            "base.core.users.services.rbac_service.DataPermissionService.get_dept_tree_ids_async",
            new=AsyncMock(return_value=[5, 6, 7]),
        ):
            owner = OwnerContext(owner_type="usr", owner_id=42)
            return await resolve_scope(owner)

    async def test_usr_scope_all(self):
        scope = await self._usr_scope(
            {"scope": "all", "dept_ids": [], "user_id": 42, "user_dept_id": 5}
        )
        self.assertEqual(scope["data_scope"], "all")
        self.assertEqual(scope["org_ids"], [])
        self.assertTrue(scope["is_superuser"])

    async def test_usr_scope_dept(self):
        scope = await self._usr_scope(
            {"scope": "dept", "dept_ids": [], "user_id": 42, "user_dept_id": 5}
        )
        self.assertEqual(scope["data_scope"], "dept")
        self.assertEqual(scope["org_ids"], [5])

    async def test_usr_scope_dept_tree(self):
        scope = await self._usr_scope(
            {"scope": "dept_tree", "dept_ids": [], "user_id": 42, "user_dept_id": 5}
        )
        self.assertEqual(scope["data_scope"], "dept_tree")
        self.assertEqual(scope["org_ids"], [5, 6, 7])

    async def test_usr_scope_custom(self):
        scope = await self._usr_scope(
            {"scope": "custom", "dept_ids": [8, 9], "user_id": 42, "user_dept_id": 5}
        )
        self.assertEqual(scope["data_scope"], "custom")
        self.assertEqual(scope["org_ids"], [8, 9])

    async def test_usr_scope_self_fallback(self):
        # RBAC 无角色 → self
        scope = await self._usr_scope({"scope": "self", "dept_ids": [], "user_id": 42})
        self.assertEqual(scope["data_scope"], "self")
        self.assertEqual(scope["org_ids"], [])

    async def test_resolve_scope_user_ids_dept(self):
        from base.core.users.models.users import User

        await User.create(username="u1", email="u1@t.com", dept_id=5)
        u2 = await User.create(username="u2", email="u2@t.com", dept_id=5)
        await User.create(username="u3", email="u3@t.com", dept_id=6)

        owner = OwnerContext(
            owner_type="usr", owner_id=u2.id,
            data_scope=DataScope.DEPT.value, org_ids=[5],
        )
        ids = await resolve_scope_user_ids(owner)
        self.assertIn(u2.id, ids)
        self.assertNotIn(6, ids)
        # 部门外用户不可见
        all_users = await User.all()
        dept6_user = [u for u in all_users if u.dept_id == 6][0]
        self.assertNotIn(dept6_user.id, ids)

    async def test_resolve_scope_user_ids_self(self):
        owner = OwnerContext(owner_type="usr", owner_id=42, data_scope=DataScope.SELF.value)
        self.assertEqual(await resolve_scope_user_ids(owner), [42])


# ============================================================
# 3. L2 声明式归属过滤
# ============================================================
class OwnershipFilterTest(AuthzTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        from base.plugins.agent.models.workflow import Workflow

        self.Workflow = Workflow
        self.wf_usr1 = await Workflow.create(
            name="usr1私有", definition={}, owner_type="usr", owner_id=1
        )
        self.wf_usr2 = await Workflow.create(
            name="usr2私有", definition={}, owner_type="usr", owner_id=2
        )
        self.wf_cus10 = await Workflow.create(
            name="cus10私有", definition={}, owner_type="cus", owner_id=10
        )
        self.wf_public = await Workflow.create(
            name="公开模板", definition={}, owner_type="usr", owner_id=2,
            visibility="public",
        )

    # ---- 双主体基础隔离 ----
    async def test_cus_list_only_own(self):
        owner = OwnerContext(owner_type="cus", owner_id=10)
        rows = await owned_queryset(self.Workflow, owner)
        self.assertEqual({r.id for r in rows}, {self.wf_cus10.id})

    async def test_usr_self_list_only_own(self):
        owner = OwnerContext(
            owner_type="usr", owner_id=1, data_scope=DataScope.SELF.value
        )
        rows = await owned_queryset(self.Workflow, owner)
        self.assertEqual({r.id for r in rows}, {self.wf_usr1.id})

    # ---- usr 四档 data_scope ----
    async def test_usr_all_scope_sees_usr_domain(self):
        owner = OwnerContext(
            owner_type="usr", owner_id=99, data_scope=DataScope.ALL.value,
            is_superuser=True,
        )
        rows = await owned_queryset(self.Workflow, owner)
        # usr 域全部（含他人私有与公开），但不含 cus 域
        self.assertEqual(
            {r.id for r in rows},
            {self.wf_usr1.id, self.wf_usr2.id, self.wf_public.id},
        )

    async def test_usr_dept_scope(self):
        # L1 已解析可见属主集合（部门 [5] 成员为 user 1 和 2）
        owner = OwnerContext(
            owner_type="usr", owner_id=1, data_scope=DataScope.DEPT.value,
            org_ids=[5], visible_user_ids=[1, 2],
        )
        rows = await owned_queryset(self.Workflow, owner)
        self.assertEqual(
            {r.id for r in rows},
            {self.wf_usr1.id, self.wf_usr2.id, self.wf_public.id},
        )

    async def test_usr_dept_tree_scope(self):
        owner = OwnerContext(
            owner_type="usr", owner_id=1,
            data_scope=DataScope.DEPT_TREE.value, org_ids=[5, 6, 7],
            visible_user_ids=[1, 2],
        )
        rows = await owned_queryset(self.Workflow, owner)
        self.assertIn(self.wf_usr2.id, {r.id for r in rows})

    # ---- 公开只读（PRD §7.1 规则 3）----
    async def test_include_public_read(self):
        owner = OwnerContext(owner_type="cus", owner_id=10)
        rows = await owned_queryset(self.Workflow, owner, include_public=True)
        self.assertEqual({r.id for r in rows}, {self.wf_cus10.id, self.wf_public.id})

    async def test_public_not_writable(self):
        owner = OwnerContext(owner_type="cus", owner_id=10)
        with self.assertRaises(OwnedResourceNotFound):
            await get_owned_or_404(self.Workflow, self.wf_public.id, owner, for_write=True)

    # ---- 单条 404（不暴露存在性）----
    async def test_cross_owner_detail_404(self):
        owner = OwnerContext(owner_type="usr", owner_id=1, data_scope=DataScope.SELF.value)
        with self.assertRaises(OwnedResourceNotFound) as ctx:
            await get_owned_or_404(self.Workflow, self.wf_usr2.id, owner)
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_cross_domain_detail_404(self):
        owner = OwnerContext(owner_type="usr", owner_id=1, data_scope=DataScope.SELF.value)
        with self.assertRaises(OwnedResourceNotFound):
            await get_owned_or_404(self.Workflow, self.wf_cus10.id, owner)

    async def test_not_exist_404(self):
        owner = OwnerContext(owner_type="cus", owner_id=10)
        with self.assertRaises(OwnedResourceNotFound):
            await get_owned_or_404(self.Workflow, 999999, owner)

    async def test_own_detail_ok(self):
        owner = OwnerContext(owner_type="usr", owner_id=1, data_scope=DataScope.SELF.value)
        obj = await get_owned_or_404(self.Workflow, self.wf_usr1.id, owner)
        self.assertEqual(obj.id, self.wf_usr1.id)

    # ---- 越权审计触发（资源存在但归属不匹配才计数，不存在的 404 不计）----
    async def test_violation_recorded_only_when_exists(self):
        owner = OwnerContext(
            owner_type="usr", owner_id=1, data_scope=DataScope.SELF.value,
            request_path="/v1/u/workflows/2", request_method="GET",
        )
        with patch(
            "base.common.authz.filter.record_violation", new=AsyncMock()
        ) as mock_record:
            with self.assertRaises(OwnedResourceNotFound):
                await get_owned_or_404(self.Workflow, self.wf_usr2.id, owner)
            mock_record.assert_awaited_once()
            args, kwargs = mock_record.await_args
            self.assertEqual(args[0], "usr:1")
            self.assertIn("workflow", kwargs["resource_hint"])

            mock_record.reset_mock()
            with self.assertRaises(OwnedResourceNotFound):
                await get_owned_or_404(self.Workflow, 999999, owner)
            mock_record.assert_not_awaited()

    # ---- L3 复核钩子 ----
    async def test_l3_assert_owner_access(self):
        owner = OwnerContext(owner_type="usr", owner_id=2, data_scope=DataScope.SELF.value)
        await assert_owner_access(self.wf_usr2, owner, for_write=True)

        other = OwnerContext(owner_type="usr", owner_id=1, data_scope=DataScope.SELF.value)
        with patch("base.common.authz.guard.record_violation", new=AsyncMock()):
            with self.assertRaises(OwnedResourceNotFound):
                await assert_owner_access(self.wf_usr2, other, for_write=True)

    async def test_l3_recheck_owner_bool(self):
        owner = OwnerContext(owner_type="usr", owner_id=2, data_scope=DataScope.SELF.value)
        self.assertTrue(await recheck_owner(self.wf_usr2, owner))
        other = OwnerContext(owner_type="usr", owner_id=1, data_scope=DataScope.SELF.value)
        self.assertFalse(await recheck_owner(self.wf_usr2, other))

    async def test_l3_usr_all_scope_write_allowed(self):
        # data_scope=all 的管理员可写 usr 域资源（RBAC 语义）
        admin = OwnerContext(
            owner_type="usr", owner_id=99, data_scope=DataScope.ALL.value,
            is_superuser=True,
        )
        self.assertTrue(await recheck_owner(self.wf_usr1, admin, for_write=True))

    async def test_unauthenticated_401(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await owned_queryset(self.Workflow, None)
        self.assertEqual(ctx.exception.status_code, 401)


# ============================================================
# 4. F8 越权审计与限流
# ============================================================
class ViolationRateLimitTest(AuthzTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        # 清理进程内计数/封禁残留
        from base.common.authz import audit as audit_mod
        audit_mod._memory_counters.clear()
        audit_mod._memory_blocks.clear()
        self.audit_mod = audit_mod
        # 测试隔离（OB-N4-02）：真实 Redis 启用时清空限流键；先重连消除跨 loop 死连接再清理
        await _reset_redis_client()
        await self._clean_rl_keys()

    async def asyncTearDown(self):
        # 封禁键 TTL 60s，不清理会污染后续用例（如 CrossAccessE2ETest 收到 429 而非 404）
        await _reset_redis_client()
        await self._clean_rl_keys()
        await super().asyncTearDown()

    async def _clean_rl_keys(self):
        from base.common.cache import RedisCache
        if RedisCache.is_enabled():
            cache = await RedisCache.get_instance()
            await cache.delete_pattern("rl:*")

    async def test_violation_warn_audit_and_counter(self):
        with patch.object(self.audit_mod, "_write_audit", new=AsyncMock()) as mock_audit:
            await self.audit_mod.record_violation(
                "usr:1", path="/v1/u/workflows/2", method="GET",
                resource_hint="workflow:2",
            )
            mock_audit.assert_awaited_once()
            kwargs = mock_audit.await_args.kwargs
            self.assertEqual(kwargs["level"], "warning")
            self.assertEqual(kwargs["operation"], "authz.violation")
            self.assertEqual(kwargs["owner_identity"], "usr:1")
            self.assertIn("/v1/u/workflows/2", kwargs["path"])

        self.assertFalse(await self.audit_mod.is_rate_limited("usr:1"))

    async def test_rate_limit_after_threshold(self):
        with patch.object(self.audit_mod, "_write_audit", new=AsyncMock()) as mock_audit:
            for _ in range(RL_THRESHOLD + 1):
                await self.audit_mod.record_violation(
                    "cus:77", path="/v1/u/kb/1", method="GET"
                )
            # 超过阈值 → 封禁
            self.assertTrue(await self.audit_mod.is_rate_limited("cus:77"))
            # 触发一次 alert（critical + authz.rate_limit_alert）
            alert_calls = [
                c for c in mock_audit.await_args_list
                if c.kwargs["operation"] == "authz.rate_limit_alert"
            ]
            self.assertEqual(len(alert_calls), 1)
            self.assertEqual(alert_calls[0].kwargs["level"], "critical")
            # warn 审计每次都记
            warn_calls = [
                c for c in mock_audit.await_args_list
                if c.kwargs["operation"] == "authz.violation"
            ]
            self.assertEqual(len(warn_calls), RL_THRESHOLD + 1)

    async def test_other_identity_not_blocked(self):
        with patch.object(self.audit_mod, "_write_audit", new=AsyncMock()):
            for _ in range(RL_THRESHOLD + 1):
                await self.audit_mod.record_violation("usr:1", path="/x", method="GET")
            self.assertTrue(await self.audit_mod.is_rate_limited("usr:1"))
            self.assertFalse(await self.audit_mod.is_rate_limited("usr:2"))
            self.assertFalse(await self.audit_mod.is_rate_limited("cus:1"))


# ============================================================
# 5. 自测 E2E：cus/usr 双 token 交叉访问（L1 中间件 + L2 过滤）
# ============================================================
class CrossAccessE2ETest(AuthzTestCase):
    """构造 FastAPI 测试应用，验证双 token 交叉访问行为"""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        from base.plugins.agent.models.workflow import Workflow

        self.Workflow = Workflow
        self.wf_usr1 = await Workflow.create(
            name="usr1的", definition={}, owner_type="usr", owner_id=1
        )
        self.wf_cus10 = await Workflow.create(
            name="cus10的", definition={}, owner_type="cus", owner_id=10
        )

        from fastapi import FastAPI, Depends
        from base.common.authz.context import require_owner
        from base.common.authz.filter import get_owned_or_404, owned_queryset
        from base.common.authz.middleware.owner_context import AuthzContextMiddleware

        app = FastAPI()
        app.add_middleware(AuthzContextMiddleware)

        @app.get("/v1/u/workflows")
        async def list_mine(owner=Depends(require_owner)):
            rows = await owned_queryset(Workflow, owner)
            return {"ids": [r.id for r in rows]}

        @app.get("/v1/u/workflows/{wf_id}")
        async def detail(wf_id: int, owner=Depends(require_owner)):
            obj = await get_owned_or_404(Workflow, wf_id, owner)
            return {"id": obj.id, "name": obj.name}

        self.app = app
        self.usr_token = create_access_token({"sub": "1", "typ": "usr", "username": "u1"})
        self.cus_token = create_access_token({"sub": "10", "typ": "cus", "email": "c@t.com"})

    def _client(self):
        import httpx
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test"
        )

    def _headers(self, token: str):
        return {"Authorization": f"Bearer {token}"}

    async def test_own_access_200(self):
        async with self._client() as client:
            resp = await client.get(
                f"/v1/u/workflows/{self.wf_usr1.id}", headers=self._headers(self.usr_token)
            )
            self.assertEqual(resp.status_code, 200)
            resp = await client.get(
                f"/v1/u/workflows/{self.wf_cus10.id}", headers=self._headers(self.cus_token)
            )
            self.assertEqual(resp.status_code, 200)

    async def test_cross_access_404(self):
        async with self._client() as client:
            # usr 访问 cus 资源 → 404
            resp = await client.get(
                f"/v1/u/workflows/{self.wf_cus10.id}", headers=self._headers(self.usr_token)
            )
            self.assertEqual(resp.status_code, 404)
            # cus 访问 usr 资源 → 404
            resp = await client.get(
                f"/v1/u/workflows/{self.wf_usr1.id}", headers=self._headers(self.cus_token)
            )
            self.assertEqual(resp.status_code, 404)

    async def test_list_isolated(self):
        async with self._client() as client:
            resp = await client.get("/v1/u/workflows", headers=self._headers(self.usr_token))
            self.assertEqual(resp.json()["ids"], [self.wf_usr1.id])
            resp = await client.get("/v1/u/workflows", headers=self._headers(self.cus_token))
            self.assertEqual(resp.json()["ids"], [self.wf_cus10.id])

    async def test_no_token_401(self):
        async with self._client() as client:
            resp = await client.get("/v1/u/workflows")
            self.assertEqual(resp.status_code, 401)

    async def test_bad_token_401(self):
        async with self._client() as client:
            resp = await client.get(
                "/v1/u/workflows", headers=self._headers("bad.token.value")
            )
            self.assertEqual(resp.status_code, 401)

    async def test_rate_limited_identity_gets_429(self):
        from base.common.authz import audit as audit_mod
        audit_mod._memory_counters.clear()
        audit_mod._memory_blocks.clear()
        with patch.object(audit_mod, "_write_audit", new=AsyncMock()):
            for _ in range(RL_THRESHOLD + 1):
                await audit_mod.record_violation("usr:1", path="/v1/u/workflows", method="GET")
        async with self._client() as client:
            resp = await client.get("/v1/u/workflows", headers=self._headers(self.usr_token))
            self.assertEqual(resp.status_code, 429)
            self.assertEqual(resp.json()["code"], 42901)
        audit_mod._memory_counters.clear()
        audit_mod._memory_blocks.clear()


# ============================================================
# 6. L1 token 解析（R-04：typ/sub 同源，拒绝旧语义）
# ============================================================
class TokenParseTest(unittest.TestCase):

    def test_parse_cus_token(self):
        token = create_access_token({"sub": "10", "typ": "cus"})
        owner = parse_owner_token(token)
        self.assertIsNotNone(owner)
        self.assertEqual(owner.owner_type, "cus")
        self.assertEqual(owner.owner_id, 10)

    def test_parse_usr_token(self):
        token = create_access_token({"sub": "3", "typ": "usr"})
        owner = parse_owner_token(token)
        self.assertEqual((owner.owner_type, owner.owner_id), ("usr", 3))

    def test_reject_missing_typ(self):
        token = create_access_token({"sub": "3"})
        self.assertIsNone(parse_owner_token(token))

    def test_reject_unknown_typ(self):
        token = create_access_token({"sub": "3", "typ": "sys"})
        self.assertIsNone(parse_owner_token(token))

    def test_reject_non_numeric_sub(self):
        token = create_access_token({"sub": "abc", "typ": "usr"})
        self.assertIsNone(parse_owner_token(token))

    def test_reject_invalid_signature(self):
        self.assertIsNone(parse_owner_token("not-a-token"))


if __name__ == "__main__":
    unittest.main()
