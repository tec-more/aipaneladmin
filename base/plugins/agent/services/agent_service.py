"""
Agent service
"""
from typing import List, Optional, Dict, Any
from tortoise.exceptions import DoesNotExist
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.models.skill import Skill
from base.plugins.agent.schemas.agent import AgentCreate, AgentUpdate

# 添加向量检索相关依赖
try:
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import Chroma
    VECTOR_SUPPORT = True
except ImportError:
    VECTOR_SUPPORT = False


class AgentService:
    """Agent service class"""

    @staticmethod
    async def create_agent(agent_data: AgentCreate) -> Agent:
        """Create agent"""
        # Create agent
        agent = await Agent.create(
            name=agent_data.name,
            description=agent_data.description,
            status=agent_data.status,
            config=agent_data.config,
            memory_capacity=agent_data.memory_capacity,
            system_prompt=agent_data.system_prompt
        )
        
        # Associate LLM model
        if agent_data.llm_model_id:
            from base.plugins.llm.models.model import LLMModel
            llm_model = await LLMModel.get(id=agent_data.llm_model_id)
            await agent.llm_model.set(llm_model)
        
        # Associate skills
        if agent_data.skill_ids:
            skills = await Skill.filter(id__in=agent_data.skill_ids).all()
            await agent.skills.add(*skills)
        
        # Associate workflows
        if agent_data.workflow_ids:
            from base.plugins.agent.models.workflow import Workflow
            workflows = await Workflow.filter(id__in=agent_data.workflow_ids).all()
            for workflow in workflows:
                await workflow.agents.add(agent)
        
        # Associate dialog flows
        if agent_data.dialog_flow_ids:
            from base.plugins.agent.models.dialog_flow import DialogFlow
            dialog_flows = await DialogFlow.filter(id__in=agent_data.dialog_flow_ids).all()
            for dialog_flow in dialog_flows:
                dialog_flow.agent = agent
                await dialog_flow.save()
        
        return agent

    @staticmethod
    async def get_agents(skip: int = 0, limit: int = 100, name: str = "", status: str = "") -> List[Agent]:
        """Get agent list"""
        query = Agent.all()
        if name:
            query = query.filter(name__icontains=name)
        if status:
            query = query.filter(status=status)
        agents = await query.offset(skip).limit(limit).prefetch_related('skills', 'llm_model')
        return agents

    @staticmethod
    async def get_agent_by_id(agent_id: int) -> Optional[Agent]:
        """Get agent by ID"""
        try:
            agent = await Agent.get(id=agent_id).prefetch_related('skills', 'memories', 'llm_model')
            return agent
        except DoesNotExist:
            return None

    @staticmethod
    async def update_agent(agent_id: int, agent_data: AgentUpdate) -> Optional[Agent]:
        """Update agent"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return None

        update_data = agent_data.model_dump(exclude_unset=True)
        skill_ids = update_data.pop('skill_ids', None)
        llm_model_id = update_data.pop('llm_model_id', None)
        workflow_ids = update_data.pop('workflow_ids', None)
        dialog_flow_ids = update_data.pop('dialog_flow_ids', None)
        
        await agent.update_from_dict(update_data)
        await agent.save()
        
        # Update LLM model
        if llm_model_id is not None:
            if llm_model_id:
                from base.plugins.llm.models.model import LLMModel
                llm_model = await LLMModel.get(id=llm_model_id)
                await agent.llm_model.set(llm_model)
            else:
                await agent.llm_model.clear()
        
        # Update skills
        if skill_ids is not None:
            await agent.skills.clear()
            if skill_ids:
                skills = await Skill.filter(id__in=skill_ids).all()
                await agent.skills.add(*skills)
        
        # Update workflows
        if workflow_ids is not None:
            # Get all existing workflows associated with this agent
            from base.plugins.agent.models.workflow import Workflow
            existing_workflows = await Workflow.filter(agents__id=agent.id).all()
            # Remove agent from existing workflows
            for workflow in existing_workflows:
                await workflow.agents.remove(agent)
            # Add agent to new workflows
            if workflow_ids:
                new_workflows = await Workflow.filter(id__in=workflow_ids).all()
                for workflow in new_workflows:
                    await workflow.agents.add(agent)
        
        # Update dialog flows
        if dialog_flow_ids is not None:
            # Get all existing dialog flows associated with this agent
            from base.plugins.agent.models.dialog_flow import DialogFlow
            existing_dialog_flows = await DialogFlow.filter(agent=agent).all()
            # Remove agent from existing dialog flows
            for dialog_flow in existing_dialog_flows:
                dialog_flow.agent = None
                await dialog_flow.save()
            # Add agent to new dialog flows
            if dialog_flow_ids:
                new_dialog_flows = await DialogFlow.filter(id__in=dialog_flow_ids).all()
                for dialog_flow in new_dialog_flows:
                    dialog_flow.agent = agent
                    await dialog_flow.save()
        
        return agent

    @staticmethod
    async def delete_agent(agent_id: int) -> bool:
        """Delete agent"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return False

        await agent.delete()
        return True

    @staticmethod
    async def get_agent_with_skills(agent_id: int) -> Optional[dict]:
        """Get agent with skills"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return None
        
        skills = await agent.skills.all()
        return {
            "agent": agent,
            "skills": skills
        }

    @staticmethod
    async def add_skill_to_agent(agent_id: int, skill_id: int) -> bool:
        """Add skill to agent"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return False
        
        try:
            skill = await Skill.get(id=skill_id)
            await agent.skills.add(skill)
            return True
        except DoesNotExist:
            return False

    @staticmethod
    async def remove_skill_from_agent(agent_id: int, skill_id: int) -> bool:
        """Remove skill from agent"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return False
        
        try:
            skill = await Skill.get(id=skill_id)
            await agent.skills.remove(skill)
            return True
        except DoesNotExist:
            return False

    @staticmethod
    def get_vector_store(agent_id: int, vector_store_path: Optional[str] = None) -> Optional['Chroma']:
        """获取智能体的向量存储"""
        if not VECTOR_SUPPORT:
            return None
        
        try:
            # 如果提供了向量存储路径，则使用该路径
            if vector_store_path:
                persist_directory = vector_store_path
            else:
                # 否则使用默认路径
                persist_directory = f"./vector_stores/agent_{agent_id}"
            
            embeddings = OpenAIEmbeddings()
            vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings
            )
            return vector_store
        except Exception as e:
            print(f"Error getting vector store: {e}")
            return None

    @staticmethod
    async def retrieve_relevant_documents(agent_id: int, query: str, k: int = 5, vector_store_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """从向量库中检索相关文档"""
        vector_store = AgentService.get_vector_store(agent_id, vector_store_path)
        if not vector_store:
            return []
        
        try:
            # 向量检索
            results = vector_store.similarity_search(query, k=k)
            
            # 格式化结果
            documents = []
            for doc in results:
                documents.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
            
            return documents
        except Exception as e:
            print(f"Error retrieving relevant documents: {e}")
            return []

    @staticmethod
    async def set_agent_skills(agent_id: int, skill_ids: List[int]) -> bool:
        """Set agent skills (replace all)"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return False
        
        await agent.skills.clear()
        if skill_ids:
            skills = await Skill.filter(id__in=skill_ids).all()
            await agent.skills.add(*skills)
        return True

    @staticmethod
    async def execute_agent(agent_id: int, input_data: dict) -> dict:
        """
        执行智能体
        根据提示词决定是否采用 ReAct 模型进行执行
        技能采用自动注册模式，可以从后台技能列表中读取技能信息
        如果关联了工作流或者对话流，则去读工作流或者对话流的流程处理
        实现 RAG 功能，根据用户输入检索相关记忆和文档
        """
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent or agent.status != "active":
            return {"success": False, "message": "Agent not found or inactive"}
        
        try:
            # 处理输入数据
            input_text = input_data.get("text", "")
            audio_data = input_data.get("audio", None)
            parameters = input_data.get("parameters", {})
            vector_store_path = input_data.get("vector_store_path", None)
            
            # 如果有音频输入，需要先转换为文本
            if audio_data:
                # 这里应该调用语音识别服务
                # 暂时使用占位符
                input_text = "这是一个黑话"
            
            # 从向量库中检索相关文档
            relevant_documents = []
            if input_text and VECTOR_SUPPORT:
                relevant_documents = await AgentService.retrieve_relevant_documents(agent_id, input_text, k=5, vector_store_path=vector_store_path)
            
            # 实现 RAG 功能：检索相关记忆
            relevant_memories = []
            if input_text:
                from base.plugins.agent.services.memory_service import MemoryService
                relevant_memories = await MemoryService.retrieve_relevant_memories(agent_id, input_text, k=5)
            
            # 构建上下文
            context = ""
            
            # 添加相关文档
            if relevant_documents:
                context += "相关文档：\n"
                for doc in relevant_documents:
                    context += f"- {doc['content'][:500]}...\n"  # 限制文档长度
                context += "\n"
            
            # 添加相关记忆
            if relevant_memories:
                context += "相关记忆：\n"
                for memory in relevant_memories:
                    context += f"- {memory.content}\n"
                context += "\n"
            
            # 构建完整的输入
            full_input = context + input_text
            
            # 检查智能体是否关联了工作流或对话流
            # 这里需要根据实际的模型关联关系来检查
            # 暂时假设智能体可以关联工作流和对话流
            has_workflow = False  # 实际应该检查智能体是否关联了工作流
            has_dialog_flow = False  # 实际应该检查智能体是否关联了对话流
            
            if has_workflow:
                # 执行工作流
                # 这里需要调用工作流执行服务
                from base.plugins.agent.services.workflow_service import WorkflowService
                # 假设智能体关联了一个工作流 ID
                workflow_id = 1  # 实际应该从智能体配置中获取
                # 将完整输入、相关记忆和相关文档传递给工作流
                input_data["text"] = full_input
                input_data["relevant_memories"] = [memory.content for memory in relevant_memories]
                input_data["relevant_documents"] = relevant_documents
                workflow_result = await WorkflowService.execute_workflow(workflow_id, input_data)
                return workflow_result
            elif has_dialog_flow:
                # 执行对话流
                # 这里需要调用对话流执行服务
                from base.plugins.agent.services.dialog_flow_service import DialogFlowService
                # 假设智能体关联了一个对话流 ID
                dialog_flow_id = 1  # 实际应该从智能体配置中获取
                # 将完整输入、相关记忆和相关文档传递给对话流
                input_data["text"] = full_input
                input_data["relevant_memories"] = [memory.content for memory in relevant_memories]
                input_data["relevant_documents"] = relevant_documents
                dialog_flow_result = await DialogFlowService.execute_dialog_flow(dialog_flow_id, input_data)
                return dialog_flow_result
            else:
                # 获取智能体的技能
                skills = await agent.skills.all()
                if not skills:
                    return {"success": False, "message": "No skills found for agent"}
                
                # 选择第一个技能执行（可以根据具体逻辑选择）
                skill = skills[0]
                
                # 根据提示词决定是否使用 ReAct 模式
                use_react = False
                if input_text:
                    # 简单的判断逻辑，实际可以更复杂
                    if "如何" in input_text or "为什么" in input_text or "什么是" in input_text:
                        use_react = True
                
                # 获取大模型名称
                model_name = "gpt-3.5-turbo"  # 默认模型
                if agent.llm_model:
                    model_name = agent.llm_model.model_id
                
                if use_react:
                    # 使用 ReAct 模式执行
                    from base.plugins.agent.services.react_agent_service import ReActAgentService
                    result = await ReActAgentService.execute_react_agent(skill.type, full_input, model_name)
                    return result
                else:
                    # 直接执行技能
                    from base.plugins.agent.services.skill_service import SkillService
                    result = await SkillService.execute_skill(skill.id, {"input_text": full_input, "model_name": model_name, "relevant_memories": [memory.content for memory in relevant_memories], "relevant_documents": relevant_documents, **parameters})
                    return result
        except Exception as e:
            return {"success": False, "message": str(e)}