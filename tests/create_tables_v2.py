import asyncio
from tortoise import Tortoise
from base.common.setting import TORTOISE_ORM

async def create_tables():
    await Tortoise.init(config=TORTOISE_ORM)
    conn = Tortoise.get_connection('postgres')
    
    import asyncpg
    raw_conn = await asyncpg.connect(
        host="127.0.0.1", port=15432,
        user="admin", password="Admin@123",
        database="aipaneladmin"
    )
    
    from tortoise.backends.asyncpg.schema_generator import AsyncpgSchemaGenerator
    generator = AsyncpgSchemaGenerator(conn)
    
    created = 0
    failed = 0
    
    for app_name, app in Tortoise.apps.items():
        for model_name, model in app.items():
            table_name = model._meta.db_table
            try:
                exists = await raw_conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1)",
                    table_name
                )
                if not exists:
                    try:
                        schema_result = generator._get_table_sql(model, True)
                        create_sql = schema_result[0] if isinstance(schema_result, tuple) else str(schema_result)
                        if create_sql and create_sql.strip():
                            await raw_conn.execute(create_sql)
                            created += 1
                            print(f"  OK: {table_name}")
                    except Exception as e:
                        err = str(e)[:100]
                        failed += 1
                        print(f"  FAILED {table_name}: {err}")
            except Exception as e:
                print(f"  CHECK ERROR {table_name}: {str(e)[:60]}")
    
    await raw_conn.close()
    await Tortoise.close_connections()
    print(f"\nCreated: {created}, Failed: {failed}")

asyncio.run(create_tables())