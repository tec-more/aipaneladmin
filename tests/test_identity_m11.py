"""
T3 / M11 身份与组织 单元测试与自测

覆盖（对应任务验证要求）：
1. link 全流程：提示（link-status 创建 prompted + 打码 + 30 天限频）→ 验证失败计数 → 验证成功 → linked
2. dismiss（30 天）与解绑冷却（cooldown 状态、冷却期内禁止重新关联）
3. 异常五态：对方已关联他人(peer_taken)、对方被禁用(peer_disabled)、验证次数耗尽 5 次锁定(verify_locked)、
   重复绑定(already_linked)、解绑需验证(verify_failed on unlink)
4. 管理员手动绑定 + 查询
5. 旧自动绑定下线：login-code 不再自动创建客户/写 system_user_id；登录响应含 link_hint
6. CustomerOrganization CRUD + 成员角色管理；resolve_assignee self 模式（cus/usr）与边界

运行：.venv/Scripts/python.exe -m unittest tests.test_identity_m11 -v
说明：DB 使用 sqlite 内存库；EmailService.verify_code 以 mock 截获；
审计落库通道以 mock 截获验证（不依赖 audit 表）。
"""
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from tortoise import Tortoise

from base.common.setting import get_model_list
from base.common.authz.context import OwnerContext
from base.common.security import create_access_token, get_password_hash
from base.plugins.customer.models.customer import Customer
from base.plugins.customer.models.identity_link import IdentityLink
from base.plugins.customer.models.customer_organization import (
    CustomerOrganization,
    CustomerOrganizationMember,
)
from base.plugins.customer.services.identity_service import (
    IdentityError,
    IdentityService,
    STATUS_COOLDOWN,
    STATUS_DISMISSED,
    STATUS_LINKED,
    STATUS_NONE,
    STATUS_PROMPTED,
    VERIFY_MAX_ATTEMPTS,
    mask_email,
)
from base.plugins.customer.services.organization_service import (
    CustomerOrganizationService,
    OrganizationError,
    resolve_assignee,
)
from base.core.users.models.users import User

# 与生产一致的完整模型注册（同 T2 测试模式）
TEST_MODULES = get_model_list()


async def _init_db():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TEST_MODULES})
    await Tortoise.generate_schemas()


async def _close_db():
    await Tortoise.close_connections()


def _cus_owner(customer_id: int) -> OwnerContext:
    return OwnerContext(owner_type="cus", owner_id=customer_id)


def _usr_owner(user_id: int) -> OwnerContext:
    return OwnerContext(owner_type="usr", owner_id=user_id)


class IdentityTestCase(unittest.IsolatedAsyncioTestCase):
    """共享 sqlite 内存库 + 通用夹具"""

    async def asyncSetUp(self):
        await _init_db()
        # 清理进程内验证计数/锁定残留
        from base.plugins.customer.services import identity_service as svc
        svc._verify_fail_counters.clear()
        svc._verify_locks.clear()

    async def asyncTearDown(self):
        await _close_db()

    async def _make_customer(self, email="a@t.com", username="cus_a", **kw):
        return await Customer.create(
            username=username, email=email, password=get_password_hash("pw123456"),
            is_active=kw.get("is_active", True),
        )

    async def _make_user(self, email="a@t.com", username="usr_a", **kw):
        return await User.create(
            username=username, email=email, password=get_password_hash("pw123456"),
            is_active=kw.get("is_active", True),
        )


