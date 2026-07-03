import asyncio
import asyncpg

async def fix():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )

    tables_to_fix = [
        ("memory", "type", "VARCHAR(50) DEFAULT 'short_term'"),
        ("workflow_node", "type", "VARCHAR(50)"),
    ]
    for table, col, col_type in tables_to_fix:
        cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=$1 AND column_name=$2",
            table, col
        )
        if not cols:
            print(f"  Adding {col} column to {table}")
            try:
                await conn.execute(
                    f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}'
                )
                print(f"  OK: {table}.{col}")
            except Exception as e:
                print(f"  FAILED {table}.{col}: {e}")
        else:
            print(f"  {table}.{col} already exists")

    await conn.close()

asyncio.run(fix())