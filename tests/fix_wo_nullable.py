import psycopg2

conn = psycopg2.connect(host='127.0.0.1', port=15432, user='admin', password='Admin@123', database='aipaneladmin')
cur = conn.cursor()

# Make work_center_code and work_center_name nullable in mes_work_order
alter_statements = [
    "ALTER TABLE mes_work_order ALTER COLUMN work_center_code DROP NOT NULL",
    "ALTER TABLE mes_work_order ALTER COLUMN work_center_name DROP NOT NULL",
]

for stmt in alter_statements:
    try:
        cur.execute(stmt)
        conn.commit()
        print(f"OK: {stmt}")
    except Exception as e:
        conn.rollback()
        print(f"FAIL: {stmt} -> {e}")

conn.close()
print("\nDone!")