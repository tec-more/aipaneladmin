import psycopg2
conn = psycopg2.connect(host='127.0.0.1', port=15432, user='admin', password='Admin@123', database='aipaneladmin')
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'suppliers' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
if cols:
    print('=== suppliers ===')
    for c in cols: print(f'  {c}')
else:
    print('=== suppliers === NOT EXISTS')
conn.close()