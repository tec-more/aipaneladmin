
"""
修复向量字段 - 删除旧的 bytea 格式，保留 pgvector 格式
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tortoise import Tortoise
from base.common.setting import TORTOISE_ORM


async def migrate():
    """执行迁移"""
    print("=" * 60)
    print("开始修复向量字段...")
    print("=" * 60)

    await Tortoise.init(config=TORTOISE_ORM)

    conn = Tortoise.get_connection("postgres")

    try:
        # 步骤 1: 获取当前列的详细信息
        print("\n[步骤 1] 检查当前列结构...")
        columns = await conn.execute_query_dict("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'rag_document_chunk'
            AND (column_name LIKE '%vector%')
            ORDER BY ordinal_position
        """)

        column_info = {}
        for col in columns:
            column_info[col['column_name']] = col
            print(f"  列名: {col['column_name']}, 类型: {col['data_type']}, UDT: {col['udt_name']}")

        # 步骤 2: 检查是否有冲突
        vector_columns = [c for c in columns if c['column_name'] == 'vector']

        if len(vector_columns) == 2:
            print("\n[警告] 发现两个 'vector' 列！")
            
            # 判断哪个是 pgvector（udt_name 应该是 'vector'）
            pgvector_col = None
            bytea_col = None
            
            for col in vector_columns:
                if col['udt_name'] == 'vector':
                    pgvector_col = col
                elif col['udt_name'] == 'bytea':
                    bytea_col = col

            if bytea_col:
                print(f"  删除旧的 bytea 格式的 vector 列...")
                
                # 删除旧的 bytea 列
                await conn.execute_query("""
                    ALTER TABLE rag_document_chunk DROP COLUMN vector
                """)
                
                print("✅ 已删除旧的 bytea vector 列")

                # 检查是否还剩 pgvector 列
                check = await conn.execute_query_dict("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'rag_document_chunk' AND column_name = 'vector'
                """)

                if not check:
                    # 如果 pgvector 列也被删了，重新创建
                    print("  重新创建 pgvector 格式的 vector 列...")
                    await conn.execute_query("""
                        ALTER TABLE rag_document_chunk ADD COLUMN vector VECTOR(1024)
                    """)
                    print("✅ 已重新创建 pgvector 列")
            
        elif len(vector_columns) == 1:
            col = vector_columns[0]
            print(f"\n只有一个 vector 列，类型: {col['data_type']}")
            
            if col['udt_name'] == 'bytea':
                print("  转换为 pgvector 格式...")
                # 如果是 bytea，先重命名，再创建新的
                await conn.execute_query("""
                    ALTER TABLE rag_document_chunk RENAME COLUMN vector TO vector_bytea_old
                """)
                await conn.execute_query("""
                    ALTER TABLE rag_document_chunk ADD COLUMN vector VECTOR(1024)
                """)
                print("✅ 已创建新的 pgvector 列")
                print("  旧的列已重命名为 vector_bytea_old（可以手动删除）")
                
        else:
            print("\n没有 vector 列，创建新的...")
            await conn.execute_query("""
                ALTER TABLE rag_document_chunk ADD COLUMN vector VECTOR(1024)
            """)
            print("✅ 已创建 vector 列")

        # 步骤 3: 更新 search_mode
        print("\n[步骤 2] 更新 search_mode 配置...")
        await conn.execute_query("""
            UPDATE rag_knowledge_base 
            SET search_mode = 'pgvector' 
            WHERE search_mode = 'binary'
        """)
        print("✅ search_mode 已更新")

        # 步骤 4: 最终检查
        print("\n[步骤 3] 最终检查...")
        final_check = await conn.execute_query_dict("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'rag_document_chunk'
            AND column_name = 'vector'
        """)

        if final_check:
            col = final_check[0]
            print(f"✅ vector 列类型: {col['udt_name']}")
            
            if col['udt_name'] == 'vector':
                print("\n🎉 迁移完成！")
            else:
                print(f"\n⚠️ 警告：vector 列类型是 {col['udt_name']}，不是 'vector'")
        else:
            print("\n❌ 错误：没有找到 vector 列！")

    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(migrate())

