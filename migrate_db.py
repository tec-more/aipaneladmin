"""
手动添加新字段到数据库的迁移脚本
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
    print("开始数据库迁移...")
    
    # 初始化 Tortoise
    await Tortoise.init(config=TORTOISE_ORM)
    
    # 获取数据库连接
    conn = Tortoise.get_connection("postgres")
    
    try:
        # 1. 为 agent 表添加 default_memory_mode 字段
        print("\n1. 检查并添加 agent.default_memory_mode 字段...")
        try:
            await conn.execute_query("""
                ALTER TABLE agent 
                ADD COLUMN IF NOT EXISTS default_memory_mode VARCHAR(20) DEFAULT 'public'
            """)
            print("   [OK] agent.default_memory_mode 字段添加成功")
        except Exception as e:
            print(f"   [INFO] 字段可能已存在: {e}")
        
        # 2. 为 memory 表添加新字段
        print("\n2. 检查并添加 memory 表的新字段...")
        
        # 添加 memory_mode 字段
        try:
            await conn.execute_query("""
                ALTER TABLE memory 
                ADD COLUMN IF NOT EXISTS memory_mode VARCHAR(20) DEFAULT 'public'
            """)
            print("   [OK] memory.memory_mode 字段添加成功")
        except Exception as e:
            print(f"   [INFO] 字段可能已存在: {e}")
        
        # 添加 customer_id 字段
        try:
            await conn.execute_query("""
                ALTER TABLE memory 
                ADD COLUMN IF NOT EXISTS customer_id BIGINT
            """)
            print("   [OK] memory.customer_id 字段添加成功")
        except Exception as e:
            print(f"   [INFO] 字段可能已存在: {e}")
        
        # 添加 user_id 字段
        try:
            await conn.execute_query("""
                ALTER TABLE memory 
                ADD COLUMN IF NOT EXISTS user_id BIGINT
            """)
            print("   [OK] memory.user_id 字段添加成功")
        except Exception as e:
            print(f"   [INFO] 字段可能已存在: {e}")
        
        print("\n[OK] 数据库迁移完成！")
        
    except Exception as e:
        print(f"\n[ERROR] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(migrate())

