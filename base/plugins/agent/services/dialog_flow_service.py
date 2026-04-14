from typing import List, Optional, Dict, Any
from datetime import datetime
from base.plugins.agent.models.dialog_flow import DialogFlow, DialogFlowNode, DialogFlowEdge, DialogFlowExecution
from base.plugins.agent.schemas.dialog_flow import (
    DialogFlowCreate, DialogFlowUpdate, DialogFlowResponse,
    DialogFlowNodeCreate, DialogFlowNodeUpdate, DialogFlowNodeResponse,
    DialogFlowEdgeCreate, DialogFlowEdgeUpdate, DialogFlowEdgeResponse,
    DialogFlowExecutionCreate, DialogFlowExecutionResponse
)


class DialogFlowService:
    """对话流服务"""
    
    @staticmethod
    async def create_dialog_flow(data: DialogFlowCreate) -> DialogFlowResponse:
        """创建对话流"""
        dialog_flow = await DialogFlow.create(**data.dict())
        return DialogFlowResponse.from_orm(dialog_flow)
    
    @staticmethod
    async def get_dialog_flow(dialog_flow_id: int) -> Optional[DialogFlowResponse]:
        """获取对话流"""
        dialog_flow = await DialogFlow.get_or_none(id=dialog_flow_id)
        if not dialog_flow:
            return None
        return DialogFlowResponse.from_orm(dialog_flow)
    
    @staticmethod
    async def list_dialog_flows(agent_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[DialogFlowResponse]:
        """列出对话流"""
        query = DialogFlow.all()
        if agent_id:
            query = query.filter(agent__id=agent_id)
        dialog_flows = await query.offset(skip).limit(limit).all()
        return [DialogFlowResponse.from_orm(df) for df in dialog_flows]
    
    @staticmethod
    async def update_dialog_flow(dialog_flow_id: int, data: DialogFlowUpdate) -> Optional[DialogFlowResponse]:
        """更新对话流"""
        dialog_flow = await DialogFlow.get_or_none(id=dialog_flow_id)
        if not dialog_flow:
            return None
        
        update_data = data.dict(exclude_unset=True)
        await dialog_flow.update_from_dict(update_data)
        await dialog_flow.save()
        
        return DialogFlowResponse.from_orm(dialog_flow)
    
    @staticmethod
    async def delete_dialog_flow(dialog_flow_id: int) -> bool:
        """删除对话流"""
        dialog_flow = await DialogFlow.get_or_none(id=dialog_flow_id)
        if not dialog_flow:
            return False
        
        # 删除相关的节点和边
        await DialogFlowNode.filter(dialog_flow_id=dialog_flow_id).delete()
        await DialogFlowEdge.filter(dialog_flow_id=dialog_flow_id).delete()
        
        # 删除对话流
        await dialog_flow.delete()
        return True
    
    @staticmethod
    async def create_node(data: DialogFlowNodeCreate) -> DialogFlowNodeResponse:
        """创建对话流节点"""
        node = await DialogFlowNode.create(**data.dict())
        return DialogFlowNodeResponse.from_orm(node)
    
    @staticmethod
    async def get_node(node_id: int) -> Optional[DialogFlowNodeResponse]:
        """获取对话流节点"""
        node = await DialogFlowNode.get_or_none(id=node_id)
        if not node:
            return None
        return DialogFlowNodeResponse.from_orm(node)
    
    @staticmethod
    async def list_nodes(dialog_flow_id: int) -> List[DialogFlowNodeResponse]:
        """列出对话流节点"""
        nodes = await DialogFlowNode.filter(dialog_flow_id=dialog_flow_id).all()
        return [DialogFlowNodeResponse.from_orm(node) for node in nodes]
    
    @staticmethod
    async def update_node(node_id: int, data: DialogFlowNodeUpdate) -> Optional[DialogFlowNodeResponse]:
        """更新对话流节点"""
        node = await DialogFlowNode.get_or_none(id=node_id)
        if not node:
            return None
        
        update_data = data.dict(exclude_unset=True)
        await node.update_from_dict(update_data)
        await node.save()
        
        return DialogFlowNodeResponse.from_orm(node)
    
    @staticmethod
    async def delete_node(node_id: int) -> bool:
        """删除对话流节点"""
        node = await DialogFlowNode.get_or_none(id=node_id)
        if not node:
            return False
        
        # 删除相关的边
        await DialogFlowEdge.filter(source_node_id=node_id).delete()
        await DialogFlowEdge.filter(target_node_id=node_id).delete()
        
        # 删除节点
        await node.delete()
        return True
    
    @staticmethod
    async def create_edge(data: DialogFlowEdgeCreate) -> DialogFlowEdgeResponse:
        """创建对话流边"""
        edge = await DialogFlowEdge.create(**data.dict())
        return DialogFlowEdgeResponse.from_orm(edge)
    
    @staticmethod
    async def get_edge(edge_id: int) -> Optional[DialogFlowEdgeResponse]:
        """获取对话流边"""
        edge = await DialogFlowEdge.get_or_none(id=edge_id)
        if not edge:
            return None
        return DialogFlowEdgeResponse.from_orm(edge)
    
    @staticmethod
    async def list_edges(dialog_flow_id: int) -> List[DialogFlowEdgeResponse]:
        """列出对话流边"""
        edges = await DialogFlowEdge.filter(dialog_flow_id=dialog_flow_id).all()
        return [DialogFlowEdgeResponse.from_orm(edge) for edge in edges]
    
    @staticmethod
    async def update_edge(edge_id: int, data: DialogFlowEdgeUpdate) -> Optional[DialogFlowEdgeResponse]:
        """更新对话流边"""
        edge = await DialogFlowEdge.get_or_none(id=edge_id)
        if not edge:
            return None
        
        update_data = data.dict(exclude_unset=True)
        await edge.update_from_dict(update_data)
        await edge.save()
        
        return DialogFlowEdgeResponse.from_orm(edge)
    
    @staticmethod
    async def delete_edge(edge_id: int) -> bool:
        """删除对话流边"""
        edge = await DialogFlowEdge.get_or_none(id=edge_id)
        if not edge:
            return False
        
        await edge.delete()
        return True
    
    @staticmethod
    async def execute_dialog_flow(*args, **kwargs) -> DialogFlowExecutionResponse:
        """执行对话流"""
        # 向后兼容：支持旧的 DialogFlowExecutionCreate 参数格式
        if len(args) == 1 and hasattr(args[0], 'dialog_flow_id'):
            data = args[0]
            dialog_flow_id = data.dialog_flow_id
            input_data = data.input_data
            agent_id = data.agent_id
            user_id = data.user_id
        else:
            # 新的参数格式
            dialog_flow_id = kwargs.get('dialog_flow_id') or (args[0] if args else None)
            input_data = kwargs.get('input_data') or (args[1] if len(args) > 1 else None)
            agent_id = kwargs.get('agent_id') or (args[2] if len(args) > 2 else None)
            user_id = kwargs.get('user_id') or (args[3] if len(args) > 3 else None)
        
        # 创建执行记录
        execution_data = {
            "dialog_flow_id": dialog_flow_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "input_data": input_data or {}
        }
        execution = await DialogFlowExecution.create(**execution_data)
        
        try:
            # 这里实现对话流的执行逻辑
            # 1. 获取对话流信息
            dialog_flow = await DialogFlow.get_or_none(id=dialog_flow_id)
            if not dialog_flow:
                raise ValueError("对话流不存在")
            
            # 2. 执行对话流
            # 这里是简化的实现，实际需要根据对话流的结构进行执行
            execution_path = []
            output_data = {}
            
            # 3. 更新执行状态
            execution.status = "completed"
            execution.execution_path = execution_path
            execution.output_data = output_data
            execution.completed_at = datetime.utcnow()
            await execution.save()
            
        except Exception as e:
            # 更新错误状态
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            await execution.save()
        
        return DialogFlowExecutionResponse.from_orm(execution)
    
    @staticmethod
    async def get_execution(execution_id: int) -> Optional[DialogFlowExecutionResponse]:
        """获取对话流执行记录"""
        execution = await DialogFlowExecution.get_or_none(id=execution_id)
        if not execution:
            return None
        return DialogFlowExecutionResponse.from_orm(execution)
    
    @staticmethod
    async def list_executions(dialog_flow_id: Optional[int] = None, agent_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[DialogFlowExecutionResponse]:
        """列出对话流执行记录"""
        query = DialogFlowExecution.all()
        if dialog_flow_id:
            query = query.filter(dialog_flow_id=dialog_flow_id)
        if agent_id:
            query = query.filter(agent_id=agent_id)
        
        executions = await query.order_by("-started_at").offset(skip).limit(limit).all()
        return [DialogFlowExecutionResponse.from_orm(execution) for execution in executions]
