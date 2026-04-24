"""
Agent API routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from base.plugins.agent.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from base.plugins.agent.services.agent_service import AgentService
from base.common.response import success_response, fail_response

agent_router = APIRouter(prefix="/agents", tags=["agents"])


@agent_router.post("/")
async def create_agent(agent: AgentCreate):
    """Create a new agent"""
    try:
        created_agent = await AgentService.create_agent(agent)
        
        skill_count = 0
        memory_count = 0
        workflow_count = 0
        dialog_flow_count = 0
        
        data = AgentResponse(
            id=created_agent.id,
            name=created_agent.name,
            description=created_agent.description,
            status=created_agent.status,
            memory_capacity=created_agent.memory_capacity,
            system_prompt=created_agent.system_prompt,
            reasoning_strategy=created_agent.reasoning_strategy,
            llm_model_id=None,
            created_at=created_agent.created_at,
            updated_at=created_agent.updated_at,
            skill_count=skill_count,
            memory_count=memory_count,
            workflow_count=workflow_count,
            dialog_flow_count=dialog_flow_count
        )
        
        return success_response(data=data, msg="智能体创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.get("/")
async def get_agents(skip: int = 0, limit: int = 100, name: str = "", status: str = ""):
    """Get all agents"""
    agents = await AgentService.get_agents(skip=skip, limit=limit, name=name, status=status)
    response = []
    for agent in agents:
        skill_count = 0
        memory_count = 0
        
        response.append({
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "status": agent.status,
            "memory_capacity": agent.memory_capacity,
            "system_prompt": agent.system_prompt,
            "reasoning_strategy": agent.reasoning_strategy,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
            "skill_count": skill_count,
            "memory_count": memory_count
        })
    return success_response(data={"items": response, "total": len(response)})


@agent_router.get("/{agent_id}")
async def get_agent(agent_id: int):
    """Get agent by ID"""
    agent = await AgentService.get_agent_by_id(agent_id)
    if not agent:
        return fail_response(msg="智能体不存在", code=404)
    
    skill_count = 0
    memory_count = 0
    
    data = {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "status": agent.status,
        "memory_capacity": agent.memory_capacity,
        "system_prompt": agent.system_prompt,
        "reasoning_strategy": agent.reasoning_strategy,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
        "skill_count": skill_count,
        "memory_count": memory_count
    }
    return success_response(data=data)


@agent_router.put("/{agent_id}")
async def update_agent(agent_id: int, agent: AgentUpdate):
    """Update agent"""
    updated_agent = await AgentService.update_agent(agent_id, agent)
    if not updated_agent:
        return fail_response(msg="智能体不存在", code=404)
    
    skill_count = 0
    memory_count = 0
    
    data = {
        "id": updated_agent.id,
        "name": updated_agent.name,
        "description": updated_agent.description,
        "status": updated_agent.status,
        "memory_capacity": updated_agent.memory_capacity,
        "system_prompt": updated_agent.system_prompt,
        "reasoning_strategy": updated_agent.reasoning_strategy,
        "created_at": updated_agent.created_at.isoformat() if updated_agent.created_at else None,
        "updated_at": updated_agent.updated_at.isoformat() if updated_agent.updated_at else None,
        "skill_count": skill_count,
        "memory_count": memory_count
    }
    return success_response(data=data, msg="智能体更新成功")


@agent_router.delete("/{agent_id}")
async def delete_agent(agent_id: int):
    """Delete agent"""
    success = await AgentService.delete_agent(agent_id)
    if not success:
        return fail_response(msg="智能体不存在", code=404)
    return success_response(msg="智能体删除成功")


@agent_router.post("/{agent_id}/execute")
async def execute_agent(agent_id: int, input_data: dict):
    """Execute agent"""
    result = await AgentService.execute_agent(agent_id, input_data)
    if result.get("success"):
        return success_response(data=result, msg="智能体执行成功")
    else:
        return fail_response(msg=result.get("message", "执行失败1"))


@agent_router.post("/{agent_id}/graph/execute")
async def execute_agent_graph(agent_id: int, input_data: dict):
    """Execute agent graph diagram using LangGraph"""
    print(f"=== 执行智能体结构图: agent_id={agent_id}, input_data={input_data} ===")
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"执行智能体结构图: agent_id={agent_id}, input_data={input_data}")
        
        print(f"1. 导入LangGraphExecutor")
        from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
        
        print(f"2. 获取智能体: agent_id={agent_id}")
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            print(f"智能体不存在: agent_id={agent_id}")
            logger.error(f"智能体不存在: agent_id={agent_id}")
            return fail_response(msg="智能体不存在", code=404)
        
        print(f"3. 智能体信息: id={agent.id}, name={agent.name}")
        print(f"4. graph_definition类型: {type(agent.graph_definition)}")
        print(f"5. graph_definition值: {agent.graph_definition}")
        logger.info(f"智能体信息: id={agent.id}, name={agent.name}")
        logger.info(f"graph_definition类型: {type(agent.graph_definition)}")
        logger.info(f"graph_definition值: {agent.graph_definition}")
        
        print(f"6. 创建执行记录")
        from base.plugins.agent.models.dialog_flow import DialogFlowExecution
        execution_record = await DialogFlowExecution.create(
            dialog_flow_id=0,  # 用0表示是智能体图执行
            user_id=None,
            input_data=input_data,
            status="running",
            execution_path=[]
        )
        logger.info(f"创建执行记录: id={execution_record.id}")
        
        print(f"7. 执行智能体")
        result = await LangGraphExecutor.execute_agent(agent, input_data)
        
        print(f"8. 执行结果: {result}")
        logger.info(f"执行结果类型: {type(result)}")
        logger.info(f"执行结果: {result}")
        
        print(f"9. 更新执行记录")
        execution_record.output_data = result
        
        # 提取执行路径 - 从结果的多个位置尝试获取
        execution_path = []
        if isinstance(result, dict):
            if result.get('variables') and result['variables'].get('execution_path'):
                execution_path = result['variables']['execution_path']
            elif result.get('execution_path'):
                execution_path = result['execution_path']
            elif result.get('trace'):
                execution_path = result['trace']
            elif result.get('execution_trace'):
                execution_path = result['execution_trace']
        
        execution_record.execution_path = execution_path
        logger.info(f"提取到的执行路径: {execution_path}")
        
        from datetime import datetime
        execution_record.completed_at = datetime.now()
        execution_record.status = "completed" if (isinstance(result, dict) and result.get("success")) else "failed"
        
        # 显式保存并检查
        await execution_record.save()
        
        # 重新获取以确认保存成功
        saved_record = await DialogFlowExecution.get(id=execution_record.id)
        logger.info(f"保存后的执行记录: id={saved_record.id}, status={saved_record.status}")
        logger.info(f"保存后的输出数据: {saved_record.output_data}")
        logger.info(f"保存后的执行路径: {saved_record.execution_path}")
        
        if isinstance(result, dict) and result.get("success"):
            print(f"10. 执行成功")
            return success_response(data=result, msg="结构图执行成功")
        else:
            error_msg = result.get("message", "结构图执行失败") if isinstance(result, dict) else str(result)
            print(f"10. 执行失败: {error_msg}")
            return fail_response(msg=error_msg)
    except Exception as e:
        import traceback
        print(f"=== 异常: {e} ===")
        print(traceback.format_exc())
        logger.exception(f"执行智能体结构图失败: {e}")
        return fail_response(msg=f"结构图执行失败: {str(e)}", data={"traceback": traceback.format_exc()})


@agent_router.get("/{agent_id}/graph")
async def get_agent_graph(agent_id: int):
    """Get agent graph definition"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"=== 获取智能体结构图: agent_id={agent_id} ===")
        
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            logger.error(f"智能体不存在: agent_id={agent_id}")
            return fail_response(msg="智能体不存在", code=404)
        
        logger.info(f"agent.graph_definition: {agent.graph_definition}")
        logger.info(f"agent.graph_definition 类型: {type(agent.graph_definition)}")
        
        return success_response(data={
            "graph_definition": agent.graph_definition
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"获取智能体结构图失败: {e}")
        return fail_response(msg=str(e))


@agent_router.put("/{agent_id}/graph")
async def update_agent_graph(agent_id: int, graph_data: dict):
    """Update agent graph definition"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"=== 保存智能体结构图: agent_id={agent_id} ===")
        logger.info(f"接收到的 graph_data: {graph_data}")
        logger.info(f"graph_data 类型: {type(graph_data)}")
        
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            logger.error(f"智能体不存在: agent_id={agent_id}")
            return fail_response(msg="智能体不存在", code=404)
        
        logger.info(f"保存前 agent.graph_definition: {agent.graph_definition}")
        
        agent.graph_definition = graph_data
        await agent.save()
        
        logger.info(f"保存后 agent.graph_definition: {agent.graph_definition}")
        logger.info(f"保存后 agent.graph_definition 类型: {type(agent.graph_definition)}")
        
        return success_response(data={"graph_definition": agent.graph_definition}, msg="智能体结构图保存成功")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"保存智能体结构图失败: {e}")
        return fail_response(msg=str(e))


@agent_router.get("/test")
async def test_endpoint():
    """测试端点"""
    print("=== 测试端点被调用 ===")
    return success_response(data={"message": "测试成功"}, msg="测试端点响应成功")


@agent_router.post("/process-documents")
async def process_documents(
    directory_path: str = Query(..., description="文档目录路径"),
    vector_store_path: str = Query(..., description="向量库存储路径")
):
    """处理文档并生成向量库"""
    try:
        from base.plugins.agent.services.document_processing_service import DocumentProcessingService, VECTOR_SUPPORT
        import os
        
        # 检查向量支持是否启用
        if not VECTOR_SUPPORT:
            return fail_response(msg="向量支持未启用，请安装相关依赖", code=400)
        
        # 检查目录是否存在
        if not os.path.exists(directory_path):
            return fail_response(msg="文档目录不存在", code=404)
        
        # 确保向量库存储路径存在
        os.makedirs(vector_store_path, exist_ok=True)
        
        # 处理文档并创建向量库
        vector_store = DocumentProcessingService.process_document_directory(directory_path, vector_store_path)
        
        # 获取向量库信息
        collection_name = vector_store._collection.name
        document_count = vector_store._collection.count()
        
        return success_response(
            data={
                "vector_store_path": vector_store_path,
                "collection_name": collection_name,
                "document_count": document_count,
                "message": f"成功处理文档并生成向量库，共处理 {document_count} 个文档片段"
            },
            msg="文档处理成功"
        )
    except Exception as e:
        return fail_response(msg=str(e), code=500)


@agent_router.get("/{agent_id}/skills")
async def get_agent_skills(agent_id: int):
    """Get agent skills"""
    try:
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        config = agent.config or {}
        skill_ids = config.get("skills", [])
        
        from base.plugins.agent.models.skill import Skill
        skills = []
        if skill_ids:
            skills = await Skill.filter(id__in=skill_ids).all()
        
        return success_response(data={"skills": skills})
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.post("/{agent_id}/skills/{skill_id}")
async def add_skill_to_agent(agent_id: int, skill_id: int):
    """Add skill to agent"""
    try:
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        if not agent.config:
            agent.config = {}
        
        skills = agent.config.get("skills", [])
        if skill_id not in skills:
            skills.append(skill_id)
            agent.config["skills"] = skills
            await agent.save()
        
        return success_response(msg="技能添加成功")
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.delete("/{agent_id}/skills/{skill_id}")
async def remove_skill_from_agent(agent_id: int, skill_id: int):
    """Remove skill from agent"""
    try:
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        if not agent.config:
            agent.config = {}
        
        skills = agent.config.get("skills", [])
        if skill_id in skills:
            skills.remove(skill_id)
            agent.config["skills"] = skills
            await agent.save()
        
        return success_response(msg="技能移除成功")
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.put("/{agent_id}/skills")
async def set_agent_skills(agent_id: int, data: dict):
    """Set agent skills"""
    try:
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        if not agent.config:
            agent.config = {}
        
        skill_ids = data.get("skill_ids", [])
        agent.config["skills"] = skill_ids
        await agent.save()
        
        return success_response(msg="技能设置成功")
    except Exception as e:
        return fail_response(msg=str(e))
