import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )
    count = await conn.fetchval("SELECT count(*) FROM event_records")
    print(f"Total event records: {count}")
    rows = await conn.fetch(
        "SELECT event_name, count(*) as cnt FROM event_records "
        "GROUP BY event_name ORDER BY cnt DESC LIMIT 10"
    )
    for r in rows:
        print(f"  {r[0]}: {r[1]}")
    await conn.close()

asyncio.run(check())