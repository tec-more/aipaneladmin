#!/usr/bin/env python3
"""
修复列名不匹配问题：将 ragknowledgebase_id 改为 rag_knowledge_base_id
"""
import asyncio
import asyncpg
from base.common.setting import settings

async def fix_column_names():
    """修复列名"""
    conn = None
    try:
        print(f"连接数据库: {settings.db_host}:{settings.db_port}/{settings.db_name}")
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name
        )
        print("数据库连接成功")

        # 检查当前列名
        check_cols_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'rag_knowledge_base_department';
        """
        cols = await conn.fetch(check_cols_sql)
        print(f"当前列名: {[c['column_name'] for c in cols]}")

        # 检查是否需要修复
        has_old_name = any(c['column_name'] == 'ragknowledgebase_id' for c in cols)
        has_new_name = any(c['column_name'] == 'rag_knowledge_base_id' for c in cols)

        if has_new_name:
            print("列名已正确，无需修复")
            return True

        if not has_old_name:
            print("未找到 ragknowledgebase_id 列，请检查表结构")
            return False

        print("开始修复列名...")

        # 1. 先删除旧的外键约束
        drop_fk_sql = """
        ALTER TABLE rag_knowledge_base_department 
        DROP CONSTRAINT IF EXISTS rag_knowledge_base_department_ragknowledgebase_id_fkey;
        """
        await conn.execute(drop_fk_sql)
        print("旧外键约束已删除")

        # 2. 重命名列
        rename_col_sql = """
        ALTER TABLE rag_knowledge_base_department 
        RENAME COLUMN ragknowledgebase_id TO rag_knowledge_base_id;
        """
        await conn.execute(rename_col_sql)
        print("列名已重命名为 rag_knowledge_base_id")

        # 3. 重新添加外键约束
        add_fk_sql = """
        ALTER TABLE rag_knowledge_base_department 
        ADD CONSTRAINT rag_knowledge_base_department_rag_knowledge_base_id_fkey
        FOREIGN KEY (rag_knowledge_base_id) REFERENCES rag_knowledge_base(id) ON DELETE CASCADE;
        """
        await conn.execute(add_fk_sql)
        print("外键约束已重新添加")

        # 4. 更新注释
        update_comment_sql = """
        COMMENT ON COLUMN rag_knowledge_base_department.rag_knowledge_base_id IS '知识库ID';
        """
        await conn.execute(update_comment_sql)
        print("注释已更新")

        # 验证结果
        final_cols = await conn.fetch(check_cols_sql)
        print(f"修复后的列名: {[c['column_name'] for c in final_cols]}")

        print("\n✅ 列名修复完成！")
        return True

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            await conn.close()
            print("数据库连接已关闭")

if __name__ == "__main__":
    asyncio.run(fix_column_names())
