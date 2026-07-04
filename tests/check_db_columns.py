import psycopg2

conn = psycopg2.connect(host='127.0.0.1', port=15432, user='admin', password='Admin@123', database='aipaneladmin')
cur = conn.cursor()

tables_to_check = [
    'mes_material', 'mes_bom_version', 'mes_bom', 'mes_work_center', 'mes_process',
    'mes_route', 'mes_route_process', 'mes_manufacturing_order', 'mes_work_order',
    'mes_production_report', 'mes_material_requisition', 'mes_material_requisition_detail',
    'mes_material_return', 'mes_production_receipt', 'mes_production_exception',
    'mes_shift_definition', 'mes_shift_schedule', 'mes_shift_handover',
    'mes_trace_record', 'mes_tooling', 'mes_tooling_process_binding',
    'mes_energy_record', 'mes_barcode_record', 'mes_operation_log',
    'mrp2_sales_forecast', 'mrp2_sales_forecast_detail',
    'mrp2_master_production_schedule', 'mrp2_mps_detail', 'mrp2_mps_plan_line',
    'mrp2_mrp_calculation', 'mrp2_mrp_result_detail',
    'mrp2_capacity_requirement_plan', 'mrp2_crp_detail',
    'mrp2_plan_execution_monitor', 'mrp2_exception_alert', 'mrp2_planned_order',
    'product'
]

for table in tables_to_check:
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
        (table,)
    )
    cols = [row[0] for row in cur.fetchall()]
    if cols:
        print(f'=== {table} ===')
        for c in cols:
            print(f'  {c}')
    else:
        print(f'=== {table} === NOT EXISTS')

conn.close()