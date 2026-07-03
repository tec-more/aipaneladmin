import asyncio
import asyncpg

async def fix():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )

    # Check finance_accounts for duplicates
    rows = await conn.fetch(
        "SELECT id, code FROM finance_accounts ORDER BY id"
    )
    seen = set()
    dupes = []
    for r in rows:
        code = r[1]
        if code in seen:
            dupes.append(r[0])
        else:
            seen.add(code)
    print(f"finance_accounts: Total={len(rows)}, Unique={len(seen)}, Duplicates={len(dupes)}")
    for d in dupes:
        await conn.execute("DELETE FROM finance_accounts WHERE id=$1", d)
        print(f"  Deleted account id={d}")

    # Verify integration_account_mappings
    rows2 = await conn.fetch(
        "SELECT id, event_type FROM finance_integration_account_mappings ORDER BY id"
    )
    seen2 = set()
    dupes2 = []
    for r in rows2:
        et = r[1]
        if et in seen2:
            dupes2.append(r[0])
        else:
            seen2.add(et)
    print(f"integration_mappings: Total={len(rows2)}, Unique={len(seen2)}, Duplicates={len(dupes2)}")
    for d in dupes2:
        await conn.execute("DELETE FROM finance_integration_account_mappings WHERE id=$1", d)
        print(f"  Deleted mapping id={d}")

    await conn.close()

asyncio.run(fix())