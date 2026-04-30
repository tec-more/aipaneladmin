#!/usr/bin/env python3
"""
验证数据库修复是否成功
"""
import asyncio
import asyncpg
from base.common.setting import settings

async def verify():
    """验证表结构"""
    conn = None
    try:
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name
        )
        print("数据库连接成功")

        # 检查表是否存在
        check_table_sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'rag_knowledge_base_department'
        );
        """
        exists = await conn.fetchval(check_table_sql)
        if not exists:
            print("表不存在！")
            return False

        print("表存在")

        # 检查列名
        check_cols_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'rag_knowledge_base_department'
        ORDER BY ordinal_position;
        """
        cols = await conn.fetch(check_cols_sql)
        col_names = [c['column_name'] for c in cols]
        print(f"列名: {col_names}")

        # 验证列名是否正确
        expected_cols = ['id', 'rag_knowledge_base_id', 'department_id']
        if col_names == expected_cols:
            print("列名正确！")
        else:
            print(f"列名不正确，期望: {expected_cols}")
            return False

        # 检查外键约束
        check_fk_sql = """
        SELECT constraint_name, column_name 
        FROM information_schema.key_column_usage 
        WHERE table_name = 'rag_knowledge_base_department';
        """
        fks = await conn.fetch(check_fk_sql)
        print(f"约束: {[dict(f) for f in fks]}")

        print("\n验证成功！表结构完全正确。")
        return True

    except Exception as e:
        print(f"错误: {e}")
        return False
    finally:
        if conn:
            await conn.close()

if __name__ == "__main__":
    success = asyncio.run(verify())
    if success:
        print("\n数据库修复完成！现在可以正常使用了。")
    else:
        print("\n验证失败，请检查数据库。")
