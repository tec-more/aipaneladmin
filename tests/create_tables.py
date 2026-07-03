import asyncio
import asyncpg

async def create_tables():
    with open("tests/create_missing_tables.sql", "r", encoding="utf-8") as f:
        sql = f.read()
    
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )
    
    statements = [s.strip() for s in sql.split(";") if s.strip() and s.strip().startswith("CREATE")]
    success = 0
    failed = 0
    for stmt in statements:
        try:
            await conn.execute(stmt)
            table_name = stmt.split('"')[1] if '"' in stmt else "unknown"
            success += 1
        except Exception as e:
            table_name = stmt.split('"')[1] if '"' in stmt else "unknown"
            print(f"  FAILED {table_name}: {str(e)[:100]}")
            failed += 1
    
    print(f"\nCreated: {success}, Failed: {failed}")
    
    # Verify
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    print(f"Total tables now: {len(tables)}")
    
    await conn.close()

asyncio.run(create_tables())