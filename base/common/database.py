import shutil
import logging
from aerich import Command
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise.expressions import Q

from base.common.setting import settings

async def init_db():
    print("开始初始化数据库...")
    print(f"模型列表: {settings.TORTOISE_ORM['apps']['models']['models']}")
    
    command = Command(tortoise_config=settings.TORTOISE_ORM)
    try:
        print("初始化数据库...")
        await command.init_db(safe=True)
        print("数据库初始化完成")
    except FileExistsError:
        print("数据库已存在，跳过初始化")
    except Exception as e:
        print(f"初始化数据库时出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        print("初始化aerich...")
        await command.init()
        print("aerich初始化完成")
    except Exception as e:
        print(f"初始化aerich时出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        print("执行数据库迁移...")
        await command.upgrade(run_in_transaction=True)
        print("数据库迁移完成")
    except Exception as e:
        print(f"执行数据库迁移时出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("数据库初始化流程完成")
    
async def init_data():
    await init_db()