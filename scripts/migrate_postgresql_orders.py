#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PostgreSQL 订单系统迁移脚本（自动化版本）

功能：
1. 自动连接数据库
2. 备份原表
3. 重命名表
4. 创建新表
5. 迁移数据
6. 验证结果

使用方法：
    python scripts/migrate_postgresql_orders.py
"""

import psycopg2
import psycopg2.extras
import configparser
import json
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_db_connection():
    """从配置文件获取数据库连接"""
    try:
        # 读取配置文件
        config_path = Path(__file__).parent.parent / "config.conf"
        if not config_path.exists():
            print("[ERROR] 配置文件不存在: {}".format(config_path))
            return None

        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')

        # 读取数据库配置
        host = config.get('db', 'db_host', fallback='127.0.0.1')
        port = config.getint('db', 'db_port', fallback=5432)
        user = config.get('db', 'db_user', fallback='admin')
        password = config.get('db', 'db_password', fallback='123456')
        database = config.get('db', 'db_name', fallback='aipaneladmin')

        print("[INFO] 从配置文件读取数据库连接：")
        print("  主机: {}".format(host))
        print("  端口: {}".format(port))
        print("  用户: {}".format(user))
        print("  数据库: {}".format(database))

        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursor_factory=psycopg2.extras.DictCursor
        )

        print("\n[SUCCESS] 数据库连接成功！")
        return conn

    except Exception as e:
        print("\n[ERROR] 数据库连接失败: {}".format(e))
        print("\n请检查 config.conf 中的数据库配置：")
        print("  [db]")
        print("  db_host = 127.0.0.1")
        print("  db_port = 5432")
        print("  db_user = admin")
        print("  db_password = your_password")
        print("  db_name = aipaneladmin")
        return None


def migrate_orders():
    """执行订单数据迁移"""

    print("\n" + "=" * 60)
    print("PostgreSQL 订单系统迁移脚本（自动化版本）")
    print("=" * 60)
    print("[START] 开始时间: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # 获取数据库连接
    conn = get_db_connection()
    if not conn:
        return

    conn.autocommit = False

    try:
        print("\n" + "=" * 60)
        print("步骤1: 检查当前表结构")
        print("=" * 60)

        with conn.cursor() as cursor:
            # 检查当前表
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('customer_order', 'orders', 'order_items')
                ORDER BY table_name
            """)
            tables = cursor.fetchall()

            print("\n当前订单相关的表：")
            for table in tables:
                print("  - {}".format(table['table_name']))

            # 检查 customer_order 是否存在
            customer_order_exists = any(t['table_name'] == 'customer_order' for t in tables)
            if not customer_order_exists:
                print("\n[ERROR] customer_order 表不存在，无法迁移")
                return

        print("\n" + "=" * 60)
        print("步骤2: 备份原表")
        print("=" * 60)

        with conn.cursor() as cursor:
            # 备份原表
            cursor.execute("DROP TABLE IF EXISTS customer_order_backup")
            cursor.execute("""
                CREATE TABLE customer_order_backup AS
                SELECT * FROM customer_order
            """)
            print("[OK] 备份表创建成功")

        print("\n" + "=" * 60)
        print("步骤3: 删除旧的空表")
        print("=" * 60)

        with conn.cursor() as cursor:
            # 检查是否有 order 表需要删除
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'order'
                )
            """)
            has_old_order = cursor.fetchone()['exists']

            if has_old_order:
                cursor.execute("DROP TABLE IF EXISTS \"order\" CASCADE")
                print("[OK] 旧的 order 表已删除")
            else:
                print("[INFO] 没有找到旧的 order 表，跳过")

        print("\n" + "=" * 60)
        print("步骤4: 重命名主表")
        print("=" * 60)

        with conn.cursor() as cursor:
            cursor.execute("ALTER TABLE customer_order RENAME TO orders")
            print("[OK] 表重命名成功: customer_order -> orders")

        print("\n" + "=" * 60)
        print("步骤5: 创建明细表")
        print("=" * 60)

        with conn.cursor() as cursor:
            # 创建 order_items 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id BIGSERIAL PRIMARY KEY,
                    order_id BIGINT NOT NULL,
                    product_id BIGINT,
                    product_name VARCHAR(255) NOT NULL,
                    product_type VARCHAR(50) NOT NULL,
                    product_image VARCHAR(500),
                    quantity INTEGER DEFAULT 1 NOT NULL,
                    unit_price NUMERIC(10,2) NOT NULL,
                    total_price NUMERIC(10,2) NOT NULL,
                    extra_info JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_order_items_order_id
                        FOREIGN KEY (order_id)
                        REFERENCES orders(id)
                        ON DELETE CASCADE
                )
            """)
            print("[OK] order_items 表创建成功")

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_order_items_order_id
                ON order_items(order_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_order_items_product_id
                ON order_items(product_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_order_items_product_type
                ON order_items(product_type)
            """)
            print("[OK] 索引创建成功")

        print("\n" + "=" * 60)
        print("步骤6: 添加新字段")
        print("=" * 60)

        with conn.cursor() as cursor:
            # 添加新字段
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'orders'
                        AND column_name = 'total_amount'
                    ) THEN
                        ALTER TABLE orders ADD COLUMN total_amount NUMERIC(10,2);
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'orders'
                        AND column_name = 'discount_amount'
                    ) THEN
                        ALTER TABLE orders ADD COLUMN discount_amount NUMERIC(10,2) DEFAULT 0;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'orders'
                        AND column_name = 'final_amount'
                    ) THEN
                        ALTER TABLE orders ADD COLUMN final_amount NUMERIC(10,2);
                    END IF;
                END $$
            """)
            print("[OK] 字段添加成功")

        print("\n" + "=" * 60)
        print("步骤7: 迁移数据")
        print("=" * 60)

        with conn.cursor() as cursor:
            # 获取总记录数
            cursor.execute("SELECT COUNT(*) as count FROM orders")
            total_count = cursor.fetchone()['count']
            print("[INFO] 开始迁移 {} 条订单记录".format(total_count))

            # 迁移数据到 order_items
            cursor.execute("""
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    product_name,
                    product_type,
                    product_image,
                    quantity,
                    unit_price,
                    total_price,
                    extra_info,
                    created_at,
                    updated_at
                )
                SELECT
                    co.id AS order_id,
                    NULL::BIGINT AS product_id,
                    COALESCE(ml.name, 'Unknown') AS product_name,
                    'membership'::VARCHAR(50) AS product_type,
                    NULL::VARCHAR(500) AS product_image,
                    1 AS quantity,
                    co.amount AS unit_price,
                    co.amount AS total_price,
                    jsonb_build_object(
                        'membership_level_id', co.membership_level_id,
                        'membership_level_name', ml.name,
                        'hours', co.hours,
                        'bonus_hours', co.bonus_hours,
                        'total_hours', co.total_hours
                    ) AS extra_info,
                    co.created_at,
                    co.updated_at
                FROM orders co
                LEFT JOIN customer_membership_level ml
                ON co.membership_level_id = ml.id
                WHERE NOT EXISTS (
                    SELECT 1 FROM order_items
                    WHERE order_id = co.id
                )
            """)

            migrated_count = cursor.rowcount
            print("[OK] 成功迁移 {} 条订单明细".format(migrated_count))

        print("\n" + "=" * 60)
        print("步骤8: 更新金额字段")
        print("=" * 60)

        with conn.cursor() as cursor:
            # 更新金额字段
            cursor.execute("""
                UPDATE orders
                SET
                    total_amount = amount,
                    discount_amount = 0,
                    final_amount = amount
                WHERE total_amount IS NULL
                OR final_amount IS NULL
            """)

            updated_count = cursor.rowcount
            print("[OK] 更新了 {} 条订单的金额字段".format(updated_count))

        # 提交所有更改
        conn.commit()

        print("\n" + "=" * 60)
        print("步骤9: 验证迁移结果")
        print("=" * 60)

        verify_migration(conn)

        print("\n" + "=" * 60)
        print("[SUCCESS] 数据迁移完成！")
        print("=" * 60)
        print("[END] 结束时间: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    except KeyboardInterrupt:
        print("\n\n[CANCEL] 用户中断迁移")
        if conn:
            conn.rollback()
            print("[INFO] 已回滚所有更改")

    except Exception as e:
        print("\n\n[ERROR] 迁移过程出错: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            print("[INFO] 已回滚所有更改")

    finally:
        if conn:
            conn.close()


def verify_migration(conn):
    """验证迁移结果"""
    try:
        with conn.cursor() as cursor:
            # 统计各表记录数
            cursor.execute("SELECT COUNT(*) as count FROM orders")
            orders_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM order_items")
            items_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM customer_order_backup")
            backup_count = cursor.fetchone()['count']

            print("\n[INFO] 统计结果：")
            print("  - 备份表记录数: {}".format(backup_count))
            print("  - orders 表记录数: {}".format(orders_count))
            print("  - order_items 表记录数: {}".format(items_count))

            # 检查是否有订单没有明细
            cursor.execute("""
                SELECT order_no
                FROM orders co
                WHERE NOT EXISTS (
                    SELECT 1 FROM order_items
                    WHERE order_id = co.id
                )
                LIMIT 10
            """)
            missing_items = cursor.fetchall()

            if missing_items:
                print("\n[WARNING] 有 {} 个订单缺少明细（显示前10个）：".format(len(missing_items)))
                for item in missing_items:
                    print("  - {}".format(item['order_no']))
            else:
                print("\n[SUCCESS] 所有订单都有明细")

            # 显示迁移数据样本
            if items_count > 0:
                print("\n[INFO] 迁移数据样本（前5条）：")
                cursor.execute("""
                    SELECT
                        oi.id,
                        oi.order_id,
                        oi.product_name,
                        oi.quantity,
                        oi.unit_price,
                        oi.extra_info
                    FROM order_items oi
                    ORDER BY oi.id
                    LIMIT 5
                """)
                samples = cursor.fetchall()
                for sample in samples:
                    extra = sample.get('extra_info', {})
                    print("  - ID: {}, 订单ID: {}, 产品: {}, 数量: {}, 单价: {}".format(
                        sample['id'],
                        sample['order_id'],
                        sample['product_name'],
                        sample['quantity'],
                        sample['unit_price']
                    ))

    except Exception as e:
        print("\n[WARNING] 验证过程出错: {}".format(e))


if __name__ == "__main__":
    try:
        migrate_orders()
    except Exception as e:
        print("\n[ERROR] 脚本执行失败: {}".format(e))
        import traceback
        traceback.print_exc()
