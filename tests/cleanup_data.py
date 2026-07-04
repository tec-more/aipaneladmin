import psycopg2

conn = psycopg2.connect(host='127.0.0.1', port=15432, user='admin', password='Admin@123', database='aipaneladmin')
cur = conn.cursor()

# Clean up MES/MRP2 test data in reverse dependency order
tables_to_clean = [
    'mrp2_planned_order', 'mrp2_exception_alert', 'mrp2_plan_execution_monitor',
    'mrp2_crp_detail', 'mrp2_capacity_requirement_plan',
    'mrp2_mrp_result_detail', 'mrp2_mrp_calculation',
    'mrp2_mps_plan_line', 'mrp2_mps_detail', 'mrp2_master_production_schedule',
    'mrp2_sales_forecast_detail', 'mrp2_sales_forecast',
    'mes_operation_log', 'mes_barcode_record', 'mes_energy_record',
    'mes_tooling_process_binding', 'mes_tooling',
    'mes_trace_record', 'mes_shift_handover', 'mes_shift_schedule', 'mes_shift_definition',
    'mes_production_exception', 'mes_production_receipt',
    'mes_material_return', 'mes_material_requisition_detail', 'mes_material_requisition',
    'mes_production_report', 'mes_work_order', 'mes_manufacturing_order',
    'mes_route_process', 'mes_route', 'mes_process', 'mes_work_center',
    'mes_bom', 'mes_bom_version', 'mes_material',
]

for table in tables_to_clean:
    try:
        cur.execute(f"DELETE FROM {table}")
        deleted = cur.rowcount
        conn.commit()
        if deleted > 0:
            print(f"  Cleaned {table}: {deleted} rows")
    except Exception as e:
        conn.rollback()
        print(f"  SKIP {table}: {e}")

# Also reset product table test data
try:
    cur.execute("DELETE FROM product WHERE name LIKE 'TEST%'")
    deleted = cur.rowcount
    conn.commit()
    if deleted > 0:
        print(f"  Cleaned product: {deleted} rows")
except Exception as e:
    conn.rollback()
    print(f"  SKIP product: {e}")

conn.close()
print("\nCleanup done!")