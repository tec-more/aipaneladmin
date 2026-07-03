import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )
    rows = await conn.fetch("SELECT id, username, alias FROM \"user\" LIMIT 5")
    for r in rows:
        print(f"  id={r[0]}, username={r[1]}, alias={r[2]}")
    if not rows:
        print("  No users found!")
    await conn.close()

asyncio.run(check())