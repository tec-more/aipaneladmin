import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    print(f"Tables on port 15432: {len(tables)}")
    for t in tables:
        print(f"  {t[0]}")
    await conn.close()

asyncio.run(check())