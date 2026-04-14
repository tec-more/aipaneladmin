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
        skill_count = await created_agent.skills.all().count()
        memory_count = await created_agent.memories.all().count()
        
        # Get workflow and dialog flow counts
        from base.plugins.agent.models.workflow import Workflow
        from base.plugins.agent.models.dialog_flow import DialogFlow
        workflow_count = len(await Workflow.filter(agents__id=created_agent.id).all())
        dialog_flow_count = len(await DialogFlow.filter(agent=created_agent).all())
        
        # Get LLM model name
        llm_model_name = None
        if created_agent.llm_model:
            llm_model_name = f"{created_agent.llm_model.provider.name} - {created_agent.llm_model.model_name}"
        
        data = AgentResponse(
            id=created_agent.id,
            name=created_agent.name,
            description=created_agent.description,
            status=created_agent.status,
            config=created_agent.config,
            memory_capacity=created_agent.memory_capacity,
            system_prompt=created_agent.system_prompt,
            reasoning_strategy=created_agent.reasoning_strategy,
            llm_model_id=created_agent.llm_model.id if created_agent.llm_model else None,
            created_at=created_agent.created_at,
            updated_at=created_agent.updated_at,
            skill_count=skill_count,
            memory_count=memory_count,
            workflow_count=workflow_count,
            dialog_flow_count=dialog_flow_count,
            llm_model_name=llm_model_name
        )
        return success_response(data=data.model_dump(), msg="智能体创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.get("/")
async def get_agents(skip: int = 0, limit: int = 100, name: str = "", status: str = ""):
    """Get all agents"""
    agents = await AgentService.get_agents(skip=skip, limit=limit, name=name, status=status)
    response = []
    for agent in agents:
        skill_count = await agent.skills.all().count()
        memory_count = await agent.memories.all().count()
        
        # Get workflow and dialog flow counts
        from base.plugins.agent.models.workflow import Workflow
        from base.plugins.agent.models.dialog_flow import DialogFlow
        workflow_count = len(await Workflow.filter(agents__id=agent.id).all())
        dialog_flow_count = len(await DialogFlow.filter(agent=agent).all())
        
        # Get LLM model name
        llm_model_name = None
        if agent.llm_model:
            llm_model_name = f"{agent.llm_model.provider.name} - {agent.llm_model.model_name}"
        
        response.append(AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            status=agent.status,
            config=agent.config,
            memory_capacity=agent.memory_capacity,
            system_prompt=agent.system_prompt,
            reasoning_strategy=agent.reasoning_strategy,
            llm_model_id=agent.llm_model.id if agent.llm_model else None,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            skill_count=skill_count,
            memory_count=memory_count,
            workflow_count=workflow_count,
            dialog_flow_count=dialog_flow_count,
            llm_model_name=llm_model_name
        ).model_dump())
    return success_response(data={"items": response, "total": len(response)})


@agent_router.get("/{agent_id}")
async def get_agent(agent_id: int):
    """Get agent by ID"""
    agent = await AgentService.get_agent_by_id(agent_id)
    if not agent:
        return fail_response(msg="智能体不存在", code=404)
    
    skill_count = await agent.skills.all().count()
    memory_count = await agent.memories.all().count()
    
    # Get LLM model name
    llm_model_name = None
    if agent.llm_model:
        llm_model_name = f"{agent.llm_model.provider.name} - {agent.llm_model.model_name}"
    
    # Get workflow and dialog flow counts and IDs
    from base.plugins.agent.models.workflow import Workflow
    from base.plugins.agent.models.dialog_flow import DialogFlow
    workflows = await Workflow.filter(agents__id=agent.id).all()
    dialog_flows = await DialogFlow.filter(agent=agent).all()
    workflow_count = len(workflows)
    dialog_flow_count = len(dialog_flows)
    workflow_ids = [workflow.id for workflow in workflows]
    dialog_flow_ids = [dialog_flow.id for dialog_flow in dialog_flows]
    
    data = {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "status": agent.status,
        "config": agent.config,
        "memory_capacity": agent.memory_capacity,
        "system_prompt": agent.system_prompt,
        "reasoning_strategy": agent.reasoning_strategy,
        "llm_model_id": agent.llm_model.id if agent.llm_model else None,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
        "skill_count": skill_count,
        "memory_count": memory_count,
        "workflow_count": workflow_count,
        "dialog_flow_count": dialog_flow_count,
        "workflow_ids": workflow_ids,
        "dialog_flow_ids": dialog_flow_ids,
        "llm_model_name": llm_model_name
    }
    return success_response(data=data)


