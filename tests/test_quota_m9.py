"""
T4 / M9 配额计量 单元测试与自测

覆盖（对应任务验证要求）：
1. 预占/结算/释放（Redis 路径，FakeRedis 模拟）
2. 超限 42901 语义（item/剩余/预计 + 补偿回退不超发）
3. 并发计数上下限（主体/全局）
4. 降级路径（Redis 不可用 → DB 预扣 + 结算修正 + 释放回退）
5. 周期滚动（自然月）与对账落盘（Redis → PG used）
6. 结算幂等去重（execution_id,node_id,resource_type 重复不双计）
7. 套餐映射（会员等级 level_type / 角色 code，priority 优先）
8. 看板输出形态（plan/period/items[limit/used/held]）
9. 悬挂预占清理、字符启发式预估、daily 项粒度

运行：.venv/Scripts/python.exe -m unittest tests.test_quota_m9 -v
说明：DB 使用 sqlite 内存库；Redis 以进程内 FakeRedis 模拟（接口对齐 redis.asyncio 子集）。
"""
import asyncio
import re
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from tortoise import Tortoise

from base.common.setting import get_model_list
from base.common.quota.errors import QuotaError, QUOTA_ERROR_CODE
from base.common.quota.metrics import quota_reject_total  # noqa: F401 触发指标注册
from base.common.quota.models.binding import QuotaPlanBinding
from base.common.quota.models.quota import QuotaAccount, QuotaPlan, UsageRecord
from base.common.quota.services.estimator import estimate_messages_tokens, estimate_tokens
from base.common.quota.services.plan_service import PlanService
from base.common.quota.services.quota_service import (
    HOLD_INDEX_KEY,
    QuotaService,
    current_period,
)

TEST_MODULES = get_model_list()


# ============================================================
# FakeRedis：redis.asyncio 客户端子集（含 TTL）
# ============================================================
class FakeRedis:
    def __init__(self):
        self._data = {}    # string/hash key -> value(str|dict)
        self._zsets = {}   # key -> {member: score}
        self._sets = {}    # key -> set
        self._exp = {}     # key -> epoch 秒

    def _purge(self, key):
        exp = self._exp.get(key)
        if exp is not None and exp <= time.time():
            self._data.pop(key, None)
            self._zsets.pop(key, None)
            self._sets.pop(key, None)
            self._exp.pop(key, None)

    async def get(self, key):
        self._purge(key)
        v = self._data.get(key)
        return v if isinstance(v, str) or v is None else None

    async def set(self, key, value, ex=None):
        self._data[key] = str(value)
        if ex:
            self._exp[key] = time.time() + ex
        return True

    async def exists(self, key):
        self._purge(key)
        return 1 if key in self._data or key in self._zsets or key in self._sets else 0

    async def expire(self, key, seconds):
        self._exp[key] = time.time() + seconds
        return True

    async def incrbyfloat(self, key, amount):
        self._purge(key)
        cur = float(self._data.get(key, 0))
        new = cur + float(amount)
        self._data[key] = repr(new)
        return new

    async def incr(self, key):
        self._purge(key)
        cur = int(float(self._data.get(key, 0)))
        self._data[key] = str(cur + 1)
        return cur + 1

    async def decr(self, key):
        self._purge(key)
        cur = int(float(self._data.get(key, 0)))
        self._data[key] = str(cur - 1)
        return cur - 1

    async def hset(self, key, mapping=None, **_):
        h = self._data.get(key)
        if not isinstance(h, dict):
            h = {}
        h.update({k: str(v) for k, v in (mapping or {}).items()})
        self._data[key] = h
        return len(mapping or {})

    async def hgetall(self, key):
        self._purge(key)
        h = self._data.get(key)
        return dict(h) if isinstance(h, dict) else {}

    async def delete(self, *keys):
        n = 0
        for key in keys:
            for store in (self._data, self._zsets, self._sets):
                if key in store:
                    store.pop(key)
                    n += 1
            self._exp.pop(key, None)
        return n

    async def zadd(self, key, mapping):
        z = self._zsets.setdefault(key, {})
        z.update({m: float(s) for m, s in mapping.items()})
        return len(mapping)

    async def zrangebyscore(self, key, min_score, max_score):
        self._purge(key)
        lo = float("-inf") if min_score == "-inf" else float(min_score)
        hi = float("inf") if max_score == "+inf" else float(max_score)
        z = self._zsets.get(key, {})
        return [m for m, s in sorted(z.items(), key=lambda kv: kv[1]) if lo <= s <= hi]

    async def zrem(self, key, member):
        z = self._zsets.get(key, {})
        return 1 if z.pop(member, None) is not None else 0

    async def sadd(self, key, *members):
        s = self._sets.setdefault(key, set())
        before = len(s)
        s.update(members)
        return len(s) - before

    async def smembers(self, key):
        self._purge(key)
        return set(self._sets.get(key, set()))

    async def scan_iter(self, match=None):
        pattern = "^" + re.escape(match or "*").replace(r"\*", ".*") + "$"
        regex = re.compile(pattern)
        for key in list(self._data.keys()):
            self._purge(key)
            if key in self._data and regex.match(key):
                yield key


