import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )
    count = await conn.fetchval("SELECT count(*) FROM event_records")
    print(f"event_records count: {count}")
    if count > 0:
        rows = await conn.fetch("SELECT id, event_name, status FROM event_records ORDER BY id DESC LIMIT 5")
        for r in rows:
            print(f"  id={r[0]}, event_name={r[1]}, status={r[2]}")
    else:
        print("  Table is empty!")
        # Check if there are any other tables with similar names
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%event%'"
        )
        for t in tables:
            tname = t[0]
            cnt = await conn.fetchval(f"SELECT count(*) FROM {tname}")
            print(f"  {tname}: {cnt} rows")
    await conn.close()

asyncio.run(check())