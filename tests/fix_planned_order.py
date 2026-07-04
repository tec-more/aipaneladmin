import psycopg2

conn = psycopg2.connect(host='127.0.0.1', port=15432, user='admin', password='Admin@123', database='aipaneladmin')
cur = conn.cursor()

# Fix mrp2_planned_order: make old NOT NULL columns nullable
alter_statements = [
    "ALTER TABLE mrp2_planned_order ALTER COLUMN order_no DROP NOT NULL",
    "ALTER TABLE mrp2_planned_order ALTER COLUMN item_code DROP NOT NULL",
    "ALTER TABLE mrp2_planned_order ALTER COLUMN item_name DROP NOT NULL",
    "ALTER TABLE mrp2_planned_order ALTER COLUMN planned_quantity DROP NOT NULL",
    "ALTER TABLE mrp2_planned_order ALTER COLUMN planned_start_date DROP NOT NULL",
    "ALTER TABLE mrp2_planned_order ALTER COLUMN planned_end_date DROP NOT NULL",
    "ALTER TABLE mrp2_planned_order ALTER COLUMN unit DROP NOT NULL",
]

for stmt in alter_statements:
    try:
        cur.execute(stmt)
        conn.commit()
        print(f"OK: {stmt}")
    except Exception as e:
        conn.rollback()
        print(f"SKIP: {stmt} -> {e}")

conn.close()
print("\nDone!")