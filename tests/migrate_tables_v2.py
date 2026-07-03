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

    # First, create sequences
    seq_created = 0
    for table_name in missing:
        seq_name = f"{table_name}_id_seq"
        try:
            seq_exists = await dst.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.sequences WHERE sequence_schema='public' AND sequence_name=$1)",
                seq_name
            )
            if not seq_exists:
                try:
                    last_val = await src.fetchval(
                        "SELECT last_value FROM public.\"{}\"".format(seq_name)
                    )
                    await dst.execute(
                        f'CREATE SEQUENCE IF NOT EXISTS "{seq_name}" START WITH {last_val + 1}'
                    )
                    seq_created += 1
                except Exception:
                    await dst.execute(
                        f'CREATE SEQUENCE IF NOT EXISTS "{seq_name}" START WITH 1'
                    )
                    seq_created += 1
        except Exception as e:
            print(f"  SEQ SKIP {seq_name}: {str(e)[:60]}")

    print(f"Sequences created: {seq_created}")

    # Now create tables
    created = 0
    for table_name in missing:
        try:
            cols = await src.fetch(
                "SELECT column_name, udt_name, column_default, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=$1 "
                "ORDER BY ordinal_position",
                table_name
            )
            col_defs = []
            for c in cols:
                col_name = c[0]
                udt = c[1]
                default = c[2]
                nullable = c[3]
                col_def = f'"{col_name}" {udt}'
                if default:
                    col_def += f" DEFAULT {default}"
                if nullable == "NO":
                    col_def += " NOT NULL"
                col_defs.append(col_def)
            ddl = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n  ' + ",\n  ".join(col_defs) + "\n)"
            await dst.execute(ddl)
            created += 1
            print(f"  OK: {table_name}")
        except Exception as e:
            print(f"  FAILED {table_name}: {str(e)[:100]}")

    print(f"\nCreated: {created}/{len(missing)}")

    await src.close()
    await dst.close()

asyncio.run(migrate())