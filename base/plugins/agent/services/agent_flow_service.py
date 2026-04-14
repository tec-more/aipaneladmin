import json
from typing import Dict, List, Any, Optional
from tortoise.transactions import atomic
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.models.workflow import Workflow, WorkflowExecution
from base.plugins.agent.models.dialog_flow import DialogFlow, DialogFlowExecution
from base.plugins.agent.services.agent_service import AgentService
from base.plugins.agent.services.workflow_service import WorkflowService
from base.plugins.agent.services.dialog_flow_service import DialogFlowService
from base.plugins.agent.services.memory_service import MemoryService
from base.plugins.llm.services.chat_service import ChatService


class AgentFlowService:
    """智能体流程图执行服务"""
    
    # 最大递归深度
    MAX_RECURSION_DEPTH = 10
    
    @staticmethod
    @atomic()
    async def execute_agent_flow(
        agent_id: int,
        input_data: Dict[str, Any],
        user_id: Optional[int] = None,
        recursion_depth: int = 0,
        executed_agent_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        执行智能体流程图
        
        Args:
            agent_id: 智能体ID
            input_data: 输入数据
            user_id: 用户ID（可选）
            recursion_depth: 当前递归深度
            executed_agent_ids: 已执行的智能体ID列表（用于循环检测）
            
        Returns:
            执行结果
        """
        try:
            # 初始化已执行智能体列表
            if executed_agent_ids is None:
                executed_agent_ids = []
            
            # 检查递归深度
            if recursion_depth >= AgentFlowService.MAX_RECURSION_DEPTH:
                return {
                    "success": False,
                    "message": f"递归深度超过限制 ({AgentFlowService.MAX_RECURSION_DEPTH})，防止无限递归"
                }
            
            # 检查循环调用
            if agent_id in executed_agent_ids:
                return {
                    "success": False,
                    "message": f"检测到循环调用：智能体 {agent_id} 已经在当前执行链中"
                }
            
            # 添加当前智能体到已执行列表
            executed_agent_ids.append(agent_id)
            
            agent = await Agent.get_or_none(id=agent_id)
            if not agent:
                return {"success": False, "message": "智能体不存在"}
            
            # 检查是否有流程图配置
            if not agent.config or "flow_data" not in agent.config:
                return {
                    "success": False, 
                    "message": "智能体没有配置流程图"
                }
            
            flow_data = agent.config["flow_data"]
            nodes = flow_data.get("nodes", [])
            edges = flow_data.get("edges", [])
            
            if not nodes or not edges:
                return {
                    "success": False, 
                    "message": "流程图配置不完整"
                }
            
            # 构建流程图执行上下文
            context = {
                "input": input_data,
                "output": {},
                "variables": {},
                "node_results": {},
                "agent_id": agent_id,
                "user_id": user_id,
                "recursion_depth": recursion_depth,
                "executed_agent_ids": executed_agent_ids
            }
            
            # 查找开始节点
            start_node = None
            for node in nodes:
                if node.get("type") == "start":
                    start_node = node
                    break
            
            if not start_node:
                return {
                    "success": False, 
                    "message": "流程图缺少开始节点"
                }
            
            # 执行流程图
            result = await AgentFlowService._execute_flow_nodes(
                start_node,
                nodes,
                edges,
                context
            )
            
            return result
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "message": f"执行流程图失败: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    @staticmethod
    async def _execute_flow_nodes(
        current_node: Dict[str, Any],
        all_nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        递归执行流程图节点
        
        Args:
            current_node: 当前节点
            all_nodes: 所有节点
            edges: 所有边
            context: 执行上下文
            
        Returns:
            执行结果
        """
        node_id = current_node.get("id")
        node_type = current_node.get("type")
        node_data = current_node.get("data", {})
        
        try:
            # 执行当前节点
            node_result = await AgentFlowService._execute_single_node(
                current_node,
                context
            )
            
            # 保存节点执行结果
            context["node_results"][node_id] = node_result
            
            # 如果是结束节点，直接返回
            if node_type == "end":
                return {
                    "success": True,
                    "result": context.get("output", {}),
                    "node_results": context["node_results"]
                }
            
            # 如果是输出节点，设置输出后继续
            if node_type == "output":
                output_value = node_result.get("result", "")
                context["output"]["final_output"] = output_value
            
            # 查找下一个节点
            next_nodes = AgentFlowService._get_next_nodes(
                current_node,
                all_nodes,
                edges
            )
            
            if not next_nodes:
                # 没有下一个节点，返回当前结果
                return {
                    "success": True,
                    "result": context.get("output", {}),
                    "node_results": context["node_results"]
                }
            
            # 执行下一个节点（目前只支持单分支，后续可扩展多分支）
            return await AgentFlowService._execute_flow_nodes(
                next_nodes[0],
                all_nodes,
                edges,
                context
            )
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "message": f"节点执行失败 [{node_type}]: {str(e)}",
                "traceback": traceback.format_exc(),
                "node_id": node_id,
                "node_results": context.get("node_results", {})
            }
    
    @staticmethod
    async def _execute_single_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单个节点
        
        Args:
            node: 节点信息
            context: 执行上下文
            
        Returns:
            节点执行结果
        """
        node_type = node.get("type")
        node_data = node.get("data", {})
        
        # 根据节点类型执行不同的逻辑
        if node_type == "start":
            return await AgentFlowService._execute_start_node(node, context)
        elif node_type == "end":
            return await AgentFlowService._execute_end_node(node, context)
        elif node_type == "input":
            return await AgentFlowService._execute_input_node(node, context)
        elif node_type == "output":
            return await AgentFlowService._execute_output_node(node, context)
        elif node_type == "agent":
            return await AgentFlowService._execute_agent_node(node, context)
        elif node_type == "workflow":
            return await AgentFlowService._execute_workflow_node(node, context)
        elif node_type == "dialog_flow":
            return await AgentFlowService._execute_dialog_flow_node(node, context)
        elif node_type == "llm":
            return await AgentFlowService._execute_llm_node(node, context)
        elif node_type == "code":
            return await AgentFlowService._execute_code_node(node, context)
        elif node_type == "template":
            return await AgentFlowService._execute_template_node(node, context)
        elif node_type == "http":
            return await AgentFlowService._execute_http_node(node, context)
        elif node_type == "knowledge_retrieval":
            return await AgentFlowService._execute_knowledge_retrieval_node(node, context)
        else:
            return {
                "success": False,
                "message": f"不支持的节点类型: {node_type}"
            }
    
    @staticmethod
    async def _execute_start_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行开始节点"""
        return {
            "success": True,
            "result": "开始执行"
        }
    
    @staticmethod
    async def _execute_end_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行结束节点"""
        return {
            "success": True,
            "result": "执行结束"
        }
    
    @staticmethod
    async def _execute_input_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行输入节点"""
        input_text = context.get("input", {}).get("text", "")
        context["variables"]["input_text"] = input_text
        return {
            "success": True,
            "result": input_text
        }
    
    @staticmethod
    async def _execute_output_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行输出节点"""
        # 获取最后一个节点的结果作为输出
        last_result = ""
        for node_id, result in context.get("node_results", {}).items():
            if result.get("success"):
                last_result = result.get("result", "")
        
        return {
            "success": True,
            "result": last_result
        }
    
    @staticmethod
    async def _execute_agent_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行智能体节点 - 多智能体协同"""
        node_data = node.get("data", {})
        target_agent_id = node_data.get("agent_id")
        
        if not target_agent_id:
            return {
                "success": False,
                "message": "智能体节点未配置目标智能体"
            }
        
        # 获取输入文本
        input_text = context.get("variables", {}).get("input_text", "")
        if not input_text:
            input_text = context.get("input", {}).get("text", "")
        
        # 执行目标智能体
        result = await AgentService.execute_agent(
            agent_id=target_agent_id,
            input_data={
                "text": input_text,
                "parameters": context.get("input", {}).get("parameters", {})
            },
            user_id=context.get("user_id"),
            recursion_depth=context.get("recursion_depth", 0) + 1,
            executed_agent_ids=context.get("executed_agent_ids", []).copy()
        )
        
        # 将结果保存到变量中
        if result.get("success"):
            context["variables"][f"agent_{target_agent_id}_result"] = result.get("result", "")
        
        return result
    
    @staticmethod
    async def _execute_workflow_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行工作流节点"""
        node_data = node.get("data", {})
        workflow_id = node_data.get("workflowId")
        
        if not workflow_id:
            return {
                "success": False,
                "message": "工作流节点未配置工作流"
            }
        
        # 构建工作流输入
        input_text = context.get("variables", {}).get("input_text", "")
        if not input_text:
            input_text = context.get("input", {}).get("text", "")
        
        workflow_input = {
            "text": input_text,
            "input_text": input_text,
            **context.get("input", {})
        }
        
        # 执行工作流
        try:
            workflow_execution = await WorkflowService.execute_workflow(
                workflow_id=workflow_id,
                input_data=workflow_input
            )
            
            result = {
                "success": True,
                "result": workflow_execution.output_data,
                "workflow_execution_id": workflow_execution.id
            }
            
            # 保存结果到变量
            context["variables"][f"workflow_{workflow_id}_result"] = workflow_execution.output_data
            
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"执行工作流失败: {str(e)}"
            }
    
    @staticmethod
    async def _execute_dialog_flow_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行对话流节点"""
        node_data = node.get("data", {})
        dialog_flow_id = node_data.get("dialogFlowId")
        
        if not dialog_flow_id:
            return {
                "success": False,
                "message": "对话流节点未配置对话流"
            }
        
        # 构建对话流输入
        input_text = context.get("variables", {}).get("input_text", "")
        if not input_text:
            input_text = context.get("input", {}).get("text", "")
        
        dialog_flow_input = {
            "text": input_text,
            "input_text": input_text,
            **context.get("input", {})
        }
        
        # 执行对话流
        try:
            dialog_flow_result = await DialogFlowService.execute_dialog_flow(
                dialog_flow_id=dialog_flow_id,
                input_data=dialog_flow_input,
                agent_id=context.get("agent_id"),
                user_id=context.get("user_id")
            )
            
            result = {
                "success": dialog_flow_result.status == "completed",
                "result": dialog_flow_result.output_data or "",
                "execution_id": dialog_flow_result.id,
                "status": dialog_flow_result.status
            }
            
            if dialog_flow_result.error_message:
                result["message"] = dialog_flow_result.error_message
                result["success"] = False
            
            # 保存结果到变量
            if result.get("success"):
                context["variables"][f"dialog_flow_{dialog_flow_id}_result"] = result.get("result", "")
            
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"执行对话流失败: {str(e)}"
            }
    
    @staticmethod
    async def _execute_llm_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行大模型节点"""
        agent_id = context.get("agent_id")
        agent = await Agent.get_or_none(id=agent_id)
        
        if not agent or not agent.llm_model:
            return {
                "success": False,
                "message": "智能体未配置大模型"
            }
        
        llm_model = await agent.llm_model
        provider = await llm_model.provider
        
        # 获取 API Key
        from base.plugins.llm.models.api_key import LLMApiKey
        api_key = await LLMApiKey.filter(
            provider_id=provider.id,
            status="active"
        ).first()
        
        if not api_key:
            return {
                "success": False,
                "message": "未找到有效的API密钥"
            }
        
        # 获取输入文本
        input_text = context.get("variables", {}).get("input_text", "")
        if not input_text:
            input_text = context.get("input", {}).get("text", "")
        
        # 构建消息
        messages = []
        if agent.system_prompt:
            messages.append({"role": "system", "content": agent.system_prompt})
        messages.append({"role": "user", "content": input_text})
        
        # 获取参数
        temperature = context.get("input", {}).get("parameters", {}).get("temperature", 0.7)
        max_tokens = context.get("input", {}).get("parameters", {}).get("max_tokens", 2048)
        
        # 调用 LLM
        try:
            service = await ChatService.get_provider_service(
                provider.name_en,
                api_key.api_key,
                api_key.endpoint_url or provider.endpoint_url,
                api_key.api_secret
            )
            
            response = await service.chat(
                messages,
                llm_model.model_id,
                temperature,
                max_tokens
            )
            
            if response and response.get("success"):
                result = {
                    "success": True,
                    "result": response.get("text", ""),
                    "usage": response.get("usage", {})
                }
                
                # 保存结果到变量
                context["variables"]["llm_result"] = response.get("text", "")
                
                return result
            else:
                return {
                    "success": False,
                    "message": response.get("error", "LLM调用失败")
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"调用大模型失败: {str(e)}"
            }
    
    @staticmethod
    async def _execute_code_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行代码节点（简化版）"""
        node_data = node.get("data", {})
        code = node_data.get("code", "")
        
        if not code:
            return {
                "success": False,
                "message": "代码节点未配置代码"
            }
        
        # 注意：实际生产环境中需要安全的代码执行沙箱
        # 这里只返回一个占位符实现
        try:
            # 获取变量
            variables = context.get("variables", {})
            
            # 简单的变量替换
            result = code
            for key, value in variables.items():
                result = result.replace(f"${{{key}}}", str(value))
            
            # 保存结果到变量
            context["variables"]["code_result"] = result
            
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"执行代码失败: {str(e)}"
            }
    
    @staticmethod
    async def _execute_template_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行模板节点"""
        node_data = node.get("data", {})
        template = node_data.get("template", "")
        
        if not template:
            return {
                "success": False,
                "message": "模板节点未配置模板"
            }
        
        try:
            # 获取变量
            variables = context.get("variables", {})
            
            # 变量替换
            result = template
            for key, value in variables.items():
                result = result.replace(f"${{{key}}}", str(value))
            
            # 保存结果到变量
            context["variables"]["template_result"] = result
            
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"执行模板失败: {str(e)}"
            }
    
    @staticmethod
    async def _execute_http_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行HTTP请求节点（简化版）"""
        node_data = node.get("data", {})
        url = node_data.get("url", "")
        
        if not url:
            return {
                "success": False,
                "message": "HTTP节点未配置URL"
            }
        
        # 注意：实际生产环境中需要更完善的HTTP请求处理
        try:
            import httpx
            
            method = node_data.get("method", "GET")
            headers = node_data.get("headers", {})
            body = node_data.get("body", "")
            
            # 变量替换
            variables = context.get("variables", {})
            for key, value in variables.items():
                url = url.replace(f"${{{key}}}", str(value))
                if body:
                    body = body.replace(f"${{{key}}}", str(value))
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, content=body)
                else:
                    return {
                        "success": False,
                        "message": f"不支持的HTTP方法: {method}"
                    }
                
                result = {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "result": response.text
                }
                
                # 保存结果到变量
                context["variables"]["http_result"] = response.text
                
                return result
        except Exception as e:
            return {
                "success": False,
                "message": f"执行HTTP请求失败: {str(e)}"
            }
    
    @staticmethod
    async def _execute_knowledge_retrieval_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行知识检索节点"""
        agent_id = context.get("agent_id")
        
        # 获取输入文本
        input_text = context.get("variables", {}).get("input_text", "")
        if not input_text:
            input_text = context.get("input", {}).get("text", "")
        
        try:
            # 注意：知识检索功能需要实现文档管理模型
            # 这里暂时返回空结果，避免导入错误
            relevant_docs = []
            
            result = {
                "success": True,
                "result": relevant_docs,
                "count": len(relevant_docs),
                "message": "知识检索功能需要文档管理模型支持"
            }
            
            # 保存结果到变量
            context["variables"]["knowledge_result"] = relevant_docs
            
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"知识检索失败: {str(e)}"
            }
    
    @staticmethod
    def _get_next_nodes(
        current_node: Dict[str, Any],
        all_nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        获取下一个节点
        
        Args:
            current_node: 当前节点
            all_nodes: 所有节点
            edges: 所有边
            
        Returns:
            下一个节点列表
        """
        current_node_id = current_node.get("id")
        
        # 查找从当前节点出发的边
        outgoing_edges = [
            edge for edge in edges 
            if edge.get("source") == current_node_id
        ]
        
        # 获取目标节点ID
        target_node_ids = [edge.get("target") for edge in outgoing_edges]
        
        # 获取目标节点
        next_nodes = [
            node for node in all_nodes 
            if node.get("id") in target_node_ids
        ]
        
        return next_nodes

