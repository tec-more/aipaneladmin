import psycopg2
conn = psycopg2.connect(host='127.0.0.1', port=15432, user='admin', password='Admin@123', database='aipaneladmin')
cur = conn.cursor()
cur.execute("SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'mes_work_order' AND column_name IN ('work_center_code', 'work_center_name')")
for row in cur.fetchall():
    print(row)
conn.close()