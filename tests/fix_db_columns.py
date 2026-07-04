import psycopg2

conn = psycopg2.connect(host='127.0.0.1', port=15432, user='admin', password='Admin@123', database='aipaneladmin')
cur = conn.cursor()

statements = [
    "ALTER TABLE product ADD COLUMN IF NOT EXISTS uom_id INTEGER",
    "ALTER TABLE product ADD COLUMN IF NOT EXISTS uom_code VARCHAR(20) NOT NULL DEFAULT 'unit'",
    "ALTER TABLE product ADD COLUMN IF NOT EXISTS uom_name VARCHAR(50) NOT NULL DEFAULT '件'",
    "ALTER TABLE product ADD COLUMN IF NOT EXISTS uom_category VARCHAR(50) NOT NULL DEFAULT 'unit'",
    "ALTER TABLE product ADD COLUMN IF NOT EXISTS secondary_uom_code VARCHAR(20)",
    "ALTER TABLE product ADD COLUMN IF NOT EXISTS secondary_uom_name VARCHAR(50)",
    "ALTER TABLE product ADD COLUMN IF NOT EXISTS conversion_factor DECIMAL(12,4) NOT NULL DEFAULT 1",
]

for stmt in statements:
    try:
        cur.execute(stmt)
        conn.commit()
        print(f"OK: {stmt}")
    except Exception as e:
        conn.rollback()
        print(f"FAIL: {stmt} -> {e}")

conn.close()
print("\nDone!")