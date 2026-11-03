"""测试节点3 种子数据准备（幂等：按唯一键 get_or_create）
目标数据（节点2约定）:
- customer: c16a(组织A成员) c16b(组织B成员) c16c(无组织) c16d(已禁用) + 既有 id=1
- org: T16组织A(active) / T16组织B(active) / T16组织C(disabled)
- tool: t16_tool_on(enabled) / t16_tool_off(disabled)
- model: T16停用模型(disabled)（active 已有 id=16）
- agent: T16停用智能体(disabled)（active 已有 id=10）
- usr: 使用既有 id=1；另确认 t16_usr 后台用户存在
运行: .venv/Scripts/python.exe tests/_t16_grant/seed.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tortoise import Tortoise

from base.common.setting import get_model_list

DB_URL = "postgres://admin:Admin@123@127.0.0.1:15432/aipaneladmin"


async def main():
    await Tortoise.init(db_url=DB_URL, modules={"models": get_model_list()})
    from base.plugins.customer.models.customer import Customer
    from base.plugins.customer.models.customer_organization import (
        CustomerOrganization,
        CustomerOrganizationMember,
    )
    from base.plugins.agent.models.tool import Tool
    from base.plugins.llm.models.model import LLMModel
    from base.plugins.agent.models.agent import Agent
    from base.core.users.models.users import User

    # ---- customers ----
    c_a, _ = await Customer.get_or_create(
        username="t16cusa", defaults=dict(nickname="T16客户A", email="t16cusa@t.com", is_active=True)
    )
    c_b, _ = await Customer.get_or_create(
        username="t16cusb", defaults=dict(nickname="T16客户B", email="t16cusb@t.com", is_active=True)
    )
    c_c, _ = await Customer.get_or_create(
        username="t16cusc", defaults=dict(nickname="T16客户C", email="t16cusc@t.com", is_active=True)
    )
    c_d, created = await Customer.get_or_create(
        username="t16cusd", defaults=dict(nickname="T16客户D禁用", email="t16cusd@t.com", is_active=False)
    )
    if not created and c_d.is_active:
        c_d.is_active = False
        await c_d.save()
    print("customers:", c_a.id, c_b.id, c_c.id, c_d.id)

    # ---- orgs ----
    org_a, _ = await CustomerOrganization.get_or_create(
        name="T16组织A", defaults=dict(owner_customer_id=c_a.id, status="active")
    )
    org_b, _ = await CustomerOrganization.get_or_create(
        name="T16组织B", defaults=dict(owner_customer_id=c_b.id, status="active")
    )
    org_c, created = await CustomerOrganization.get_or_create(
        name="T16组织C停用", defaults=dict(owner_customer_id=c_c.id, status="disabled")
    )
    if not created and org_c.status != "disabled":
        org_c.status = "disabled"
        await org_c.save()
    print("orgs:", org_a.id, org_b.id, org_c.id)

    # ---- members (c_a in A; c_b in B; c_c none; 既有 customer id=1 in A) ----
    for oid, cid, role in [(org_a.id, c_a.id, "owner"), (org_a.id, 1, "member"), (org_b.id, c_b.id, "owner")]:
        m, mc = await CustomerOrganizationMember.get_or_create(
            org_id=oid, customer_id=cid, defaults=dict(role=role, status="active")
        )
        if not mc and m.status != "active":
            m.status = "active"
            await m.save()
    print("members ok")

    # ---- tools ----
    t_on, _ = await Tool.get_or_create(
        name="t16_tool_on", defaults=dict(display_name="T16启用工具", enabled=True)
    )
    t_off, created = await Tool.get_or_create(
        name="t16_tool_off", defaults=dict(display_name="T16禁用工具", enabled=False)
    )
    if not created and t_off.enabled:
        t_off.enabled = False
        await t_off.save()
    print("tools:", t_on.id, t_off.id)

    # ---- model disabled sample ----
    m_off, created = await LLMModel.get_or_create(
        model_name="T16停用模型", defaults=dict(provider_id=11, model_id="t16-disabled-model", status="disabled")
    )
    if not created and m_off.status == "active":
        m_off.status = "disabled"
        await m_off.save()
    print("models: active=16 disabled=", m_off.id)

    # ---- agent disabled sample ----
    a_off, created = await Agent.get_or_create(
        name="T16停用智能体", defaults=dict(status="disabled")
    )
    if not created and a_off.status == "active":
        a_off.status = "disabled"
        await a_off.save()
    print("agents: active=10 disabled=", a_off.id)

    # ---- usr check ----
    users = await User.all().limit(10)
    for u in users:
        print("usr:", u.id, u.username, "active=", getattr(u, "is_active", None), "super=", getattr(u, "is_superuser", None))

    await Tortoise.close_connections()


asyncio.run(main())