# ============================================================
# 测试基类与夹具
# ============================================================
class QuotaTestCase(unittest.IsolatedAsyncioTestCase):
    use_fake_redis = True

    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TEST_MODULES})
        await Tortoise.generate_schemas()
        QuotaService._mem_holds.clear()
        QuotaService._mem_conc.clear()
        self.fake = FakeRedis() if self.use_fake_redis else None
        self._redis_patcher = patch.object(
            QuotaService, "_redis", AsyncMock(return_value=self.fake)
        )
        self._redis_patcher.start()

    async def asyncTearDown(self):
        self._redis_patcher.stop()
        QuotaService._mem_holds.clear()
        QuotaService._mem_conc.clear()
        await Tortoise.close_connections()

    # ---- 夹具：cus 主体（客户 + vip 会员等级 + 绑定套餐） ----
    async def make_cus_owner(self, token_limit=1000, concurrency=2, daily_runs=5):
        from base.plugins.customer.models.customer import Customer
        from base.plugins.customer.models.customer_membership import CustomerMembership
        from base.plugins.customer.models.membership import LevelType, MembershipLevel

        plan = await QuotaPlan.create(
            code=f"vip_plan_{token_limit}", name="VIP套餐", scope="cus",
            quota_items={"token": token_limit, "concurrency": concurrency,
                         "daily_runs": daily_runs, "kb_search": 50},
        )
        await QuotaPlanBinding.create(
            bind_type="membership_level", bind_key="vip", plan_id=plan.id, priority=1
        )
        suffix = str(int(time.time() * 1000) % 10_000_000)
        level = await MembershipLevel.create(
            level_type=LevelType.VIP, name=f"VIP{suffix}", price=0
        )
        customer = await Customer.create(
            nickname=f"测试客户{suffix}", username=f"c{suffix}", email=f"c{suffix}@t.com"
        )
        await CustomerMembership.create(customer=customer, membership_level=level)
        return ("cus", customer.id), plan

    # ---- 夹具：usr 主体（用户 + 角色 + 绑定套餐） ----
    async def make_usr_owner(self, token_limit=500):
        from base.core.users.models.rbac import Role
        from base.core.users.models.users import User

        plan = await QuotaPlan.create(
            code=f"role_plan_{token_limit}", name="角色套餐", scope="usr",
            quota_items={"token": token_limit, "concurrency": 3},
        )
        await QuotaPlanBinding.create(
            bind_type="role", bind_key="operator", plan_id=plan.id, priority=1
        )
        suffix = str(int(time.time() * 1000) % 10_000_000)
        role = await Role.create(name=f"运营{suffix}", code="operator")
        user = await User.create(username=f"u{suffix}", email=f"u{suffix}@t.com")
        await user.roles.add(role)
        return ("usr", user.id), plan

    def held_of(self, ot, oid, item, period=None):
        period = period or current_period()
        key = QuotaService._held_key(ot, oid, item, period)
        v = self.fake._data.get(key)
        return float(v) if v else 0.0

    def used_of(self, ot, oid, item, period=None):
        period = period or current_period()
        key = QuotaService._used_key(ot, oid, item, period)
        v = self.fake._data.get(key)
        return float(v) if v else 0.0


