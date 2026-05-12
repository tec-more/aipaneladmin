"""
Agent Development Base Plugin
"""

from fastapi import APIRouter

router = APIRouter(prefix="/v1/agent")


def _setup_routes():
    """延迟设置路由，避免提前导入模型"""
    from .api.v1 import dialog_flow, workflow, agent, skill, skill_category, tool, tool_tag, memory, joke, rag, checkpoint
    
    @router.get("/test")
    async def test_endpoint():
        """测试端点"""
        print("=== 测试端点被调用 ===")
        from base.common.response import success_response
        return success_response(data={"message": "测试成功"}, msg="测试端点响应成功")

    router.include_router(agent.agent_router)
    router.include_router(agent.execution_router)
    router.include_router(skill.skill_router)
    router.include_router(skill_category.skill_category_router)
    router.include_router(tool.tool_router)
    router.include_router(tool_tag.tool_tag_router)
    router.include_router(memory.memory_router)
    router.include_router(workflow.workflow_router)
    router.include_router(workflow.workflow_execution_router)
    router.include_router(dialog_flow.dialog_flow_router)
    router.include_router(joke.joke_router)
    router.include_router(rag.rag_router)
    router.include_router(checkpoint.router)


async def on_enable(app):
    """Enable plugin"""
    _setup_routes()
    app.include_router(router)
    return True

async def on_disable():
    """Disable plugin"""
    return True

async def on_startup():
    """Startup hook"""
    # 延迟导入技能模块，避免循环导入
    try:
        from base.plugins.agent.skills.registry import SkillRegistry
        await SkillRegistry.auto_register_all()
    except Exception as e:
        print(f"Error registering skills: {e}")
    pass

async def on_shutdown():
    """Shutdown hook"""
    pass