# ============================================================
# 1. link-status 检测与提示限频
# ============================================================
class LinkStatusTest(IdentityTestCase):

    async def test_status_none_without_counterpart(self):
        c = await self._make_customer(email="solo@t.com")
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            data = await IdentityService.get_link_status(_cus_owner(c.id))
        self.assertEqual(data["status"], STATUS_NONE)
        self.assertFalse(data["should_prompt"])
        self.assertIsNone(data["peer"])

    async def test_first_prompt_creates_prompted_with_masked_peer(self):
        c = await self._make_customer()
        u = await self._make_user()
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()) as mock_audit:
            data = await IdentityService.get_link_status(_cus_owner(c.id))
        self.assertEqual(data["status"], STATUS_PROMPTED)
        self.assertTrue(data["should_prompt"])
        # L3：打码信息，不含资产数据
        self.assertEqual(data["peer"]["owner_type"], "usr")
        self.assertEqual(data["peer"]["username"], "usr_a")
        self.assertEqual(data["peer"]["masked_email"], "a***@t.com")
        self.assertNotIn("email", {k: v for k, v in data["peer"].items() if k != "masked_email"})
        # L10：提示审计
        mock_audit.assert_awaited_once()
        self.assertEqual(mock_audit.await_args.kwargs["operation"], "identity.prompt_shown")
        # 已生成 prompted 记录
        link = await IdentityLink.get(customer_id=c.id, user_id=u.id)
        self.assertEqual(link.status, STATUS_PROMPTED)
        self.assertEqual(link.audit[-1]["action"], "prompt_shown")

    async def test_prompt_frequency_once_per_30_days(self):
        c = await self._make_customer()
        await self._make_user()
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            first = await IdentityService.get_link_status(_cus_owner(c.id))
            second = await IdentityService.get_link_status(_cus_owner(c.id))
        self.assertTrue(first["should_prompt"])
        # L7：30 天内不重复提示
        self.assertFalse(second["should_prompt"])
        link = await IdentityLink.get(customer_id=c.id)
        prompt_events = [e for e in link.audit if e["action"] == "prompt_shown"]
        self.assertEqual(len(prompt_events), 1)

    async def test_mask_email(self):
        self.assertEqual(mask_email("alice@example.com"), "a***@example.com")
        self.assertEqual(mask_email("b@x.cn"), "b***@x.cn")
        self.assertIsNone(mask_email("not-an-email"))
        self.assertIsNone(mask_email(None))


# ============================================================
# 2. link 全流程
# ============================================================
class LinkFlowTest(IdentityTestCase):

    async def test_full_flow_prompt_verify_link(self):
        c = await self._make_customer()
        u = await self._make_user()
        owner = _cus_owner(c.id)

        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            # 1. 提示
            status = await IdentityService.get_link_status(owner)
            self.assertEqual(status["status"], STATUS_PROMPTED)

            # 2. 验证失败（错误密码）
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.link(owner, "password", "wrong-pw")
            self.assertEqual(ctx.exception.code, "verify_failed")
            self.assertEqual(ctx.exception.data["attempts_left"], VERIFY_MAX_ATTEMPTS - 1)

            # 3. 验证成功（对方 usr 密码）
            result = await IdentityService.link(owner, "password", "pw123456")

        self.assertEqual(result["status"], STATUS_LINKED)
        self.assertIn("linked_at", result)
        # L8：明示不共享资产
        self.assertIn("不共享", result["notice"])

        link = await IdentityLink.get(customer_id=c.id, user_id=u.id)
        self.assertEqual(link.status, STATUS_LINKED)
        self.assertEqual(link.verified_via, "password")
        self.assertIsNotNone(link.verified_at)
        actions = [e["action"] for e in link.audit]
        self.assertIn("verify_failed", actions)
        self.assertEqual(actions[-1], "linked")

        # 关联后 link-status 返回 linked
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            status = await IdentityService.get_link_status(owner)
        self.assertEqual(status["status"], STATUS_LINKED)

    async def test_link_via_email_code(self):
        c = await self._make_customer()
        await self._make_user()
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()), patch(
            "base.core.users.services.email_service.EmailService.verify_code",
            new=MagicMock(return_value=True),
        ):
            result = await IdentityService.link(_cus_owner(c.id), "email_code", "123456")
        self.assertEqual(result["status"], STATUS_LINKED)
        link = await IdentityLink.get(customer_id=c.id)
        self.assertEqual(link.verified_via, "email_code")

    async def test_link_usr_to_cus_by_email_code(self):
        """usr → cus 方向：邮箱验证码"""
        c = await self._make_customer()
        u = await self._make_user()
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()), patch(
            "base.core.users.services.email_service.EmailService.verify_code",
            new=MagicMock(return_value=True),
        ):
            result = await IdentityService.link(_usr_owner(u.id), "email_code", "123456")
        self.assertEqual(result["status"], STATUS_LINKED)
        link = await IdentityLink.get(user_id=u.id)
        self.assertEqual(link.customer_id, c.id)
        self.assertEqual(link.status, STATUS_LINKED)

    async def test_verify_attempts_exhausted_locks(self):
        c = await self._make_customer()
        await self._make_user()
        owner = _cus_owner(c.id)
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            for _ in range(VERIFY_MAX_ATTEMPTS - 1):
                with self.assertRaises(IdentityError) as ctx:
                    await IdentityService.link(owner, "password", "bad")
                self.assertEqual(ctx.exception.code, "verify_failed")
            # 第 5 次失败 → 锁定
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.link(owner, "password", "bad")
            self.assertEqual(ctx.exception.code, "verify_locked")
            # 锁定期内即使密码正确也拒绝
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.link(owner, "password", "pw123456")
            self.assertEqual(ctx.exception.code, "verify_locked")


