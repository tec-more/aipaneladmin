"""
Agent service
"""
from typing import List, Optional
from tortoise.exceptions import DoesNotExist
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.schemas.agent import AgentCreate, AgentUpdate


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
        
        return agent

    @staticmethod
    async def get_agents(skip: int = 0, limit: int = 100, name: str = "", status: str = "") -> List[Agent]:
        """Get agent list"""
        query = Agent.all()
        if name:
            query = query.filter(name__icontains=name)
        if status:
            query = query.filter(status=status)
        agents = await query.offset(skip).limit(limit)
        return agents

    @staticmethod
    async def get_agent_by_id(agent_id: int) -> Optional[Agent]:
        """Get agent by ID"""
        try:
            agent = await Agent.get(id=agent_id)
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
        
        await agent.update_from_dict(update_data)
        await agent.save()
        
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
    async def execute_agent(agent_id: int, input_data: dict) -> dict:
        """
        执行智能体
        使用结构图（LangGraph的具现化）来实现智能体内部的逻辑控制
        结构图存储在 graph_definition 字段中
        """
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent or agent.status != "active":
            return {"success": False, "message": "Agent not found or inactive"}
        
        try:
            # 使用新的 LangGraph 执行器
            from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
            result = await LangGraphExecutor.execute_agent(agent, input_data)
            return result
        
        except Exception as e:
            import traceback
            return {"success": False, "message": str(e), "traceback": traceback.format_exc()}
    
    @staticmethod
    def _transform_node(node: dict) -> dict:
        """转换节点格式：模板格式 -> 系统格式"""
        transformed = {
            'id': node.get('id'),
            'type': node.get('type'),
            'position': node.get('position', {'x': 0, 'y': 0}),
            'data': {
                'label': node.get('name') or node.get('data', {}).get('label') or '节点',
                'description': node.get('data', {}).get('description', '')
            }
        }
        
        node_type = node.get('type')
        if node_type == 'llm':
            config = node.get('config', {})
            data = node.get('data', {})
            transformed['data']['prompt'] = config.get('prompt') or data.get('prompt', '')
            transformed['data']['modelId'] = config.get('model_id') or data.get('modelId')
            transformed['data']['temperature'] = data.get('temperature', 0.7)
            transformed['data']['maxTokens'] = data.get('maxTokens', 1024)
            transformed['data']['stream'] = data.get('stream', False)
            transformed['data']['outputVar'] = data.get('outputVar', '')
        elif node_type == 'tool':
            config = node.get('config', {})
            data = node.get('data', {})
            transformed['data']['toolName'] = config.get('tool_name') or data.get('toolName', '')
            transformed['data']['description'] = config.get('description') or data.get('description', '')
        elif node_type == 'decision' or node_type == 'condition':
            transformed['type'] = 'condition'
            config = node.get('config', {})
            data = node.get('data', {})
            transformed['data']['condition'] = config.get('condition') or data.get('condition', '')
        
        return transformed
    
    @staticmethod
    def _transform_edge(edge: dict, index: int) -> dict:
        """转换边格式：模板格式 -> 系统格式"""
        return {
            'id': edge.get('id') or f"{edge.get('source')}-{edge.get('target')}-{index}",
            'source': edge.get('source'),
            'target': edge.get('target'),
            'sourceHandle': edge.get('sourceHandle'),
            'targetHandle': edge.get('targetHandle'),
            'condition': edge.get('condition')
        }
    
    @staticmethod
    async def import_agent(import_data: dict) -> Agent:
        """
        导入智能体完整配置
        支持的格式：
        {
          "agent": { ... },
          "tools": [...],
          "skills": [...],
          "rag": {...}
        }
        或直接传入 agent 配置
        """
        # 提取 agent 数据
        agent_data = import_data.get('agent') or import_data
        
        # 转换 graph_definition 的格式
        graph_definition = agent_data.get('graph_definition', {'nodes': [], 'edges': []})
        if graph_definition and 'nodes' in graph_definition:
            graph_definition['nodes'] = [
                AgentService._transform_node(node)
                for node in graph_definition['nodes']
            ]
        if graph_definition and 'edges' in graph_definition:
            graph_definition['edges'] = [
                AgentService._transform_edge(edge, index)
                for index, edge in enumerate(graph_definition['edges'])
            ]
        
        # 创建智能体
        agent = await Agent.create(
            name=agent_data.get('name', '导入的智能体'),
            description=agent_data.get('description', ''),
            status=agent_data.get('status', 'active'),
            memory_capacity=agent_data.get('memory_capacity', 100),
            system_prompt=agent_data.get('system_prompt', ''),
            reasoning_strategy=agent_data.get('reasoning_strategy', 'function_call'),
            default_memory_mode=agent_data.get('default_memory_mode', 'public'),
            graph_definition=graph_definition
        )
        
        # TODO: 可以扩展导入 tools, skills, rag 等
        # 这里先只导入智能体基本配置和结构图
        
        return agent