"""
创建 RAG 相关数据库表的迁移脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from tortoise import Tortoise
from base.common.setting import TORTOISE_ORM


async def migrate():
    """
    执行数据库迁移
    """
    print("开始创建 RAG 数据库表...")
    
    # 初始化 Tortoise
    await Tortoise.init(config=TORTOISE_ORM)
    
    # 获取数据库连接
    conn = Tortoise.get_connection("postgres")
    
    try:
        # 1. 创建 rag_knowledge_base 表
        print("\n1. 创建 rag_knowledge_base 表...")
        try:
            await conn.execute_query("""
                CREATE TABLE IF NOT EXISTS rag_knowledge_base (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'active',
                    vector_dimension INTEGER DEFAULT 1024,
                    config JSONB
                )
            """)
            print("   [OK] rag_knowledge_base 表创建成功")
        except Exception as e:
            print(f"   [INFO] 表可能已存在: {e}")
        
        # 2. 创建 rag_document 表
        print("\n2. 创建 rag_document 表...")
        try:
            await conn.execute_query("""
                CREATE TABLE IF NOT EXISTS rag_document (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    knowledge_base_id BIGINT NOT NULL REFERENCES rag_knowledge_base(id) ON DELETE CASCADE,
                    title VARCHAR(500) NOT NULL,
                    file_name VARCHAR(500),
                    file_type VARCHAR(50),
                    file_size BIGINT,
                    file_path VARCHAR(1000),
                    content TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    chunk_count INTEGER DEFAULT 0,
                    metadata JSONB
                )
            """)
            print("   [OK] rag_document 表创建成功")
        except Exception as e:
            print(f"   [INFO] 表可能已存在: {e}")
        
        # 3. 创建 rag_document_chunk 表
        print("\n3. 创建 rag_document_chunk 表...")
        try:
            await conn.execute_query("""
                CREATE TABLE IF NOT EXISTS rag_document_chunk (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    document_id BIGINT NOT NULL REFERENCES rag_document(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    vector BYTEA,
                    metadata JSONB
                )
            """)
            print("   [OK] rag_document_chunk 表创建成功")
        except Exception as e:
            print(f"   [INFO] 表可能已存在: {e}")
        
        # 4. 创建索引
        print("\n4. 创建索引...")
        
        # rag_document 索引
        try:
            await conn.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_rag_document_kb_id ON rag_document(knowledge_base_id)
            """)
            print("   [OK] idx_rag_document_kb_id 索引创建成功")
        except Exception as e:
            print(f"   [INFO] 索引可能已存在: {e}")
        
        # rag_document_chunk 索引
        try:
            await conn.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_rag_document_chunk_doc_id ON rag_document_chunk(document_id)
            """)
            print("   [OK] idx_rag_document_chunk_doc_id 索引创建成功")
        except Exception as e:
            print(f"   [INFO] 索引可能已存在: {e}")
        
        print("\n[OK] RAG 数据库表创建完成！")
        
    except Exception as e:
        print(f"\n[ERROR] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(migrate())
