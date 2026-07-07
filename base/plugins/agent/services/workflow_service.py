"""
Workflow service
"""
from typing import List, Optional, Dict, Any
from tortoise.exceptions import DoesNotExist
from base.plugins.agent.models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowExecution
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.models.skill import Skill
from base.plugins.llm.models.model import LLMModel
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

# Try to import HTTP libraries
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Try to import code execution libraries
try:
    import json
    import re
    JSON_AVAILABLE = True
except ImportError:
    JSON_AVAILABLE = False


class WorkflowService:
    model = "workflow"
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
        return workflow

    @staticmethod
    async def get_workflows(skip: int = 0, limit: int = 100, name: str = "", status: str = "") -> List[Workflow]:
        """Get workflow list"""
        query = Workflow.all()
        if name:
            query = query.filter(name__icontains=name)
        if status:
            query = query.filter(status=status)
        workflows = await query.offset(skip).limit(limit).prefetch_related('nodes', 'edges')
        return workflows

    @staticmethod
    async def get_workflow_by_id(workflow_id: int) -> Optional[Workflow]:
        """Get workflow by ID"""
        try:
            workflow = await Workflow.get(id=workflow_id).prefetch_related('nodes', 'edges')
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
        
        await workflow.update_from_dict(update_data)
        await workflow.save()
        
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
    async def import_workflow(import_data: dict) -> Workflow:
        """
        导入工作流完整配置
        支持的格式：
        {
          "workflow": { ... },
          "nodes": [...],
          "edges": [...]
        }
        或直接传入 workflow 配置
        """
        workflow_data = import_data.get('workflow') or import_data

        definition = workflow_data.get('definition', {'nodes': [], 'edges': []})
        
        if not definition or 'nodes' not in definition:
            definition = {
                'nodes': workflow_data.get('nodes', []),
                'edges': workflow_data.get('edges', [])
            }

        workflow = await Workflow.create(
            name=workflow_data.get('name', '导入的工作流'),
            description=workflow_data.get('description', ''),
            status=workflow_data.get('status', 'draft'),
            definition=definition
        )

        return workflow

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
    async def get_all_workflow_executions(skip: int = 0, limit: int = 100, status: str = "") -> List[WorkflowExecution]:
        """Get all workflow executions"""
        query = WorkflowExecution.all()
        
        if status:
            query = query.filter(status=status)
        
        executions = await query.offset(skip).limit(limit).order_by("-started_at")
        return executions

    @staticmethod
    async def get_workflow_executions(workflow_id: int, skip: int = 0, limit: int = 100, status: str = "") -> List[WorkflowExecution]:
        """Get workflow executions"""
        query = WorkflowExecution.filter(workflow_id=workflow_id)
        
        if status:
            query = query.filter(status=status)
        
        executions = await query.offset(skip).limit(limit).order_by("-started_at")
        return executions

    @staticmethod
    async def get_workflow_execution_by_id(execution_id: int) -> Optional[WorkflowExecution]:
        """Get workflow execution by ID"""
        try:
            return await WorkflowExecution.get(id=execution_id)
        except DoesNotExist:
            return None

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
            elif node.type == "llm":
                # Add LLM node
                llm = await node.llm
                if llm:
                    graph.add_node(node.name, lambda state: WorkflowService._execute_llm_node(llm, state))
            elif node.type == "decision":
                # Add decision node
                graph.add_node(node.name, lambda state: WorkflowService._execute_decision_node(node, state))
            elif node.type == "fork":
                # Add fork node
                graph.add_node(node.name, lambda state: WorkflowService._execute_fork_node(node, state))
            elif node.type == "join":
                # Add join node
                graph.add_node(node.name, lambda state: WorkflowService._execute_join_node(node, state))
            elif node.type == "iteration":
                # Add iteration node
                graph.add_node(node.name, lambda state: WorkflowService._execute_iteration_node(node, state))
            elif node.type == "code":
                # Add code execution node (Dify style)
                graph.add_node(node.name, lambda state: WorkflowService._execute_code_node(node, state))
            elif node.type == "template":
                # Add template node (Dify style)
                graph.add_node(node.name, lambda state: WorkflowService._execute_template_node(node, state))
            elif node.type == "variable_aggregator":
                # Add variable aggregator node (Dify style)
                graph.add_node(node.name, lambda state: WorkflowService._execute_variable_aggregator_node(node, state))
            elif node.type == "document_extractor":
                # Add document extractor node (Dify style)
                graph.add_node(node.name, lambda state: WorkflowService._execute_document_extractor_node(node, state))
            elif node.type == "variable_assigner":
                # Add variable assigner node (Dify style)
                graph.add_node(node.name, lambda state: WorkflowService._execute_variable_assigner_node(node, state))
            elif node.type == "parameter_extractor":
                # Add parameter extractor node (Dify style)
                graph.add_node(node.name, lambda state: WorkflowService._execute_parameter_extractor_node(node, state))
            elif node.type == "http":
                # Add HTTP request node (Dify style)
                graph.add_node(node.name, lambda state: WorkflowService._execute_http_node(node, state))
            elif node.type == "list_operation":
                # Add list operation node (Dify style)
                graph.add_node(node.name, lambda state: WorkflowService._execute_list_operation_node(node, state))
        
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
    async def _execute_iteration_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute iteration node"""
        print(f"Executing iteration node: {node.name}")
        
        # Get iteration configuration
        config = node.config or {}
        iteration_collection = config.get('iteration_collection', '')
        iteration_variable = config.get('iteration_variable', 'item')
        iteration_condition = config.get('iteration_condition', '')
        
        # Get the collection from state
        collection = state.get(iteration_collection, [])
        
        # Execute iteration
        results = []
        for item in collection:
            # Set the iteration variable in state
            state[iteration_variable] = item
            
            # Evaluate condition if provided
            if iteration_condition:
                from base.plugins.agent.utils.safe_eval import safe_eval_condition
                try:
                    condition_result = safe_eval_condition(iteration_condition, state)
                    if not condition_result:
                        continue
                except Exception as e:
                    print(f"Error evaluating iteration condition: {e}")
                    continue
            
            # Add item to results
            results.append(item)
        
        # Store results in state
        state[f"iteration_{node.id}_output"] = results
        state[f"iteration_{node.id}_collection"] = collection
        state[f"iteration_{node.id}_count"] = len(results)
        
        return state

    @staticmethod
    async def _evaluate_condition(condition: str, state: Dict[str, Any]) -> str:
        """Evaluate condition"""
        # Here you would implement condition evaluation
        # This could involve evaluating the condition against the state
        print(f"Evaluating condition: {condition}")
        
        # Simulate condition evaluation
        return "true"
    
    # ==================== Dify 风格节点执行函数 ====================
    
    @staticmethod
    async def _execute_llm_node(llm: LLMModel, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LLM node"""
        print(f"Executing LLM node: {llm.model_name}")
        
        # Get LLM configuration from node config
        config = llm.config or {}
        prompt = config.get('prompt', '')
        temperature = config.get('temperature', 0.7)
        max_tokens = config.get('max_tokens', 2048)
        
        # Simulate LLM execution
        # In production, this would call the actual LLM API
        state[f"llm_{llm.id}_output"] = {
            "model": llm.model_name,
            "prompt": prompt,
            "response": f"Simulated response from {llm.model_name}",
            "temperature": temperature
        }
        return state
    
    @staticmethod
    async def _execute_code_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code node (Dify style)"""
        print(f"Executing code node: {node.name}")
        
        # Get code configuration
        config = node.config or {}
        language = config.get('language', 'python')
        code = config.get('code', '')
        
        # Execute code
        try:
            if language == 'python':
                # Execute Python code
                exec_globals = {'state': state, 'json': json, 're': re}
                exec(code, exec_globals)
                result = exec_globals.get('result', 'Code executed successfully')
            elif language == 'javascript':
                # Execute JavaScript code (simplified)
                result = f"JavaScript code executed: {code[:50]}..."
            else:
                result = f"Unsupported language: {language}"
        except Exception as e:
            result = f"Code execution error: {str(e)}"
        
        state[f"code_{node.id}_output"] = result
        return state
    
    @staticmethod
    async def _execute_template_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute template node (Dify style)"""
        print(f"Executing template node: {node.name}")
        
        # Get template configuration
        config = node.config or {}
        template = config.get('template', '')
        
        # Render template
        try:
            # Simple template rendering (in production, use Jinja2 or similar)
            rendered = template
            for key, value in state.items():
                if isinstance(value, (str, int, float, bool)):
                    rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
        except Exception as e:
            rendered = f"Template rendering error: {str(e)}"
        
        state[f"template_{node.id}_output"] = rendered
        return state
    
    @staticmethod
    async def _execute_variable_aggregator_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute variable aggregator node (Dify style)"""
        print(f"Executing variable aggregator node: {node.name}")
        
        # Get configuration
        config = node.config or {}
        input_vars = config.get('input_vars', '').split('\n')
        output_var = config.get('output_var', 'aggregated_output')
        
        # Aggregate variables
        aggregated = {}
        for var_name in input_vars:
            var_name = var_name.strip()
            if var_name in state:
                aggregated[var_name] = state[var_name]
        
        state[output_var] = aggregated
        state[f"variable_aggregator_{node.id}_output"] = aggregated
        return state
    
    @staticmethod
    async def _execute_document_extractor_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute document extractor node (Dify style)"""
        print(f"Executing document extractor node: {node.name}")
        
        # Get configuration
        config = node.config or {}
        document_var = config.get('document_var', '')
        extract_rules = config.get('extract_rules', '')
        
        # Extract content from document
        # In production, this would use actual document processing
        extracted = {
            "document_var": document_var,
            "extract_rules": extract_rules,
            "extracted_content": f"Extracted content from {document_var}"
        }
        
        state[f"document_extractor_{node.id}_output"] = extracted
        return state
    
    @staticmethod
    async def _execute_variable_assigner_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute variable assigner node (Dify style)"""
        print(f"Executing variable assigner node: {node.name}")
        
        # Get configuration
        config = node.config or {}
        var_name = config.get('var_name', '')
        var_value = config.get('var_value', '')
        
        # Assign variable
        state[var_name] = var_value
        state[f"variable_assigner_{node.id}_output"] = f"Variable {var_name} assigned"
        return state
    
    @staticmethod
    async def _execute_parameter_extractor_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parameter extractor node (Dify style)"""
        print(f"Executing parameter extractor node: {node.name}")
        
        # Get configuration
        config = node.config or {}
        input_text = config.get('input_text', '')
        parameters = config.get('parameters', '').split('\n')
        
        # Extract parameters
        extracted_params = {}
        for param_name in parameters:
            param_name = param_name.strip()
            # In production, this would use actual parameter extraction logic
            extracted_params[param_name] = f"Extracted {param_name}"
        
        state[f"parameter_extractor_{node.id}_output"] = extracted_params
        return state
    
    @staticmethod
    async def _execute_http_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP request node (Dify style)"""
        print(f"Executing HTTP node: {node.name}")
        
        # Get configuration
        config = node.config or {}
        method = config.get('method', 'GET')
        url = config.get('url', '')
        headers = config.get('headers', '{}')
        body = config.get('body', '{}')
        
        # Execute HTTP request
        if HTTPX_AVAILABLE:
            try:
                async with httpx.AsyncClient() as client:
                    if method == 'GET':
                        response = await client.get(url, headers=json.loads(headers))
                    elif method == 'POST':
                        response = await client.post(url, headers=json.loads(headers), json=json.loads(body))
                    elif method == 'PUT':
                        response = await client.put(url, headers=json.loads(headers), json=json.loads(body))
                    elif method == 'DELETE':
                        response = await client.delete(url, headers=json.loads(headers))
                    else:
                        response = None
                    
                    result = {
                        "status_code": response.status_code if response else 0,
                        "response": response.text if response else "No response",
                        "headers": dict(response.headers) if response else {}
                    }
            except Exception as e:
                result = {
                    "error": str(e),
                    "status_code": 0
                }
        else:
            # Fallback if httpx is not available
            result = {
                "message": "HTTPX library not available",
                "url": url,
                "method": method,
                "simulated_response": "HTTP request would be executed here"
            }
        
        state[f"http_{node.id}_output"] = result
        return state
    
    @staticmethod
    async def _execute_list_operation_node(node: WorkflowNode, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute list operation node (Dify style)"""
        print(f"Executing list operation node: {node.name}")
        
        # Get configuration
        config = node.config or {}
        operation = config.get('operation', 'filter')
        input_list = config.get('input_list', '')
        
        # Get the list from state
        input_data = state.get(input_list, [])
        
        # Perform operation
        if operation == 'filter':
            result = [item for item in input_data if item]  # Simple filter
        elif operation == 'map':
            result = [f"Processed: {item}" for item in input_data]  # Simple map
        elif operation == 'sort':
            result = sorted(input_data)  # Simple sort
        elif operation == 'unique':
            result = list(set(input_data))  # Remove duplicates
        else:
            result = input_data
        
        state[f"list_operation_{node.id}_output"] = result
        return state

    @staticmethod
    def should_use_sse(workflow) -> bool:
        """
        判断工作流是否应该使用 SSE 模式执行

        判断条件：
        1. 有流式 LLM 节点（stream=True）
        2. 有工具/HTTP/技能节点（可能需要等待外部响应）
        3. 有条件分支或循环节点（需要多轮执行）

        Args:
            workflow: 工作流对象

        Returns:
            是否应该使用 SSE 模式
        """
        graph = workflow.definition
        if not graph or 'nodes' not in graph:
            return False

        nodes = graph.get('nodes', [])

        for node in nodes:
            stream_val = node.get('data', {}).get('stream')
            is_streaming = stream_val is True or (isinstance(stream_val, str) and stream_val.lower() == 'true')
            if node.get('type') == 'llm' and is_streaming:
                return True

        for node in nodes:
            if node.get('type') in ('tool', 'http', 'skill'):
                return True

        has_condition = any(n.get('type') == 'condition' for n in nodes)
        has_loop = any(n.get('type') in ('loop', 'iteration') for n in nodes)
        if has_condition or has_loop:
            return True

        return False

    @staticmethod
    async def sse_execution_generator(
        agent,
        input_data: Dict[str, Any],
        execution_id: str,
        execution_manager: dict,
        actor: dict
    ):
        """
        SSE事件生成器 - 实时推送执行过程（支持边思考边输出）

        Args:
            agent: 模拟的agent对象（包含graph_definition）
            input_data: 输入数据
            execution_id: 执行ID
            execution_manager: 执行管理器（用于检查取消状态）
            actor: 当前用户

        Returns:
            SSE事件流
        """
        from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
        import json
        from datetime import datetime

        logger = logging.getLogger(__name__)
        logger.info(f"[Workflow Execution] 开始执行，execution_id: {execution_id}")

        def send_event(event_data):
            return f"data: {json.dumps({**event_data, 'timestamp': datetime.now().isoformat()}, ensure_ascii=False)}\n\n"

        async def check_cancelled():
            exec_info = execution_manager.get(execution_id)
            return exec_info and exec_info.get('is_cancelled', False)

        try:
            yield send_event({'type': 'start', 'execution_id': execution_id, 'message': '开始执行工作流'})

            class SSEQueue:
                def __init__(self):
                    self.queue = asyncio.Queue()

                async def put(self, event):
                    await self.queue.put(event)

                async def get(self):
                    return await self.queue.get()

                def empty(self):
                    return self.queue.empty()

            sse_queue = SSEQueue()
            sse_yield_call_count = [0]

            async def wrapped_sse_yield_with_counter(event):
                sse_yield_call_count[0] += 1
                await sse_queue.put(event)

            async def execute_task():
                logger.info(f"[Workflow SSE生成器] execute_task 开始执行")
                try:
                    exec_info = execution_manager.get(execution_id, {})
                    llm_resources = exec_info.get('_llm_resources', {})
                    skill_resources = exec_info.get('_skill_resources', {})
                    logger.info(f"[Workflow SSE生成器] 获取预加载资源: LLM={len(llm_resources)}, 技能={len(skill_resources)}")

                    result = await LangGraphExecutor.execute_agent(
                        agent=agent,
                        input_data=input_data,
                        actor=actor,
                        sse_yield_func=wrapped_sse_yield_with_counter,
                        execution_id=execution_id,
                        llm_resources=llm_resources,
                        skill_resources=skill_resources,
                    )
                    return result
                except Exception as e:
                    logger.error(f"[Workflow SSE生成器] LangGraph 执行异常: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return {
                        "success": False,
                        "message": str(e),
                        "traceback": traceback.format_exc()
                    }

            task = asyncio.create_task(execute_task())

            yield send_event({'type': 'info', 'label': '初始化', 'message': '初始化执行环境...'})

            done = False
            last_activity = asyncio.get_event_loop().time()
            import time
            loop_start_time = time.time()
            last_log_time = loop_start_time
            loop_count = 0

            while not done or not sse_queue.empty():
                loop_count += 1
                try:
                    current_time = asyncio.get_event_loop().time()
                    current_elapsed = time.time() - loop_start_time

                    if current_elapsed - last_log_time >= 5.0:
                        last_log_time = current_elapsed

                    if await check_cancelled():
                        yield send_event({'type': 'cancelled', 'message': '执行被用户中断'})
                        task.cancel()
                        break

                    if task.done():
                        task_exception = task.exception()
                        if task_exception:
                            yield send_event({'type': 'error', 'message': f'执行异常: {str(task_exception)}'})
                            break

                    if current_time - last_activity > 300:
                        yield send_event({'type': 'error', 'message': '执行超时，请重试'})
                        task.cancel()
                        break

                    try:
                        if not sse_queue.empty():
                            event = await asyncio.wait_for(sse_queue.get(), timeout=1.0)
                            yield send_event(event)
                            last_activity = current_time
                        elif not task.done():
                            last_activity = current_time
                            await asyncio.sleep(0.01)
                    except asyncio.TimeoutError:
                        await asyncio.sleep(0.01)
                    except Exception as e:
                        pass

                    if task.done() and sse_queue.empty():
                        done = True
                        logger.info("[Workflow Execution] 任务已完成，队列已空，退出循环")

                except Exception as e:
                    logger.error(f"[Workflow SSE 推送异常] {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    break

            logger.info("[Workflow Execution] while循环已退出，准备获取task结果")
            try:
                logger.info(f"[Workflow Execution] 检查task状态: cancelled={task.cancelled()}, done={task.done()}")
                if not task.cancelled():
                    result = await task
                    logger.info(f"[Workflow Execution] await task 完成，result.success={result.get('success')}")

                    variables_summary = {}
                    variables = result.get('variables', {})
                    for key, value in list(variables.items())[:5]:
                        if key == 'llm_output':
                            llm_str = str(value)
                            variables_summary[key] = {
                                'type': 'large_text',
                                'length': len(llm_str),
                                'preview': llm_str[:100] + '...' if len(llm_str) > 100 else llm_str
                            }
                        else:
                            variables_summary[key] = value

                    logger.info("[Workflow Execution] 准备发送 complete 事件")
                    yield send_event({
                        'type': 'complete',
                        'result': result.get('output', {}),
                        'variables': variables_summary
                    })
                    logger.info("[Workflow Execution] complete 事件已发送")
                else:
                    logger.warning("[Workflow Execution] task已被取消，跳过获取结果")
            except Exception as e:
                logger.error(f"获取执行结果失败: {e}")
                yield send_event({'type': 'error', 'message': str(e)})

        except Exception as e:
            import traceback
            yield send_event({'type': 'error', 'message': str(e), 'traceback': traceback.format_exc()})

    @staticmethod
    async def execute_workflow_direct(workflow_id: int, input_data: dict, actor: dict, execution_id: str = None) -> dict:
        """
        直接执行工作流（非SSE模式）

        Args:
            workflow_id: 工作流ID
            input_data: 输入数据
            actor: 当前用户
            execution_id: 执行ID

        Returns:
            执行结果
        """
        workflow = await WorkflowService.get_workflow_by_id(workflow_id)
        if not workflow or workflow.status != "active":
            return {"success": False, "message": "Workflow not found or inactive"}

        try:
            from base.plugins.agent.services.langgraph_executor import LangGraphExecutor

            class MockAgent:
                def __init__(self, definition, wid, wname):
                    self.graph_definition = definition
                    self.id = wid
                    self.name = wname

            mock_agent = MockAgent(workflow.definition or {}, workflow_id, workflow.name)
            result = await LangGraphExecutor.execute_agent(
                agent=mock_agent,
                input_data=input_data,
                actor=actor,
                execution_id=execution_id
            )
            return result

        except Exception as e:
            import traceback
            return {"success": False, "message": str(e), "traceback": traceback.format_exc()}
