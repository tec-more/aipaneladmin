import asyncio
import asyncpg

async def migrate():
    src = await asyncpg.connect(
        host="127.0.0.1", port=5432,
        user="admin", password="123456",
        database="aipaneladmin"
    )
    dst = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )

    src_tables = await src.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    dst_tables = await dst.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    src_set = set(r[0] for r in src_tables)
    dst_set = set(r[0] for r in dst_tables)
    missing = sorted(src_set - dst_set)

    print(f"Missing tables: {len(missing)}")

    created = 0
    for table_name in missing:
        try:
            ddl = await src.fetchval(
                "SELECT pg_get_tabledef($1::regclass, true)",
                f"public.{table_name}"
            )
        except Exception:
            try:
                cols = await src.fetch(
                    "SELECT column_name, data_type, character_maximum_length, "
                    "column_default, is_nullable, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=$1 "
                    "ORDER BY ordinal_position",
                    table_name
                )
                col_defs = []
                for c in cols:
                    col_name = c[0]
                    udt = c[5]
                    default = c[3]
                    nullable = c[4]
                    col_def = f'"{col_name}" {udt}'
                    if default:
                        col_def += f" DEFAULT {default}"
                    if nullable == "NO":
                        col_def += " NOT NULL"
                    col_defs.append(col_def)
                ddl = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n  ' + ",\n  ".join(col_defs) + "\n)"
            except Exception as e:
                print(f"  SKIP {table_name}: {str(e)[:80]}")
                continue

        if ddl:
            try:
                await dst.execute(ddl)
                created += 1
                print(f"  OK: {table_name}")
            except Exception as e:
                print(f"  FAILED {table_name}: {str(e)[:100]}")

    print(f"\nCreated: {created}/{len(missing)}")

    await src.close()
    await dst.close()

asyncio.run(migrate())