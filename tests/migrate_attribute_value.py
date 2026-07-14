import subprocess
import os

DB_HOST = "127.0.0.1"
DB_PORT = "15432"
DB_NAME = "aipaneladmin"
DB_USER = "admin"
DB_PASSWORD = "Admin@123"

os.environ["PGPASSWORD"] = DB_PASSWORD

commands = [
    f'psql -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -d {DB_NAME} -c "ALTER TABLE product_attribute_value ADD COLUMN IF NOT EXISTS product_category_id INTEGER DEFAULT NULL;"',
    f'psql -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -d {DB_NAME} -c "CREATE INDEX IF NOT EXISTS idx_product_attribute_value_category ON product_attribute_value (product_category_id);"',
    f'psql -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -d {DB_NAME} -c "DROP INDEX IF EXISTS idx_product_attribute_value_unique;"',
    f'psql -h {DB_HOST} -p {DB_PORT} -U {DB_USER} -d {DB_NAME} -c "CREATE UNIQUE INDEX IF NOT EXISTS idx_product_attribute_value_unique ON product_attribute_value (attribute_id, value, COALESCE(product_category_id, -1));"',
]

for cmd in commands:
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("Success!")
    else:
        print(f"Error: {result.stderr}")

print("Migration completed!")