@agent_router.put("/{agent_id}")
async def update_agent(agent_id: int, agent: AgentUpdate):
    """Update agent"""
    updated_agent = await AgentService.update_agent(agent_id, agent)
    if not updated_agent:
        return fail_response(msg="智能体不存在", code=404)
    
    skill_count = await updated_agent.skills.all().count()
    memory_count = await updated_agent.memories.all().count()
    
    # Get LLM model name
    llm_model_name = None
    if updated_agent.llm_model:
        llm_model_name = f"{updated_agent.llm_model.provider.name} - {updated_agent.llm_model.model_name}"
    
    # Get workflow and dialog flow counts and IDs
    from base.plugins.agent.models.workflow import Workflow
    from base.plugins.agent.models.dialog_flow import DialogFlow
    workflows = await Workflow.filter(agents__id=updated_agent.id).all()
    dialog_flows = await DialogFlow.filter(agent=updated_agent).all()
    workflow_count = len(workflows)
    dialog_flow_count = len(dialog_flows)
    workflow_ids = [workflow.id for workflow in workflows]
    dialog_flow_ids = [dialog_flow.id for dialog_flow in dialog_flows]
    
    data = {
        "id": updated_agent.id,
        "name": updated_agent.name,
        "description": updated_agent.description,
        "status": updated_agent.status,
        "config": updated_agent.config,
        "memory_capacity": updated_agent.memory_capacity,
        "system_prompt": updated_agent.system_prompt,
        "reasoning_strategy": updated_agent.reasoning_strategy,
        "llm_model_id": updated_agent.llm_model.id if updated_agent.llm_model else None,
        "created_at": updated_agent.created_at,
        "updated_at": updated_agent.updated_at,
        "skill_count": skill_count,
        "memory_count": memory_count,
        "workflow_count": workflow_count,
        "dialog_flow_count": dialog_flow_count,
        "workflow_ids": workflow_ids,
        "dialog_flow_ids": dialog_flow_ids,
        "llm_model_name": llm_model_name
    }
    return success_response(data=data, msg="智能体更新成功")


@agent_router.delete("/{agent_id}")
async def delete_agent(agent_id: int):
    """Delete agent"""
    success = await AgentService.delete_agent(agent_id)
    if not success:
        return fail_response(msg="智能体不存在", code=404)
    return success_response(msg="智能体删除成功")


@agent_router.get("/{agent_id}/skills")
async def get_agent_skills(agent_id: int):
    """Get agent skills"""
    agent_data = await AgentService.get_agent_with_skills(agent_id)
    if not agent_data:
        return fail_response(msg="智能体不存在", code=404)
    
    skill_ids = [skill.id for skill in agent_data["skills"]]
    return success_response(data=skill_ids)


@agent_router.put("/{agent_id}/skills")
async def set_agent_skills(agent_id: int, data: dict):
    """Set agent skills"""
    skill_ids = data.get("skill_ids", [])
    success = await AgentService.set_agent_skills(agent_id, skill_ids)
    if not success:
        return fail_response(msg="设置技能失败", code=400)
    return success_response(msg="技能设置成功")


@agent_router.post("/{agent_id}/skills/{skill_id}")
async def add_skill_to_agent(agent_id: int, skill_id: int):
    """Add skill to agent"""
    success = await AgentService.add_skill_to_agent(agent_id, skill_id)
    if not success:
        return fail_response(msg="智能体或技能不存在", code=404)
    return success_response(msg="技能添加成功")


@agent_router.delete("/{agent_id}/skills/{skill_id}")
async def remove_skill_from_agent(agent_id: int, skill_id: int):
    """Remove skill from agent"""
    success = await AgentService.remove_skill_from_agent(agent_id, skill_id)
    if not success:
        return fail_response(msg="智能体或技能不存在", code=404)
    return success_response(msg="技能移除成功")


@agent_router.post("/{agent_id}/execute")
async def execute_agent(agent_id: int, input_data: dict):
    """Execute agent"""
    result = await AgentService.execute_agent(agent_id, input_data)
    if result.get("success"):
        return success_response(data=result, msg="智能体执行成功")
    else:
        return fail_response(msg=result.get("message", "执行失败"))


@agent_router.put("/{agent_id}/flow")
async def update_agent_flow(agent_id: int, flow_data: dict):
    """Update agent flow diagram"""
    try:
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        # 更新智能体配置中的流程图数据
        if not agent.config:
            agent.config = {}
        agent.config["flow_data"] = flow_data
        await agent.save()
        
        return success_response(msg="智能体流程图更新成功")
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.post("/{agent_id}/flow/execute")
async def execute_agent_flow(agent_id: int, input_data: dict):
    """Execute agent flow diagram"""
    try:
        from base.plugins.agent.services.agent_flow_service import AgentFlowService
        
        user_id = input_data.get("user_id", None)
        result = await AgentFlowService.execute_agent_flow(
            agent_id=agent_id,
            input_data=input_data,
            user_id=user_id
        )
        
        if result.get("success"):
            return success_response(data=result, msg="流程图执行成功")
        else:
            return fail_response(msg=result.get("message", "流程图执行失败"))
    except Exception as e:
        import traceback
        return fail_response(msg=f"流程图执行失败: {str(e)}", data={"traceback": traceback.format_exc()})


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