# ============================================================
# 3. dismiss 与解绑冷却
# ============================================================
class DismissUnlinkTest(IdentityTestCase):

    async def test_dismiss_30_days(self):
        c = await self._make_customer()
        u = await self._make_user()
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            result = await IdentityService.dismiss(_cus_owner(c.id))
        self.assertEqual(result["status"], STATUS_DISMISSED)
        link = await IdentityLink.get(customer_id=c.id, user_id=u.id)
        self.assertEqual(link.status, STATUS_DISMISSED)
        self.assertGreater(link.dismissed_until, datetime.now(timezone.utc) + timedelta(days=29))

        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            status = await IdentityService.get_link_status(_cus_owner(c.id))
        self.assertEqual(status["status"], STATUS_DISMISSED)
        self.assertFalse(status["should_prompt"])

    async def test_unlink_requires_verify_and_cooldown(self):
        c = await self._make_customer()
        u = await self._make_user()
        owner = _cus_owner(c.id)
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            await IdentityService.link(owner, "password", "pw123456")

            # 解绑验证失败
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.unlink(owner, "password", "bad")
            self.assertEqual(ctx.exception.code, "verify_failed")
            link = await IdentityLink.get(customer_id=c.id)
            self.assertEqual(link.status, STATUS_LINKED)  # 仍为已关联

            # 验证成功 → 解绑，进入冷却
            result = await IdentityService.unlink(owner, "password", "pw123456")
        self.assertEqual(result["status"], STATUS_COOLDOWN)

        link = await IdentityLink.get(customer_id=c.id, user_id=u.id)
        self.assertEqual(link.status, STATUS_DISMISSED)
        self.assertGreater(link.dismissed_until, datetime.now(timezone.utc) + timedelta(days=29))
        self.assertEqual(link.audit[-1]["action"], "unlinked")

        # 冷却期 link-status → cooldown，不提示
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            status = await IdentityService.get_link_status(owner)
            self.assertEqual(status["status"], STATUS_COOLDOWN)
            self.assertFalse(status["should_prompt"])
            # 冷却期内禁止重新关联
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.link(owner, "password", "pw123456")
            self.assertEqual(ctx.exception.code, "cooldown")

    async def test_unlink_not_linked(self):
        c = await self._make_customer()
        await self._make_user()
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.unlink(_cus_owner(c.id), "password", "pw123456")
        self.assertEqual(ctx.exception.code, "not_linked")


