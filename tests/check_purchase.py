import psycopg2

conn = psycopg2.connect(host='127.0.0.1', port=15432, user='admin', password='Admin@123', database='aipaneladmin')
cur = conn.cursor()

# Check purchase tables
for table in ['purchase_order', 'purchase_supplier']:
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position", (table,))
    cols = [row[0] for row in cur.fetchall()]
    if cols:
        print(f"\n=== {table} ===")
        for c in cols:
            print(f"  {c}")
    else:
        print(f"\n=== {table} === NOT EXISTS")

conn.close()