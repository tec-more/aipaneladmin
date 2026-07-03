import asyncio
import asyncpg

async def migrate_data():
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

    tables_to_migrate = [
        "suppliers",
        "product",
        "finance_accounts",
        "finance_integration_account_mappings",
    ]

    for table_name in tables_to_migrate:
        try:
            rows = await src.fetch(f'SELECT * FROM "{table_name}"')
            if not rows:
                print(f"  {table_name}: no data to migrate")
                continue

            cols = list(rows[0].keys())
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(f"${i+1}" for i in range(len(cols)))

            inserted = 0
            for row in rows:
                values = [row[c] for c in cols]
                try:
                    await dst.execute(
                        f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})',
                        *values
                    )
                    inserted += 1
                except Exception as e:
                    err = str(e)
                    if "duplicate" in err.lower() or "already exists" in err.lower() or "unique" in err.lower():
                        pass
                    else:
                        print(f"  INSERT ERROR {table_name}: {err[:60]}")

            print(f"  {table_name}: migrated {inserted}/{len(rows)} rows")
        except Exception as e:
            print(f"  ERROR {table_name}: {str(e)[:80]}")

    await src.close()
    await dst.close()

asyncio.run(migrate_data())