# ============================================================
# 4. 异常五态
# ============================================================
class AbnormalStateTest(IdentityTestCase):

    async def test_peer_taken(self):
        """对方主体已关联他人 → peer_taken（User.email 唯一，经 admin_bind 跨邮箱构造）"""
        u2 = await self._make_user(email="taken@t.com", username="u_taken")
        c_other = await self._make_customer(email="other@t.com", username="c_other")
        # c2 与 u2 同邮箱 → c2 视角对方 u2 已被其他客户关联
        c2 = await self._make_customer(email="taken@t.com", username="c2")
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            await IdentityService.admin_bind(999, c_other.id, u2.id)
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.link(_cus_owner(c2.id), "password", "pw123456")
            self.assertEqual(ctx.exception.code, "peer_taken")
            # link-status 同样体现
            status = await IdentityService.get_link_status(_cus_owner(c2.id))
        self.assertEqual(status["status"], STATUS_NONE)
        self.assertEqual(status["reason"], "peer_taken")

    async def test_peer_disabled(self):
        c = await self._make_customer()
        await self._make_user(is_active=False)
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.link(_cus_owner(c.id), "password", "pw123456")
        self.assertEqual(ctx.exception.code, "peer_disabled")

    async def test_already_linked(self):
        c = await self._make_customer()
        await self._make_user()
        owner = _cus_owner(c.id)
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            await IdentityService.link(owner, "password", "pw123456")
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.link(owner, "password", "pw123456")
        self.assertEqual(ctx.exception.code, "already_linked")
        self.assertIn("linked_at", ctx.exception.data)

    async def test_peer_not_found(self):
        c = await self._make_customer(email="lonely@t.com")
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.link(_cus_owner(c.id), "password", "pw123456")
        self.assertEqual(ctx.exception.code, "peer_not_found")

    async def test_d1_uniqueness_both_columns(self):
        """D1：customer_id/user_id 双列各自唯一（模型声明 + 服务层防重）

        说明：生产 DDL（migrations/core_create_table_identity_link_*.sql）含
        uq_identity_link_customer / uq_identity_link_user 唯一索引；
        sqlite 内存库经 Tortoise generate_schemas 不生成 FK 唯一索引，
        故此处断言模型声明与服务层双向防重。
        """
        self.assertTrue(IdentityLink._meta.fields_map["customer"].unique)
        self.assertTrue(IdentityLink._meta.fields_map["user"].unique)

        c = await self._make_customer()
        u = await self._make_user()
        c2 = await self._make_customer(email="c2@t.com", username="c2")
        u2 = await self._make_user(email="u2@t.com", username="u2")
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            await IdentityService.admin_bind(999, c.id, u.id)
            # user 侧防重：u 已被 c 关联
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.admin_bind(999, c2.id, u.id)
            self.assertEqual(ctx.exception.code, "peer_taken")
            # customer 侧防重：c 已被 u 关联
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.admin_bind(999, c.id, u2.id)
            self.assertEqual(ctx.exception.code, "peer_taken")


# ============================================================
# 5. 管理员手动绑定与查询
# ============================================================
class AdminBindTest(IdentityTestCase):

    async def test_admin_bind_and_list(self):
        c = await self._make_customer()
        u = await self._make_user()
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()) as mock_audit:
            result = await IdentityService.admin_bind(999, c.id, u.id)
        self.assertEqual(result["status"], STATUS_LINKED)
        self.assertEqual(result["customer_id"], c.id)
        self.assertEqual(result["user_id"], u.id)
        mock_audit.assert_awaited_once()
        self.assertEqual(mock_audit.await_args.kwargs["operation"], "identity.admin_bind")

        link = await IdentityLink.get(customer_id=c.id)
        self.assertEqual(link.verified_via, "admin")

        data = await IdentityService.list_links(customer_id=c.id)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["status"], STATUS_LINKED)

    async def test_admin_bind_taken(self):
        c = await self._make_customer()
        u = await self._make_user()
        c2 = await self._make_customer(email="c2@t.com", username="c2")
        with patch.object(IdentityService, "_write_audit_log", new=AsyncMock()):
            await IdentityService.admin_bind(999, c.id, u.id)
            with self.assertRaises(IdentityError) as ctx:
                await IdentityService.admin_bind(999, c2.id, u.id)
        self.assertEqual(ctx.exception.code, "peer_taken")


