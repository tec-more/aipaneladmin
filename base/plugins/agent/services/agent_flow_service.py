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
            
            # 添加调试日志
            import logging
            logging.info(f"流程图数据 - 节点数: {len(nodes)}, 边数: {len(edges)}")
            logging.info(f"流程图数据内容: {flow_data}")
            
            # 只需要有节点即可，边可以为空（单节点执行）
            if not nodes:
                return {
                    "success": False, 
                    "message": f"流程图配置不完整: 没有找到节点 (当前节点数: {len(nodes)}, 边数: {len(edges)})"
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
        import logging
        logger = logging.getLogger(__name__)
        
        node_id = current_node.get("id")
        node_type = current_node.get("type")
        node_data = current_node.get("data", {})
        
        logger.info(f"[流程执行] 开始执行节点: {node_id}, 类型: {node_type}")
        
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
                edges,
                node_result
            )
            
            if not next_nodes:
                # 没有下一个节点，返回当前结果
                return {
                    "success": True,
                    "result": context.get("output", {}),
                    "node_results": context["node_results"]
                }
            
            # 条件分支节点：根据条件选择下一个节点
            if node_type == "decision":
                # 条件分支已经在 _get_next_nodes 中处理了
                next_node = next_nodes[0] if next_nodes else None
                if next_node:
                    return await AgentFlowService._execute_flow_nodes(
                        next_node,
                        all_nodes,
                        edges,
                        context
                    )
                else:
                    return {
                        "success": False,
                        "message": "条件分支没有匹配的出口",
                        "node_results": context["node_results"]
                    }
            else:
                # 其他节点：执行第一个下一个节点
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
        elif node_type == "decision":
            return await AgentFlowService._execute_decision_node(node, context)
        elif node_type == "loop":
            return await AgentFlowService._execute_loop_node(node, context)
        elif node_type == "iteration":
            return await AgentFlowService._execute_iteration_node(node, context)
        elif node_type == "variable_aggregator":
            return await AgentFlowService._execute_variable_aggregator_node(node, context)
        elif node_type == "document_extractor":
            return await AgentFlowService._execute_document_extractor_node(node, context)
        elif node_type == "variable_assigner":
            return await AgentFlowService._execute_variable_assigner_node(node, context)
        elif node_type == "parameter_extractor":
            return await AgentFlowService._execute_parameter_extractor_node(node, context)
        elif node_type == "list_operation":
            return await AgentFlowService._execute_list_operation_node(node, context)
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
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[输出节点] 开始执行，所有节点结果: {context.get('node_results', {})}")
        
        # 获取最后一个节点的结果作为输出
        last_result = ""
        for node_id, result in context.get("node_results", {}).items():
            if result.get("success"):
                last_result = result.get("result", "")
                logger.info(f"[输出节点] 找到成功节点: {node_id}, 结果: {last_result}")
        
        logger.info(f"[输出节点] 最终输出: {last_result}")
        
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
        import logging
        logger = logging.getLogger(__name__)
        
        node_data = node.get("data", {})
        llm_id = node_data.get("llm_id")
        
        logger.info(f"[LLM节点] 开始执行，llm_id: {llm_id}")
        
        if not llm_id:
            logger.error(f"[LLM节点] 节点未配置大模型")
            return {
                "success": False,
                "message": "节点未配置大模型"
            }
        
        from base.plugins.llm.models.model import LLMModel
        llm_model = await LLMModel.get_or_none(id=llm_id).prefetch_related('provider')
        
        if not llm_model:
            logger.error(f"[LLM节点] 找不到指定的大模型，llm_id: {llm_id}")
            return {
                "success": False,
                "message": f"找不到指定的大模型 (ID: {llm_id})"
            }
        
        logger.info(f"[LLM节点] 模型信息: {llm_model.model_id}, 提供商: {llm_model.provider.name_en}")
        
        # 获取 API Key
        from base.plugins.llm.models.api_key import LLMApiKey
        api_key = await LLMApiKey.filter(
            model_id=llm_model.id,
            status="active"
        ).first()
        
        # 如果没有找到模型关联的API密钥，回退到使用provider
        if not api_key:
            api_key = await LLMApiKey.filter(
                provider_id=llm_model.provider.id,
                status="active"
            ).first()
        
        if not api_key:
            logger.error(f"[LLM节点] 未找到有效的API密钥，provider_id: {llm_model.provider.id}")
            return {
                "success": False,
                "message": "未找到有效的API密钥"
            }
        
        # 获取输入文本
        input_text = context.get("variables", {}).get("input_text", "")
        if not input_text:
            input_text = context.get("input", {}).get("text", "")
        
        logger.info(f"[LLM节点] 输入文本: {input_text}")
        
        # 构建消息 - 从智能体获取系统提示词
        agent_id = context.get("agent_id")
        agent = await Agent.get_or_none(id=agent_id)
        
        messages = []
        if agent and agent.system_prompt:
            messages.append({"role": "system", "content": agent.system_prompt})
        messages.append({"role": "user", "content": input_text})
        
        logger.info(f"[LLM节点] 构建的消息: {messages}")
        
        # 获取参数
        temperature = context.get("input", {}).get("parameters", {}).get("temperature", 0.7)
        max_tokens = context.get("input", {}).get("parameters", {}).get("max_tokens", 2048)
        
        logger.info(f"[LLM节点] 调用参数: temperature={temperature}, max_tokens={max_tokens}")
        
        # 调用 LLM
        try:
            endpoint_url = llm_model.endpoint_url or api_key.endpoint_url or llm_model.provider.official_url
            if endpoint_url:
                endpoint_url = endpoint_url.rstrip('/')
                if endpoint_url.endswith('/chat/completions'):
                    endpoint_url = endpoint_url[:-len('/chat/completions')]
            
            credentials = api_key.get_credentials()
            
            logger.info(f"[LLM节点] 获取到的 credentials:")
            logger.info(f"  provider.name_en: {llm_model.provider.name_en}")
            logger.info(f"  endpoint_url: {endpoint_url}")
            logger.info(f"  api_key: {credentials.get('api_key', '')[:8] if credentials.get('api_key') else 'None'}...")
            logger.info(f"  api_secret provided: {credentials.get('api_secret') is not None}")
            
            service = await ChatService.get_provider_service(
                llm_model.provider.name_en,
                credentials.get("api_key", ""),
                endpoint_url,
                credentials.get("api_secret", "")
            )
            
            logger.info(f"[LLM节点] 开始调用LLM API...")
            response = await service.chat(
                model=llm_model.model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            logger.info(f"[LLM节点] LLM响应: {response}")
            
            if response and "choices" in response:
                result_text = response["choices"][0]["message"]["content"]
                logger.info(f"[LLM节点] 调用成功，结果: {result_text}")
                result = {
                    "success": True,
                    "result": result_text,
                    "usage": response.get("usage", {})
                }
                
                # 保存结果到变量
                context["variables"]["llm_result"] = result_text
                
                return result
            else:
                error_msg = "LLM调用失败"
                logger.error(f"[LLM节点] 调用失败: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg
                }
        except Exception as e:
            logger.exception(f"[LLM节点] 调用异常: {str(e)}")
            import traceback
            return {
                "success": False,
                "message": f"调用大模型失败: {str(e)}",
                "traceback": traceback.format_exc()
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
        edges: List[Dict[str, Any]],
        node_result: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取下一个节点
        
        Args:
            current_node: 当前节点
            all_nodes: 所有节点
            edges: 所有边
            node_result: 当前节点的执行结果（用于条件分支）
            
        Returns:
            下一个节点列表
        """
        current_node_id = current_node.get("id")
        current_node_type = current_node.get("type")
        current_node_data = current_node.get("data", {})
        
        # 查找从当前节点出发的边
        outgoing_edges = [
            edge for edge in edges 
            if edge.get("source") == current_node_id
        ]
        
        # 如果是条件分支节点，根据条件筛选边
        if current_node_type == "decision" and node_result:
            condition_result = node_result.get("result", False)
            filtered_edges = []
            
            for edge in outgoing_edges:
                edge_data = edge.get("data", {})
                edge_condition = edge_data.get("condition", "")
                
                # 根据条件判断
                if condition_result:
                    # 条件为真，找 true 分支或无条件的边
                    if edge_condition in ["true", ""]:
                        filtered_edges.append(edge)
                else:
                    # 条件为假，找 false 分支或无条件的边
                    if edge_condition in ["false", ""]:
                        filtered_edges.append(edge)
            
            # 如果没有匹配的边，使用所有边
            if filtered_edges:
                outgoing_edges = filtered_edges
        
        # 获取目标节点ID
        target_node_ids = [edge.get("target") for edge in outgoing_edges]
        
        # 获取目标节点
        next_nodes = [
            node for node in all_nodes 
            if node.get("id") in target_node_ids
        ]
        
        return next_nodes

    @staticmethod
    async def _execute_decision_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行条件分支节点"""
        node_data = node.get("data", {})
        condition = node_data.get("condition", "")
        
        try:
            # 简单的条件表达式评估
            # 支持变量替换，例如 ${variable_name} > 10
            evaluated_condition = condition
            
            # 替换变量
            variables = context.get("variables", {})
            for key, value in variables.items():
                evaluated_condition = evaluated_condition.replace(f"${{{key}}}", str(value))
            
            # 尝试评估条件
            result = False
            try:
                # 安全评估条件（只支持简单的表达式）
                # 注意：实际生产环境应该使用更安全的评估方式
                safe_locals = {}
                safe_globals = {"__builtins__": {}}
                result = eval(evaluated_condition, safe_globals, safe_locals)
            except:
                # 如果评估失败，尝试简单的字符串匹配
                if evaluated_condition.lower() in ["true", "yes", "1", "y"]:
                    result = True
                elif evaluated_condition.lower() in ["false", "no", "0", "n"]:
                    result = False
            
            return {
                "success": True,
                "result": result,
                "condition": condition,
                "evaluated_condition": evaluated_condition
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"条件分支评估失败: {str(e)}",
                "result": False
            }

    @staticmethod
    async def _execute_loop_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行循环节点"""
        node_data = node.get("data", {})
        condition = node_data.get("condition", "")
        max_iterations = node_data.get("max_iterations", 10)
        
        try:
            iteration_count = 0
            results = []
            
            while iteration_count < max_iterations:
                # 评估条件
                evaluated_condition = condition
                variables = context.get("variables", {})
                for key, value in variables.items():
                    evaluated_condition = evaluated_condition.replace(f"${{{key}}}", str(value))
                
                # 尝试评估条件
                should_continue = False
                try:
                    safe_locals = {}
                    safe_globals = {"__builtins__": {}}
                    should_continue = eval(evaluated_condition, safe_globals, safe_locals)
                except:
                    break
                
                if not should_continue:
                    break
                
                # 执行循环体（这里简化处理，实际应该递归执行循环体节点）
                iteration_count += 1
                results.append(f"Iteration {iteration_count}")
            
            return {
                "success": True,
                "result": results,
                "iteration_count": iteration_count
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"循环执行失败: {str(e)}"
            }

    @staticmethod
    async def _execute_iteration_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行迭代节点"""
        node_data = node.get("data", {})
        collection_var = node_data.get("collection_var", "items")
        item_var = node_data.get("item_var", "item")
        
        try:
            collection = context.get("variables", {}).get(collection_var, [])
            results = []
            
            for item in collection:
                # 设置当前项到变量
                context["variables"][item_var] = item
                # 执行迭代体（这里简化处理，实际应该递归执行迭代体节点）
                results.append(item)
            
            return {
                "success": True,
                "result": results,
                "item_count": len(collection)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"迭代执行失败: {str(e)}"
            }

    @staticmethod
    async def _execute_variable_aggregator_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行变量聚合器节点"""
        node_data = node.get("data", {})
        variables = node_data.get("variables", [])
        result_var = node_data.get("result_var", "aggregated_result")
        
        try:
            aggregated = {}
            for var_name in variables:
                if var_name in context.get("variables", {}):
                    aggregated[var_name] = context["variables"][var_name]
            
            # 保存聚合结果到变量
            context["variables"][result_var] = aggregated
            
            return {
                "success": True,
                "result": aggregated,
                "variables": variables
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"变量聚合失败: {str(e)}"
            }

    @staticmethod
    async def _execute_document_extractor_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行文档提取器节点"""
        node_data = node.get("data", {})
        source_var = node_data.get("source_var", "input_text")
        extract_var = node_data.get("extract_var", "extracted_content")
        
        try:
            source_content = context.get("variables", {}).get(source_var, "")
            if not source_content:
                source_content = context.get("input", {}).get("text", "")
            
            # 简单的文档提取（实际应该使用更复杂的提取逻辑）
            extracted = {
                "content": source_content,
                "length": len(source_content),
                "words": len(source_content.split())
            }
            
            # 保存提取结果到变量
            context["variables"][extract_var] = extracted
            
            return {
                "success": True,
                "result": extracted
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"文档提取失败: {str(e)}"
            }

    @staticmethod
    async def _execute_variable_assigner_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行变量赋值节点"""
        node_data = node.get("data", {})
        variable_name = node_data.get("variable_name", "")
        variable_value = node_data.get("variable_value", "")
        
        try:
            if not variable_name:
                return {
                    "success": False,
                    "message": "变量名不能为空"
                }
            
            # 替换变量
            variables = context.get("variables", {})
            value = variable_value
            for key, val in variables.items():
                value = value.replace(f"${{{key}}}", str(val))
            
            # 保存到变量
            context["variables"][variable_name] = value
            
            return {
                "success": True,
                "result": value,
                "variable_name": variable_name
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"变量赋值失败: {str(e)}"
            }

    @staticmethod
    async def _execute_parameter_extractor_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行参数提取器节点"""
        node_data = node.get("data", {})
        parameters = node_data.get("parameters", [])
        
        try:
            extracted_params = {}
            input_data = context.get("input", {})
            variables = context.get("variables", {})
            
            for param in parameters:
                param_name = param.get("name", "")
                param_source = param.get("source", "input")
                param_key = param.get("key", "")
                
                if param_name and param_key:
                    if param_source == "input":
                        if param_key in input_data:
                            extracted_params[param_name] = input_data[param_key]
                    elif param_source == "variables":
                        if param_key in variables:
                            extracted_params[param_name] = variables[param_key]
            
            # 保存提取的参数到变量
            context["variables"]["extracted_parameters"] = extracted_params
            
            return {
                "success": True,
                "result": extracted_params,
                "parameters": parameters
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"参数提取失败: {str(e)}"
            }

    @staticmethod
    async def _execute_list_operation_node(
        node: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行列表操作节点"""
        node_data = node.get("data", {})
        operation = node_data.get("operation", "")
        list_var = node_data.get("list_var", "items")
        result_var = node_data.get("result_var", "list_result")
        
        try:
            target_list = context.get("variables", {}).get(list_var, [])
            result = []
            
            if operation == "filter":
                # 过滤操作
                filter_expr = node_data.get("filter_expr", "")
                for item in target_list:
                    try:
                        if eval(filter_expr, {}, {"item": item}):
                            result.append(item)
                    except:
                        pass
            elif operation == "map":
                # 映射操作
                map_expr = node_data.get("map_expr", "item")
                for item in target_list:
                    try:
                        mapped = eval(map_expr, {}, {"item": item})
                        result.append(mapped)
                    except:
                        result.append(item)
            elif operation == "sort":
                # 排序操作
                sort_key = node_data.get("sort_key", "")
                if sort_key:
                    result = sorted(target_list, key=lambda x: eval(sort_key, {}, {"item": x}))
                else:
                    result = sorted(target_list)
            elif operation == "limit":
                # 限制操作
                limit = node_data.get("limit", 10)
                result = target_list[:limit]
            elif operation == "reverse":
                # 反转操作
                result = target_list[::-1]
            else:
                # 默认为复制
                result = target_list.copy()
            
            # 保存结果到变量
            context["variables"][result_var] = result
            
            return {
                "success": True,
                "result": result,
                "operation": operation
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"列表操作失败: {str(e)}"
            }

