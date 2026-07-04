import psycopg2

conn = psycopg2.connect(host='127.0.0.1', port=15432, user='admin', password='Admin@123', database='aipaneladmin')
cur = conn.cursor()

alter_statements = [
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS tax_amount DECIMAL(10,2) DEFAULT 0",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_status VARCHAR(20) DEFAULT 'pending'",
]

for stmt in alter_statements:
    try:
        cur.execute(stmt)
        conn.commit()
        print(f"OK: {stmt}")
    except Exception as e:
        conn.rollback()
        print(f"FAIL: {stmt} -> {e}")

# Also fix aerich table id sequence
try:
    cur.execute("SELECT column_name, column_default FROM information_schema.columns WHERE table_name = 'aerich' AND column_name = 'id'")
    row = cur.fetchone()
    if row:
        print(f"aerich.id: {row}")
        if row[1] is None:
            cur.execute("CREATE SEQUENCE IF NOT EXISTS aerich_id_seq")
            cur.execute("ALTER TABLE aerich ALTER COLUMN id SET DEFAULT nextval('aerich_id_seq')")
            cur.execute("SELECT setval('aerich_id_seq', COALESCE((SELECT MAX(id) FROM aerich), 0) + 1)")
            conn.commit()
            print("OK: Fixed aerich id sequence")
        else:
            print("aerich id already has default")
    else:
        print("aerich table not found or no id column")
except Exception as e:
    conn.rollback()
    print(f"FAIL: aerich fix -> {e}")

conn.close()
print("\nDone!")