# ============================================================
# 1. 预占 / 结算 / 释放（Redis 路径）
# ============================================================
class EstimateSettleReleaseTest(QuotaTestCase):

    async def test_estimate_success(self):
        owner, plan = await self.make_cus_owner()
        hold_id = await QuotaService.quota_estimate(owner, {"token": 400})
        self.assertTrue(hold_id)
        self.assertEqual(self.held_of(*owner, "token"), 400)
        # 未绑定套餐项不在 limits 的请求被忽略
        hold2 = await QuotaService.quota_estimate(owner, {"unknown_item": 10})
        self.assertEqual(hold2, "")

    async def test_estimate_insufficient_42901(self):
        owner, plan = await self.make_cus_owner(token_limit=1000)
        await QuotaService.quota_estimate(owner, {"token": 800})
        with self.assertRaises(QuotaError) as ctx:
            await QuotaService.quota_estimate(owner, {"token": 500})
        err = ctx.exception
        self.assertEqual(err.code, QUOTA_ERROR_CODE)
        self.assertEqual(err.item, "token")
        self.assertEqual(err.estimated, 500)
        self.assertEqual(err.remaining, 200)
        self.assertIn("额度不足", err.message)
        # 补偿回退：held 仍为 800，不超发
        self.assertEqual(self.held_of(*owner, "token"), 800)

    async def test_settle_converts_hold_and_writes_record(self):
        owner, plan = await self.make_cus_owner()
        hold_id = await QuotaService.quota_estimate(owner, {"token": 400})
        result = await QuotaService.quota_settle(hold_id, [{
            "execution_id": 9001, "node_id": "n_llm", "seq": 3,
            "resource_type": "llm_token", "amount": 300,
            "tokens_in": 200, "tokens_out": 100, "model": "m_gpt4o",
        }])
        self.assertEqual(result["settled"], 1)
        self.assertEqual(self.used_of(*owner, "token"), 300)
        self.assertEqual(self.held_of(*owner, "token"), 100)  # 差额留在预占待释放
        record = await UsageRecord.get_or_none(execution_id=9001, node_id="n_llm")
        self.assertIsNotNone(record)
        self.assertEqual(record.tokens_in, 200)
        self.assertEqual(record.owner_type, "cus")

    async def test_settle_idempotent(self):
        owner, plan = await self.make_cus_owner()
        hold_id = await QuotaService.quota_estimate(owner, {"token": 400})
        usage = [{
            "execution_id": 9002, "node_id": "n_llm", "seq": 3,
            "resource_type": "llm_token", "amount": 300,
            "tokens_in": 200, "tokens_out": 100,
        }]
        r1 = await QuotaService.quota_settle(hold_id, usage)
        r2 = await QuotaService.quota_settle(hold_id, usage)
        self.assertEqual(r1["settled"], 1)
        self.assertEqual(r2["settled"], 0)
        self.assertEqual(r2["skipped"], 1)
        self.assertEqual(self.used_of(*owner, "token"), 300)  # 不双计
        count = await UsageRecord.filter(execution_id=9002).count()
        self.assertEqual(count, 1)

    async def test_release_returns_held(self):
        owner, plan = await self.make_cus_owner()
        hold_id = await QuotaService.quota_estimate(owner, {"token": 400})
        ok = await QuotaService.quota_release(hold_id)
        self.assertTrue(ok)
        self.assertEqual(self.held_of(*owner, "token"), 0)
        # 幂等：重复释放无操作
        self.assertFalse(await QuotaService.quota_release(hold_id))

    async def test_daily_item_period(self):
        owner, plan = await self.make_cus_owner(daily_runs=2)
        await QuotaService.quota_estimate(owner, {"daily_runs": 1})
        await QuotaService.quota_estimate(owner, {"daily_runs": 1})
        with self.assertRaises(QuotaError) as ctx:
            await QuotaService.quota_estimate(owner, {"daily_runs": 1})
        self.assertEqual(ctx.exception.item, "daily_runs")

    async def test_no_plan_no_metering(self):
        # 无绑定主体：不计量不拦截
        hold = await QuotaService.quota_estimate(("cus", 999999), {"token": 10})
        self.assertEqual(hold, "")


