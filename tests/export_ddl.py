import asyncio
import asyncpg

async def export_ddl():
    conn5432 = await asyncpg.connect(
        host="127.0.0.1", port=5432,
        user="admin", password="123456",
        database="aipaneladmin"
    )
    conn15432 = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )

    tables_5432 = await conn5432.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    tables_15432 = await conn15432.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )

    t5432 = set(r[0] for r in tables_5432)
    t15432 = set(r[0] for r in tables_15432)

    missing = sorted(t5432 - t15432)
    print(f"Tables in 5432 but not in 15432: {len(missing)}")
    for t in missing:
        print(f"  {t}")

    existing_in_both = sorted(t5432 & t15432)
    print(f"\nTables in both: {len(existing_in_both)}")

    # Export DDL for missing tables
    ddl_statements = []
    for table_name in missing:
        try:
            rows = await conn5432.fetch(
                "SELECT column_name, data_type, character_maximum_length, "
                "is_nullable, column_default FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=$1 ORDER BY ordinal_position",
                table_name
            )
            if rows:
                cols = []
                for r in rows:
                    col_name = r[0]
                    data_type = r[1]
                    max_len = r[2]
                    nullable = r[3]
                    default = r[4]
                    
                    type_str = data_type
                    if max_len and data_type == "character varying":
                        type_str = f"varchar({max_len})"
                    
                    col_def = f'"{col_name}" {type_str}'
                    if default:
                        col_def += f" DEFAULT {default}"
                    if nullable == "NO":
                        col_def += " NOT NULL"
                    cols.append(col_def)
                
                ddl = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n  ' + ",\n  ".join(cols) + "\n);"
                ddl_statements.append(ddl)
        except Exception as e:
            print(f"  Error exporting {table_name}: {e}")

    # Write DDL to file
    with open("tests/create_missing_tables.sql", "w", encoding="utf-8") as f:
        for ddl in ddl_statements:
            f.write(ddl + "\n\n")
    
    print(f"\nExported {len(ddl_statements)} CREATE TABLE statements to tests/create_missing_tables.sql")

    await conn5432.close()
    await conn15432.close()

asyncio.run(export_ddl())