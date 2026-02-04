import shutil
import logging
from aerich import Command
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise.expressions import Q

from base.common.setting import settings

async def init_db():
    command = Command(tortoise_config=settings.TORTOISE_ORM)
    try:
        await command.init_db(safe=True)
    except FileExistsError:
        pass

    await command.init()
    # Skip migrate during server startup to avoid interactive prompts
    # Run migrations manually with: aerich migrate
    await command.upgrade(run_in_transaction=True)
    
async def init_data():
    await init_db()