"""测试节点3 执行辅助：DB 直连查询（asyncpg）
用法: .venv/Scripts/python.exe tests/_t16_grant/db.py <command> [args]
命令:
  menu          查询权限管理分组与 grant 菜单
  query <sql>   执行任意只读查询
  exec <sql>    执行写 SQL（如菜单插入）
"""
import asyncio
import json
import sys

import asyncpg

DSN = dict(host="127.0.0.1", port=15432, user="admin", password="Admin@123", database="aipaneladmin", timeout=10)


async def main():
    cmd = sys.argv[1]
    conn = await asyncpg.connect(**DSN)
    try:
        if cmd == "menu":
            rows = await conn.fetch(
                "SELECT id, name, path, component, menu_type, parent_id, is_active, permission "
                "FROM menu WHERE name LIKE '%权限%' OR path LIKE '%grant%' OR name LIKE '%资源授权%' ORDER BY id"
            )
            for r in rows:
                print(json.dumps(dict(r), ensure_ascii=False, default=str))
            print("menu total:", await conn.fetchval("SELECT count(*) FROM menu"))
        elif cmd == "query":
            rows = await conn.fetch(sys.argv[2])
            for r in rows:
                print(json.dumps(dict(r), ensure_ascii=False, default=str))
            print(f"[{len(rows)} rows]")
        elif cmd == "exec":
            sql = sys.argv[2]
            res = await conn.execute(sql)
            print("EXEC:", res)
        else:
            print("unknown cmd")
    finally:
        await conn.close()


asyncio.run(main())
