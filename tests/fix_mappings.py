import asyncio
import asyncpg

async def fix():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )
    rows = await conn.fetch(
        "SELECT id, event_type FROM finance_integration_account_mappings ORDER BY id"
    )
    seen = set()
    dupes = []
    for r in rows:
        et = r[1]
        if et in seen:
            dupes.append(r[0])
        else:
            seen.add(et)
    print(f"Total: {len(rows)}, Unique: {len(seen)}, Duplicates: {len(dupes)}")
    for d in dupes:
        await conn.execute(
            "DELETE FROM finance_integration_account_mappings WHERE id=$1", d
        )
        print(f"  Deleted id={d}")
    await conn.close()

asyncio.run(fix())