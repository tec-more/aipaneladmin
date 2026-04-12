"""
Workflow service
"""
from typing import List, Optional, Dict, Any
from tortoise.exceptions import DoesNotExist
from base.plugins.agent.models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowExecution
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.models.skill import Skill
from base.plugins.agent.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowExecutionCreate
)

# Try to import LangGraph and LangChain
try:
    from langchain_core.runnables import RunnableConfig
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


class WorkflowService:
    """Workflow service class"""

    @staticmethod
    async def create_workflow(workflow_data: WorkflowCreate) -> Workflow:
        """Create workflow"""
        workflow = await Workflow.create(
            name=workflow_data.name,
            description=workflow_data.description,
            status=workflow_data.status,
            definition=workflow_data.definition
        )
        
        # Associate agents
        if workflow_data.agent_ids:
            agents = await Agent.filter(id__in=workflow_data.agent_ids).all()
            await workflow.agents.add(*agents)
        
        return workflow

    @staticmethod
    async def get_workflows(skip: int = 0, limit: int = 100, name: str = "") -> List[Workflow]:
        """Get workflow list"""
        query = Workflow.all()
        if name:
            query = query.filter(name__icontains=name)
        workflows = await query.offset(skip).limit(limit).prefetch_related('nodes', 'edges', 'agents')
        return workflows

    @staticmethod
    async def get_workflow_by_id(workflow_id: int) -> Optional[Workflow]:
        """Get workflow by ID"""
        try:
            workflow = await Workflow.get(id=workflow_id).prefetch_related('nodes', 'edges', 'agents')
            return workflow
        except DoesNotExist:
            return None

    @staticmethod
    async def update_workflow(workflow_id: int, workflow_data: WorkflowUpdate) -> Optional[Workflow]:
        """Update workflow"""
        workflow = await WorkflowService.get_workflow_by_id(workflow_id)
        if not workflow:
            return None

        update_data = workflow_data.model_dump(exclude_unset=True)
        agent_ids = update_data.pop('agent_ids', None)
        
        await workflow.update_from_dict(update_data)
        await workflow.save()
        
        # Update agents
        if agent_ids is not None:
            await workflow.agents.clear()
            if agent_ids:
                agents = await Agent.filter(id__in=agent_ids).all()
                await workflow.agents.add(*agents)
        
        return workflow

    @staticmethod
    async def delete_workflow(workflow_id: int) -> bool:
        """Delete workflow"""
        workflow = await WorkflowService.get_workflow_by_id(workflow_id)
        if not workflow:
            return False

        # Delete associated nodes and edges
        await WorkflowNode.filter(workflow=workflow).delete()
        await WorkflowEdge.filter(workflow=workflow).delete()
        
        await workflow.delete()
        return True

    @staticmethod
    async def create_workflow_node(workflow_id: int, node_data: Dict[str, Any]) -> WorkflowNode:
        """Create workflow node"""
        workflow = await WorkflowService.get_workflow_by_id(workflow_id)
        if not workflow:
            raise ValueError("Workflow not found")
        
        node = await WorkflowNode.create(
            workflow=workflow,
            name=node_data['name'],
            type=node_data['type'],
            config=node_data['config'],
            position=node_data['position'],
            agent_id=node_data.get('agent_id'),
            skill_id=node_data.get('skill_id')
        )
        
        return node

    @staticmethod
    async def create_workflow_edge(workflow_id: int, edge_data: Dict[str, Any]) -> WorkflowEdge:
        """Create workflow edge"""
        workflow = await WorkflowService.get_workflow_by_id(workflow_id)
        if not workflow:
            raise ValueError("Workflow not found")
        
        source_node = await WorkflowNode.get(id=edge_data['source_node_id'])
        target_node = await WorkflowNode.get(id=edge_data['target_node_id'])
        
        edge = await WorkflowEdge.create(
            workflow=workflow,
            source_node=source_node,
            target_node=target_node,
            condition=edge_data.get('condition'),
            label=edge_data.get('label')
        )
        
        return edge

    @staticmethod
    async def execute_workflow(workflow_id: int, input_data: Dict[str, Any]) -> WorkflowExecution:
        """Execute workflow"""
        workflow = await WorkflowService.get_workflow_by_id(workflow_id)
        if not workflow:
            raise ValueError("Workflow not found")
        
        # Create execution record
        execution = await WorkflowExecution.create(
            workflow=workflow,
            input_data=input_data,
            status="running"
        )
        
        try:
            # Build and execute the workflow using LangGraph
            output_data = await WorkflowService._build_and_execute_graph(workflow, input_data)
            
            # Update execution status
            from datetime import datetime
            await execution.update_from_dict({
                "status": "success",
                "output_data": output_data,
                "completed_at": datetime.now()
            })
            await execution.save()
        except Exception as e:
            # Update execution status with error
            from datetime import datetime
            await execution.update_from_dict({
                "status": "failed",
                "error_message": str(e),
                "completed_at": datetime.now()
            })
            await execution.save()
            raise
        
        return execution

    @staticmethod
    async def _build_and_execute_graph(workflow: Workflow, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build and execute workflow graph using LangGraph"""
        if not LANGGRAPH_AVAILABLE:
            # LangGraph is not available, return a mock response
            return {
                "message": "LangGraph is not available",
                "input_data": input_data,
                "workflow_name": workflow.name
            }
        
        # Create a StateGraph
        graph = StateGraph(Dict[str, Any])
        
        # Add nodes to the graph
        for node in workflow.nodes:
            if node.type == "agent":
                # Add agent node
                agent = await node.agent
                if agent:
                    graph.add_node(node.name, lambda state: WorkflowService._execute_agent_node(agent, state))
            elif node.type == "skill":
                # Add skill node
                skill = await node.skill
                if skill:
                    graph.add_node(node.name, lambda state: WorkflowService._execute_skill_node(skill, state))
            elif node.type == "decision":
                # Add decision node
                graph.add_node(node.name, lambda state: WorkflowService._execute_decision_node(node, state))
            elif node.type == "fork":
                # Add fork node
                graph.add_node(node.name, lambda state: WorkflowService._execute_fork_node(node, state))
            elif node.type == "join":
                # Add join node
                graph.add_node(node.name, lambda state: WorkflowService._execute_join_node(node, state))
        
        # Add edges to the graph
        for edge in workflow.edges:
            source_node = await edge.source_node
            target_node = await edge.target_node
            if edge.condition:
                # Add conditional edge
                graph.add_conditional_edges(
                    source_node.name,
                    lambda state: WorkflowService._evaluate_condition(edge.condition, state),
                    {target_node.name: target_node.name}
                )
            else:
                # Add unconditional edge
                graph.add_edge(source_node.name, target_node.name)
        
        # Set entry point
        entry_node = next((node for node in workflow.nodes if node.position.get('x') < 100), None)
        if entry_node:
            graph.set_entry_point(entry_node.name)
        
        # Compile the graph
        compiled_graph = graph.compile()
        
        # Execute the graph
        result = await compiled_graph.ainvoke(input_data)
        
        return result

    @staticmethod
    async def _execute_agent_node(agent: Agent, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent node"""
        # Here you would implement the agent execution logic
        # This could involve calling the agent's API or using LangChain
        print(f"Executing agent: {agent.name}")
        
        # Simulate agent execution
        state[f"agent_{agent.id}_output"] = f"Output from agent {agent.name}"
        return state

    @staticmethod
    async def _execute_skill_node(skill: Skill, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute skill node"""
        # Here you would implement the skill execution logic
        # This could involve running the skill's implementation code
        print(f"Executing skill: {skill.name}")
        
        # Simulate skill execution
        state[f"skill_{skill.id}_output"] = f"Output from skill {skill.name}"
        return state

    @staticmethod
    async def _execute_decision_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute decision node"""
        # Here you would implement the decision logic
        print(f"Executing decision node: {node.name}")
        
        # Simulate decision
        state[f"decision_{node.id}_output"] = "Decision made"
        return state

    @staticmethod
    async def _execute_fork_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute fork node"""
        # Here you would implement the fork logic
        print(f"Executing fork node: {node.name}")
        
        # Simulate fork
        state[f"fork_{node.id}_output"] = "Fork executed"
        return state

    @staticmethod
    async def _execute_join_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute join node"""
        # Here you would implement the join logic
        print(f"Executing join node: {node.name}")
        
        # Simulate join
        state[f"join_{node.id}_output"] = "Join executed"
        return state

    @staticmethod
    async def _evaluate_condition(condition: str, state: Dict[str, Any]) -> str:
        """Evaluate condition"""
        # Here you would implement condition evaluation
        # This could involve evaluating the condition against the state
        print(f"Evaluating condition: {condition}")
        
        # Simulate condition evaluation
        return "true"
