import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )
    count = await conn.fetchval("SELECT count(*) FROM event_records")
    print(f"DB event_records count: {count}")
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE '%event%'"
    )
    for t in tables:
        tname = t[0]
        cnt = await conn.fetchval(f"SELECT count(*) FROM {tname}")
        print(f"Table {tname}: {cnt} rows")
    await conn.close()

asyncio.run(check())