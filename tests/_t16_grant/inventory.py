"""测试数据现状盘点"""
import asyncio
import json
import sys

import asyncpg

DSN = dict(host="127.0.0.1", port=15432, user="admin", password="Admin@123", database="aipaneladmin", timeout=10)

SQLS = {
    "customers": "SELECT id, username, nickname, email, is_active FROM customer ORDER BY id LIMIT 20",
    "orgs": "SELECT id, name, status, owner_customer_id FROM customer_organization ORDER BY id LIMIT 20",
    "org_members": "SELECT id, org_id, customer_id, role, status FROM customer_organization_member ORDER BY id LIMIT 30",
    "users": "SELECT id, username, email, is_active, is_superuser FROM users ORDER BY id LIMIT 20",
    "models": "SELECT id, model_name, status FROM llm_model ORDER BY id DESC LIMIT 5",
    "kbs": "SELECT id, name, status FROM rag_knowledge_base ORDER BY id DESC LIMIT 5",
    "tools": "SELECT id, display_name, enabled FROM tool ORDER BY id DESC LIMIT 8",
    "agents": "SELECT id, name, status FROM agent ORDER BY id DESC LIMIT 5",
    "grants": "SELECT count(*) AS c FROM resource_grant",
}


async def main():
    conn = await asyncpg.connect(**DSN)
    try:
        for name, sql in SQLS.items():
            print(f"===== {name} =====")
            try:
                rows = await conn.fetch(sql)
                for r in rows:
                    print(json.dumps(dict(r), ensure_ascii=False, default=str))
                if not rows:
                    print("(empty)")
            except Exception as e:
                print(f"ERR: {e}")
    finally:
        await conn.close()


asyncio.run(main())