# ============================================================
# 2. 并发计数
# ============================================================
class ConcurrencyTest(QuotaTestCase):

    async def test_owner_and_global_limit(self):
        owner, plan = await self.make_cus_owner(concurrency=2)
        await QuotaService.acquire_concurrency(owner, limit=2)
        await QuotaService.acquire_concurrency(owner, limit=2)
        with self.assertRaises(QuotaError) as ctx:
            await QuotaService.acquire_concurrency(owner, limit=2)
        self.assertEqual(ctx.exception.item, "concurrency")
        await QuotaService.release_concurrency(owner)
        self.assertTrue(await QuotaService.acquire_concurrency(owner, limit=2))
        self.assertEqual(await QuotaService.current_concurrency(*owner), 2)

    async def test_global_limit(self):
        o1, _ = await self.make_cus_owner()
        await QuotaService.acquire_concurrency(o1, limit=10, global_limit=1)
        with self.assertRaises(QuotaError):
            await QuotaService.acquire_concurrency(o1, limit=10, global_limit=1)


# ============================================================
# 3. 降级路径（Redis 不可用）
# ============================================================
class DegradedTest(QuotaTestCase):
    use_fake_redis = False

    async def test_estimate_db_precharge_and_settle_release(self):
        owner, plan = await self.make_cus_owner(token_limit=1000)
        hold_id = await QuotaService.quota_estimate(owner, {"token": 400})
        account = await QuotaAccount.get(owner_type="cus", owner_id=owner[1])
        self.assertEqual(float(account.used.get("token", 0)), 400)  # DB 预扣

        # 结算真实 300：预扣 400 中转 300，剩 100 仍在预占
        result = await QuotaService.quota_settle(hold_id, [{
            "execution_id": 9003, "node_id": "n_llm", "seq": 1,
            "resource_type": "llm_token", "amount": 300,
        }])
        self.assertEqual(result["settled"], 1)
        await account.refresh_from_db()
        self.assertEqual(float(account.used.get("token", 0)), 400)

        # 释放剩余预占 100 → 300
        self.assertTrue(await QuotaService.quota_release(hold_id))
        await account.refresh_from_db()
        self.assertEqual(float(account.used.get("token", 0)), 300)

    async def test_estimate_db_insufficient(self):
        owner, plan = await self.make_cus_owner(token_limit=100)
        with self.assertRaises(QuotaError) as ctx:
            await QuotaService.quota_estimate(owner, {"token": 200})
        self.assertEqual(ctx.exception.code, QUOTA_ERROR_CODE)
        self.assertEqual(ctx.exception.remaining, 100)  # limit 100，尚未使用

    async def test_concurrency_degraded(self):
        owner, plan = await self.make_cus_owner(concurrency=1)
        await QuotaService.acquire_concurrency(owner, limit=1)
        with self.assertRaises(QuotaError):
            await QuotaService.acquire_concurrency(owner, limit=1)
        await QuotaService.release_concurrency(owner)
        self.assertTrue(await QuotaService.acquire_concurrency(owner, limit=1))


# ============================================================
# 4. 滚动 / 对账 / 悬挂清理 / 看板
# ============================================================
class MaintenanceTest(QuotaTestCase):

    async def test_period_rollover(self):
        owner, plan = await self.make_cus_owner()
        start, _end = __import__("base.common.quota.services.quota_service", fromlist=["month_bounds"]).month_bounds()
        account = await QuotaService.ensure_account(*owner)
        # 人为置为上一周期
        account.period_start = start - timedelta(days=40)
        account.period_end = start - timedelta(days=10)
        account.used = {"token": 999}
        await account.save()
        account2 = await QuotaService.ensure_account(*owner)
        self.assertEqual(account2.used, {})
        self.assertGreater(account2.period_end, datetime.now())

    async def test_reconcile_flushes_redis_to_pg(self):
        owner, plan = await self.make_cus_owner()
        hold_id = await QuotaService.quota_estimate(owner, {"token": 400})
        await QuotaService.quota_settle(hold_id, [{
            "execution_id": 9004, "node_id": "n1", "seq": 1,
            "resource_type": "llm_token", "amount": 250,
        }])
        count = await QuotaService.reconcile_active_accounts()
        self.assertGreaterEqual(count, 1)
        account = await QuotaAccount.get(owner_type="cus", owner_id=owner[1])
        self.assertEqual(float(account.used.get("token", 0)), 250)

    async def test_cleanup_stale_holds(self):
        owner, plan = await self.make_cus_owner()
        hold_id = await QuotaService.quota_estimate(owner, {"token": 400})
        # 人为过期索引
        self.fake._zsets[HOLD_INDEX_KEY][hold_id] = time.time() - 1
        released = await QuotaService.cleanup_stale_holds()
        self.assertEqual(released, 1)
        self.assertEqual(self.held_of(*owner, "token"), 0)

    async def test_board_shape(self):
        owner, plan = await self.make_cus_owner()
        hold_id = await QuotaService.quota_estimate(owner, {"token": 400})
        await QuotaService.quota_settle(hold_id, [{
            "execution_id": 9005, "node_id": "n1", "seq": 1,
            "resource_type": "llm_token", "amount": 120,
        }])
        board = await QuotaService.board(owner)
        self.assertEqual(board["plan"], plan.code)
        self.assertEqual(board["period"], current_period())
        items = {i["item"]: i for i in board["items"]}
        self.assertEqual(items["token"]["limit"], 1000)
        self.assertEqual(items["token"]["used"], 120)
        self.assertEqual(items["token"]["held"], 280)
        self.assertIn("concurrency", items)


