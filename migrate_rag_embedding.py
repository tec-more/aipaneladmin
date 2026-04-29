"""
添加Embedding模型字段的迁移脚本
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tortoise import Tortoise
from base.common.setting import TORTOISE_ORM


async def migrate():
    """执行迁移"""
    print("开始添加知识库Embedding模型字段...")

    await Tortoise.init(config=TORTOISE_ORM)

    conn = Tortoise.get_connection("postgres")

    try:
        try:
            await conn.execute_query("""
                ALTER TABLE rag_knowledge_base 
                ADD COLUMN embedding_model_id BIGINT
            """)
            print("  embedding_model_id 字段添加成功")
        except Exception as e:
            if "already exists" in str(e):
                print("  embedding_model_id 字段已存在")
            else:
                raise
        
        try:
            await conn.execute_query("""
                ALTER TABLE rag_knowledge_base 
                ADD CONSTRAINT rag_knowledge_base_embedding_model_id_fkey
                FOREIGN KEY (embedding_model_id) REFERENCES llm_model (id) ON DELETE SET NULL
            """)
            print("  外键约束添加成功")
        except Exception as e:
            if "already exists" in str(e):
                print("  外键约束已存在")
            else:
                raise
        
        print("OK! RAG Embedding数据库迁移完成")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(migrate())