# ============================================================
# 6. 旧自动绑定下线（RK-14）：登录路径不再写 system_user_id
# ============================================================
class LoginAutoBindRemovedTest(IdentityTestCase):

    async def test_login_code_no_auto_create_customer(self):
        """同邮箱仅存在 User 时：不再自动创建客户主体，返回未注册"""
        from base.plugins.customer.api.v1.auth import (
            customer_login_with_code, VerifyCodeSchema,
        )
        await self._make_user(email="only-user@t.com")
        with patch(
            "base.core.users.services.email_service.EmailService.verify_code",
            new=MagicMock(return_value=True),
        ):
            resp = await customer_login_with_code(
                VerifyCodeSchema(email="only-user@t.com", code="123456")
            )
        body = json.loads(resp.body)
        self.assertFalse(body["success"])
        self.assertIn("未注册", body["msg"])
        # 未创建任何 Customer，未产生任何 IdentityLink
        self.assertEqual(await Customer.all().count(), 0)
        self.assertEqual(await IdentityLink.all().count(), 0)

    async def test_login_code_existing_customer_no_system_user_id_write(self):
        """客户存在且同邮箱有 User：登录成功、link_hint=True，但绝不写 system_user_id"""
        from base.plugins.customer.api.v1.auth import (
            customer_login_with_code, VerifyCodeSchema,
        )
        c = await self._make_customer()
        await self._make_user()
        with patch(
            "base.core.users.services.email_service.EmailService.verify_code",
            new=MagicMock(return_value=True),
        ), patch.object(Customer, "to_dict", new=AsyncMock(return_value={"id": c.id})):
            resp = await customer_login_with_code(
                VerifyCodeSchema(email="a@t.com", code="123456")
            )
        body = json.loads(resp.body)
        self.assertTrue(body["success"])
        self.assertTrue(body["data"]["link_hint"])
        # token 三段式保持不变（R-04）
        from base.common.security import decode_access_token
        payload = decode_access_token(body["data"]["access_token"])
        self.assertEqual(payload["typ"], "cus")
        self.assertEqual(payload["sub"], str(c.id))
        # system_user_id 保持只读废弃（None）
        await c.refresh_from_db()
        self.assertIsNone(c.system_user_id)
        # 未自动建立映射
        self.assertEqual(await IdentityLink.all().count(), 0)

    async def test_password_login_link_hint_false_when_no_peer(self):
        from base.plugins.customer.api.v1.auth import (
            customer_login_with_password, CustomerPasswordLoginSchema,
        )
        c = await self._make_customer(email="nopeer@t.com")
        with patch.object(Customer, "to_dict", new=AsyncMock(return_value={"id": c.id})):
            resp = await customer_login_with_password(
                CustomerPasswordLoginSchema(email="nopeer@t.com", password="pw123456")
            )
        body = json.loads(resp.body)
        self.assertTrue(body["success"])
        self.assertFalse(body["data"]["link_hint"])

    async def test_password_login_link_hint_false_when_linked(self):
        from base.plugins.customer.api.v1.auth import (
            customer_login_with_password, CustomerPasswordLoginSchema,
        )
        c = await self._make_customer()
        u = await self._make_user()
        await IdentityLink.create(
            customer_id=c.id, user_id=u.id, status=STATUS_LINKED, verified_via="admin"
        )
        with patch.object(Customer, "to_dict", new=AsyncMock(return_value={"id": c.id})):
            resp = await customer_login_with_password(
                CustomerPasswordLoginSchema(email="a@t.com", password="pw123456")
            )
        body = json.loads(resp.body)
        self.assertTrue(body["success"])
        self.assertFalse(body["data"]["link_hint"])

    async def test_membership_get_or_create_no_system_user_id(self):
        """membership.get_or_create_customer 不再读写 system_user_id"""
        from base.plugins.customer.api.v1.membership import get_or_create_customer
        u = await self._make_user(email="member@t.com", username="member_u")
        with patch(
            "base.plugins.customer.services.membership_service.MembershipService.initialize_regular_member",
            new=AsyncMock(),
        ):
            customer = await get_or_create_customer(u)
        self.assertIsNone(customer.system_user_id)
        self.assertEqual(customer.email, "member@t.com")


