import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )
    schemas = await conn.fetch(
        "SELECT schema_name FROM information_schema.schemata"
    )
    for s in schemas:
        print(f"Schema: {s[0]}")
    count = await conn.fetchval("SELECT count(*) FROM public.event_records")
    print(f"public.event_records: {count}")
    # Check if there's another schema with event_records
    tables = await conn.fetch(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_name = 'event_records'"
    )
    for t in tables:
        schema = t[0]
        tname = t[1]
        cnt = await conn.fetchval(f'SELECT count(*) FROM {schema}.{tname}')
        print(f"  {schema}.{tname}: {cnt} rows")
    await conn.close()

asyncio.run(check())