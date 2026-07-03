import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )
    result = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1)",
        "user"
    )
    print(f"user exists: {result}")
    result2 = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1)",
        "purchase_orders"
    )
    print(f"purchase_orders exists: {result2}")
    await conn.close()

asyncio.run(test())