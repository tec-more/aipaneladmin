import asyncio
import asyncpg

async def clean():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=5432,
        user="admin", password="123456",
        database="aipaneladmin"
    )
    result = await conn.execute("TRUNCATE TABLE event_records CASCADE")
    print(f"Truncate result: {result}")
    count = await conn.fetchval("SELECT count(*) FROM event_records")
    print(f"After truncate: {count}")
    await conn.close()

asyncio.run(clean())