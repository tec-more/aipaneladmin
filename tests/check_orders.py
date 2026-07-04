import psycopg2

conn = psycopg2.connect(host='127.0.0.1', port=15432, user='admin', password='Admin@123', database='aipaneladmin')
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'orders' ORDER BY ordinal_position")
cols = [row[0] for row in cur.fetchall()]
print("=== orders table columns ===")
for c in cols:
    print(f"  {c}")

conn.close()