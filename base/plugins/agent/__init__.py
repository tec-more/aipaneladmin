"""
Agent Development Base Plugin
"""

from fastapi import APIRouter
from .api.v1 import dialog_flow, workflow, agent, skill, memory, joke

# 创建主路由
router = APIRouter(prefix="/v1/agent")

# 包含所有子路由
router.include_router(agent.agent_router)
router.include_router(skill.skill_router)
router.include_router(memory.memory_router)
router.include_router(workflow.workflow_router)
router.include_router(workflow.workflow_execution_router)
router.include_router(dialog_flow.dialog_flow_router)
router.include_router(joke.joke_router)

async def on_enable(app):
    """Enable plugin"""
    app.include_router(router)
    return True

async def on_disable():
    """Disable plugin"""
    return True

async def on_startup():
    """Startup hook"""
    from base.plugins.agent.skills import slang_translator, joke_translator
    pass

async def on_shutdown():
    """Shutdown hook"""
    pass