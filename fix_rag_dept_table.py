#!/usr/bin/env python3
"""
修复知识库部门多对多关系表缺失的问题
"""
import asyncio
import asyncpg
from base.common.setting import settings

async def create_rag_dept_table():
    """创建知识库和部门的多对多关系表"""
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

        # 检查表是否存在
        check_sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'rag_knowledge_base_department'
        );
        """
        exists = await conn.fetchval(check_sql)
        
        if exists:
            print("表 rag_knowledge_base_department 已存在，跳过创建")
            return True

        print("开始创建表 rag_knowledge_base_department...")

        # 创建表的 SQL
        create_sql = """
        CREATE TABLE IF NOT EXISTS rag_knowledge_base_department (
            id SERIAL PRIMARY KEY,
            ragknowledgebase_id INT NOT NULL,
            department_id INT NOT NULL,
            UNIQUE(ragknowledgebase_id, department_id)
        );
        """
        
        await conn.execute(create_sql)
        print("表创建成功")

        # 添加外键约束（先检查是否存在）
        add_fk1_sql = """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'rag_knowledge_base_department_ragknowledgebase_id_fkey'
            ) THEN
                ALTER TABLE rag_knowledge_base_department
                ADD CONSTRAINT rag_knowledge_base_department_ragknowledgebase_id_fkey
                FOREIGN KEY (ragknowledgebase_id) REFERENCES rag_knowledge_base(id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
        
        add_fk2_sql = """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'rag_knowledge_base_department_department_id_fkey'
            ) THEN
                ALTER TABLE rag_knowledge_base_department
                ADD CONSTRAINT rag_knowledge_base_department_department_id_fkey
                FOREIGN KEY (department_id) REFERENCES department(id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
        
        await conn.execute(add_fk1_sql)
        await conn.execute(add_fk2_sql)
        print("外键约束添加成功")

        # 添加注释
        comment_table_sql = "COMMENT ON TABLE rag_knowledge_base_department IS '知识库与部门的关联表';"
        comment_col1_sql = "COMMENT ON COLUMN rag_knowledge_base_department.ragknowledgebase_id IS '知识库ID';"
        comment_col2_sql = "COMMENT ON COLUMN rag_knowledge_base_department.department_id IS '部门ID';"
        
        await conn.execute(comment_table_sql)
        await conn.execute(comment_col1_sql)
        await conn.execute(comment_col2_sql)
        print("注释添加成功")

        print("\n✅ 表 rag_knowledge_base_department 创建完成！")
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
    asyncio.run(create_rag_dept_table())