# ============================================================
# 5. 套餐解析（会员等级 / 角色 / 优先级）
# ============================================================
class PlanResolveTest(QuotaTestCase):

    async def test_membership_level_mapping(self):
        owner, plan = await self.make_cus_owner()
        resolved = await PlanService.resolve_plan("cus", owner[1])
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.code, plan.code)

    async def test_role_mapping(self):
        owner, plan = await self.make_usr_owner()
        resolved = await PlanService.resolve_plan("usr", owner[1])
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.code, plan.code)

    async def test_priority_wins(self):
        owner, plan = await self.make_usr_owner(token_limit=500)
        better = await QuotaPlan.create(
            code="better_plan", name="更优套餐", scope="usr",
            quota_items={"token": 5000},
        )
        await QuotaPlanBinding.create(
            bind_type="role", bind_key="operator_plus", plan_id=better.id, priority=9
        )
        # 给用户加第二个角色
        from base.core.users.models.rbac import Role
        from base.core.users.models.users import User
        suffix = str(int(time.time() * 1000) % 10_000_000)
        role2 = await Role.create(name=f"运营加{suffix}", code="operator_plus")
        user = await User.get(id=owner[1])
        await user.roles.add(role2)
        resolved = await PlanService.resolve_plan("usr", owner[1])
        self.assertEqual(resolved.code, "better_plan")

    async def test_plan_crud_and_binding(self):
        plan = await PlanService.create_plan({
            "code": "crud_plan", "name": "CRUD", "quota_items": {"token": 10},
        })
        with self.assertRaises(ValueError):
            await PlanService.create_plan({"code": "crud_plan", "name": "dup"})
        updated = await PlanService.update_plan(plan.id, {"name": "CRUD2"})
        self.assertEqual(updated.name, "CRUD2")
        binding = await PlanService.bind("role", "r1", plan.id, priority=2)
        # 幂等重绑
        binding2 = await PlanService.bind("role", "r1", plan.id, priority=5)
        self.assertEqual(binding.id, binding2.id)
        self.assertEqual(binding2.priority, 5)
        self.assertEqual(len(await PlanService.list_bindings(bind_type="role")), 1)
        self.assertTrue(await PlanService.unbind(binding.id))
        self.assertTrue(await PlanService.delete_plan(plan.id))


# ============================================================
# 6. 字符启发式预估
# ============================================================
class EstimatorTest(unittest.TestCase):

    def test_english(self):
        # 350 chars / 3.5 = 100
        self.assertEqual(estimate_tokens("a" * 350), 100)

    def test_chinese_conservative(self):
        # 150 中文字 / 1.5 = 100（保守取高）
        self.assertEqual(estimate_tokens("汉" * 150), 100)

    def test_mixed_and_reserve(self):
        tokens = estimate_tokens("汉" * 15 + "a" * 35, reserve_output=50)
        self.assertEqual(tokens, 10 + 10 + 50)

    def test_messages(self):
        msgs = [{"role": "user", "content": "a" * 35}, {"role": "system", "content": "汉" * 15}]
        # content: 35/3.5=10 + 15/1.5=10；role 字符串也计入（user=2, system=2），保守取高
        self.assertEqual(estimate_messages_tokens(msgs), 10 + 10 + 2 + 2)


if __name__ == "__main__":
    unittest.main()