# ============================================================
# 7. 组织服务与 resolve_assignee
# ============================================================
class OrganizationServiceTest(IdentityTestCase):

    async def _make_org(self):
        owner = await self._make_customer(email="owner@t.com", username="owner_c")
        org = await CustomerOrganizationService.create_organization(owner.id, "测试组织")
        return owner, org

    async def test_create_org_owner_membership(self):
        owner, org = await self._make_org()
        membership = await CustomerOrganizationMember.get(org_id=org.id, customer_id=owner.id)
        self.assertEqual(membership.role, "owner")
        self.assertEqual(org.owner_customer_id, owner.id)

        orgs = await CustomerOrganizationService.list_my_organizations(owner.id)
        self.assertEqual(len(orgs), 1)
        self.assertEqual(orgs[0]["my_role"], "owner")

    async def test_member_management_roles(self):
        owner, org = await self._make_org()
        member = await self._make_customer(email="m@t.com", username="m_c")
        admin = await self._make_customer(email="adm@t.com", username="adm_c")

        # owner 添加 member / admin
        await CustomerOrganizationService.add_member(org.id, owner.id, member.id)
        await CustomerOrganizationService.add_member(org.id, owner.id, admin.id, role="admin")

        # admin 可添加 member
        m2 = await self._make_customer(email="m2@t.com", username="m2_c")
        await CustomerOrganizationService.add_member(org.id, admin.id, m2.id)

        members = await CustomerOrganizationService.list_members(org.id, owner.id)
        self.assertEqual(len(members), 4)

        # member 无权添加
        with self.assertRaises(OrganizationError) as ctx:
            await CustomerOrganizationService.add_member(org.id, member.id, m2.id)
        self.assertEqual(ctx.exception.code, "forbidden")

        # 重复添加
        with self.assertRaises(OrganizationError) as ctx:
            await CustomerOrganizationService.add_member(org.id, owner.id, member.id)
        self.assertEqual(ctx.exception.code, "already_member")

        # 角色变更：仅 owner
        with self.assertRaises(OrganizationError):
            await CustomerOrganizationService.update_member_role(
                org.id, admin.id, member.id, "admin"
            )
        updated = await CustomerOrganizationService.update_member_role(
            org.id, owner.id, member.id, "admin"
        )
        self.assertEqual(updated.role, "admin")

        # 不可移除 owner
        with self.assertRaises(OrganizationError) as ctx:
            await CustomerOrganizationService.remove_member(org.id, owner.id, owner.id)
        self.assertEqual(ctx.exception.code, "cannot_remove_owner")

        # admin 移除 member
        await CustomerOrganizationService.remove_member(org.id, admin.id, m2.id)
        remaining = await CustomerOrganizationService.list_members(org.id, owner.id)
        self.assertEqual(len(remaining), 3)

    async def test_org_update_permission(self):
        owner, org = await self._make_org()
        outsider = await self._make_customer(email="out@t.com", username="out_c")
        with self.assertRaises(OrganizationError):
            await CustomerOrganizationService.update_organization(
                org.id, outsider.id, name="越权改名"
            )
        updated = await CustomerOrganizationService.update_organization(
            org.id, owner.id, name="新名称"
        )
        self.assertEqual(updated.name, "新名称")


class ResolveAssigneeTest(IdentityTestCase):

    async def test_self_mode_cus(self):
        principal = await resolve_assignee("self", _cus_owner(42))
        self.assertEqual(principal["principal_type"], "cus")
        self.assertEqual(principal["principal_id"], 42)

    async def test_self_mode_usr(self):
        principal = await resolve_assignee("self", _usr_owner(7))
        self.assertEqual(principal["principal_type"], "usr")
        self.assertEqual(principal["principal_id"], 7)

    async def test_cus_only_self_p0(self):
        """P0 客户域仅支持 self"""
        with self.assertRaises(OrganizationError) as ctx:
            await resolve_assignee("specific_user", _cus_owner(42), ["43"])
        self.assertEqual(ctx.exception.code, "unsupported_mode")

    async def test_usr_specific_user_in_scope(self):
        owner = OwnerContext(
            owner_type="usr", owner_id=1, data_scope="dept", visible_user_ids=[1, 2, 3]
        )
        principal = await resolve_assignee("specific_user", owner, ["2"])
        self.assertEqual(principal["principal_id"], 2)

    async def test_usr_specific_user_out_of_scope(self):
        owner = OwnerContext(
            owner_type="usr", owner_id=1, data_scope="dept", visible_user_ids=[1, 2, 3]
        )
        with self.assertRaises(OrganizationError) as ctx:
            await resolve_assignee("specific_user", owner, ["99"])
        self.assertEqual(ctx.exception.code, "assignee_out_of_scope")

    async def test_org_role_reserved(self):
        with self.assertRaises(NotImplementedError):
            await resolve_assignee("org_role", _usr_owner(1))


if __name__ == "__main__":
    unittest.main()
