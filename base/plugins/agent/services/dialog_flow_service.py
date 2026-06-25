from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import json
import logging
from base.plugins.agent.models.dialog_flow import DialogFlow, DialogFlowNode, DialogFlowEdge, DialogFlowExecution
from base.plugins.agent.schemas.dialog_flow import (
    DialogFlowCreate, DialogFlowUpdate, DialogFlowResponse,
    DialogFlowNodeCreate, DialogFlowNodeUpdate, DialogFlowNodeResponse,
    DialogFlowEdgeCreate, DialogFlowEdgeUpdate, DialogFlowEdgeResponse,
    DialogFlowExecutionCreate, DialogFlowExecutionResponse
)

logger = logging.getLogger(__name__)


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
    async def list_dialog_flows(agent_id: Optional[int] = None, skip: int = 0, limit: int = 100, name: str = "", status: str = "") -> List[DialogFlowResponse]:
        """列出对话流"""
        query = DialogFlow.all()
        if agent_id:
            query = query.filter(agent__id=agent_id)
        if name:
            query = query.filter(name__icontains=name)
        if status:
            query = query.filter(status=status)
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
        
        await DialogFlowNode.filter(dialog_flow_id=dialog_flow_id).delete()
        await DialogFlowEdge.filter(dialog_flow_id=dialog_flow_id).delete()
        
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
        
        await DialogFlowEdge.filter(source_node_id=node_id).delete()
        await DialogFlowEdge.filter(target_node_id=node_id).delete()
        
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
    def _parse_flow_data(dialog_flow: DialogFlow) -> Dict[str, Any]:
        """解析对话流结构数据"""
        flow_data = dialog_flow.flow_data or {}
        if isinstance(flow_data, str):
            try:
                flow_data = json.loads(flow_data)
            except json.JSONDecodeError:
                logger.error("对话流结构解析失败")
                return {"nodes": [], "edges": []}
        return flow_data

    @staticmethod
    def _build_node_map(nodes: List[Dict]) -> Dict[str, Dict]:
        """构建节点ID到节点的映射"""
        return {node.get("id"): node for node in nodes}

    @staticmethod
    def _build_edge_map(edges: List[Dict]) -> Dict[str, List[Dict]]:
        """构建源节点ID到边列表的映射"""
        edge_map = {}
        for edge in edges:
            source = edge.get("source")
            if source not in edge_map:
                edge_map[source] = []
            edge_map[source].append(edge)
        return edge_map

    @staticmethod
    def _find_start_node(nodes: List[Dict]) -> Optional[Dict]:
        """找到开始节点"""
        for node in nodes:
            if node.get("type") == "start":
                return node
        return None

    @staticmethod
    async def _execute_node(
        node: Dict,
        variables: Dict[str, Any],
        input_data: Dict[str, Any],
        sse_yield_func=None
    ) -> Dict[str, Any]:
        """执行单个节点"""
        node_type = node.get("type")
        node_data = node.get("data", {})
        result = {"type": node_type, "node_id": node.get("id"), "output": {}}

        if node_type == "start":
            result["output"] = {"message": "对话流开始"}
        
        elif node_type == "end":
            result["output"] = {"message": "对话流结束"}
        
        elif node_type == "input":
            input_key = node_data.get("input_var", "input")
            result["output"] = {input_key: input_data.get("text", "")}
        
        elif node_type == "output":
            output_var = node_data.get("output_var", "output")
            result["output"] = {output_var: variables.get(output_var, "")}
        
        elif node_type == "message":
            content = node_data.get("content", "")
            content = DialogFlowService._replace_variables(content, variables)
            result["output"] = {"message": content}
            if sse_yield_func:
                await sse_yield_func({
                    "type": "message",
                    "node_id": node.get("id"),
                    "content": content
                })
        
        elif node_type == "text":
            content = node_data.get("content", "")
            content = DialogFlowService._replace_variables(content, variables)
            output_var = node_data.get("output_var", "text")
            result["output"] = {output_var: content}
        
        elif node_type == "image":
            image_url = node_data.get("image_url", "")
            image_url = DialogFlowService._replace_variables(image_url, variables)
            result["output"] = {"image_url": image_url, "image_alt": node_data.get("image_alt", "")}
        
        elif node_type == "voice":
            text = node_data.get("text", "")
            text = DialogFlowService._replace_variables(text, variables)
            result["output"] = {"text": text, "voice_type": node_data.get("voice_type", "tts")}
        
        elif node_type == "llm":
            llm_result = await DialogFlowService._execute_llm_node(
                node, variables, input_data, sse_yield_func
            )
            result["output"] = llm_result
        
        elif node_type == "knowledge_retrieval":
            kr_result = await DialogFlowService._execute_knowledge_retrieval_node(
                node, variables, sse_yield_func
            )
            result["output"] = kr_result
        
        elif node_type == "api":
            api_result = await DialogFlowService._execute_api_node(
                node, variables, sse_yield_func
            )
            result["output"] = api_result
        
        elif node_type == "condition":
            condition = node_data.get("condition", "")
            condition = DialogFlowService._replace_variables(condition, variables)
            try:
                result["output"] = {"result": eval(condition, {}, variables)}
            except Exception as e:
                logger.error(f"条件节点执行失败: {e}")
                result["output"] = {"result": False}
        
        elif node_type == "question":
            question = node_data.get("question", "")
            question = DialogFlowService._replace_variables(question, variables)
            result["output"] = {"question": question}
        
        else:
            logger.warning(f"未知节点类型: {node_type}")
            result["output"] = {"message": f"未处理的节点类型: {node_type}"}

        return result

    @staticmethod
    async def _execute_llm_node(
        node: Dict,
        variables: Dict[str, Any],
        input_data: Dict[str, Any],
        sse_yield_func=None
    ) -> Dict[str, Any]:
        """执行大模型节点"""
        node_data = node.get("data", {})
        model_id = node_data.get("llm_model_id")
        prompt = node_data.get("llm_prompt", "")
        temperature = node_data.get("llm_temperature", 0.7)
        max_tokens = node_data.get("llm_max_tokens", 1024)
        stream = node_data.get("llm_stream", True)
        output_var = node_data.get("output_var", "response")

        prompt = DialogFlowService._replace_variables(prompt, variables)

        messages = []
        if input_data.get("history"):
            for msg in input_data["history"]:
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content")
                })
        messages.append({"role": "user", "content": prompt})

        if not model_id:
            return {output_var: "请先配置大模型"}

        try:
            from base.plugins.llm.models.model import LLMModel
            from base.plugins.llm.models.api_key import LLMApiKey
            from base.plugins.llm.services.chat_service import ChatService

            model = await LLMModel.get_or_none(id=model_id).prefetch_related('provider')
            if not model:
                return {output_var: "模型不存在"}

            if model.status != "active":
                return {output_var: "模型未启用"}

            api_key_obj = await LLMApiKey.filter(
                model_id=model.id
            ).first()
            if not api_key_obj:
                api_key_obj = await LLMApiKey.filter(
                    provider_id=model.provider_id,
                    model_id__isnull=True
                ).first()
            if not api_key_obj:
                return {output_var: "没有可用的API密钥"}

            endpoint_url = model.endpoint_url or api_key_obj.endpoint_url or model.provider.official_url
            if endpoint_url:
                endpoint_url = endpoint_url.rstrip('/')
                if endpoint_url.endswith('/chat/completions'):
                    endpoint_url = endpoint_url[:-len('/chat/completions')]
                if '/responses' in endpoint_url:
                    endpoint_url = endpoint_url.split('/responses')[0]

            credentials = api_key_obj.get_credentials()

            service = await ChatService.get_provider_service(
                provider_name_en=model.provider.name_en,
                api_key=credentials.get("api_key", ""),
                endpoint_url=endpoint_url,
                api_secret=credentials.get("api_secret", ""),
                call_mode=credentials.get("call_mode", "vendor_sdk"),
            )

            if stream and sse_yield_func:
                full_response = ""
                async for chunk in service.chat_stream(
                    model=model.model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=1.0
                ):
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        full_response += content
                        await sse_yield_func({
                            "type": "stream",
                            "node_id": node.get("id"),
                            "content": content,
                            "full_content": full_response
                        })
                return {output_var: full_response}
            else:
                result = await service.chat(
                    model=model.model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=1.0,
                    stream=False
                )
                response_text = result["choices"][0]["message"]["content"]
                if sse_yield_func:
                    await sse_yield_func({
                        "type": "llm_complete",
                        "node_id": node.get("id"),
                        "content": response_text
                    })
                return {output_var: response_text}

        except Exception as e:
            logger.error(f"大模型节点执行失败: {e}", exc_info=True)
            return {output_var: f"大模型调用失败: {str(e)}"}

    @staticmethod
    async def _execute_knowledge_retrieval_node(
        node: Dict,
        variables: Dict[str, Any],
        sse_yield_func=None
    ) -> Dict[str, Any]:
        """执行知识检索节点"""
        node_data = node.get("data", {})
        query = node_data.get("query", "")
        top_k = node_data.get("top_k", 3)
        output_var = node_data.get("output_var", "knowledge")

        query = DialogFlowService._replace_variables(query, variables)

        if sse_yield_func:
            await sse_yield_func({
                "type": "knowledge_retrieval",
                "node_id": node.get("id"),
                "query": query
            })

        try:
            from base.plugins.agent.services.rag_service import RAGService
            results = await RAGService.search(query, top_k=top_k)
            contexts = [r.get("content", "") for r in results]
            result = {"results": results, "contexts": "\n".join(contexts)}
            
            if sse_yield_func:
                await sse_yield_func({
                    "type": "knowledge_result",
                    "node_id": node.get("id"),
                    "results": results
                })
            
            return {output_var: result}
        except Exception as e:
            logger.error(f"知识检索失败: {e}", exc_info=True)
            return {output_var: f"知识检索失败: {str(e)}"}

    @staticmethod
    async def _execute_api_node(
        node: Dict,
        variables: Dict[str, Any],
        sse_yield_func=None
    ) -> Dict[str, Any]:
        """执行API调用节点"""
        node_data = node.get("data", {})
        url = node_data.get("url", "")
        method = node_data.get("method", "GET")
        headers = node_data.get("headers", {})
        body = node_data.get("body", {})
        output_var = node_data.get("output_var", "api_result")

        url = DialogFlowService._replace_variables(url, variables)

        if isinstance(body, str):
            body = DialogFlowService._replace_variables(body, variables)
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass

        if sse_yield_func:
            await sse_yield_func({
                "type": "api_call",
                "node_id": node.get("id"),
                "url": url,
                "method": method
            })

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body if isinstance(body, dict) else None,
                    data=body if isinstance(body, str) else None
                ) as response:
                    status = response.status
                    try:
                        result = await response.json()
                    except Exception:
                        result = await response.text()
                    
                    if sse_yield_func:
                        await sse_yield_func({
                            "type": "api_result",
                            "node_id": node.get("id"),
                            "status": status,
                            "result": result
                        })
                    
                    return {output_var: {"status": status, "result": result}}
        except Exception as e:
            logger.error(f"API调用失败: {e}", exc_info=True)
            return {output_var: f"API调用失败: {str(e)}"}

    @staticmethod
    def _replace_variables(text: str, variables: Dict[str, Any]) -> str:
        """替换文本中的变量"""
        if not text:
            return text
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            text = text.replace(placeholder, str(value))
        return text

    @staticmethod
    def _evaluate_condition(edge: Dict, variables: Dict[str, Any]) -> bool:
        """评估边的条件"""
        condition = edge.get("condition", "")
        if not condition:
            return True
        condition = DialogFlowService._replace_variables(condition, variables)
        try:
            return bool(eval(condition, {}, variables))
        except Exception:
            return False

    @staticmethod
    def should_use_sse(dialog_flow: DialogFlow) -> bool:
        """判断是否应该使用SSE模式"""
        flow_data = DialogFlowService._parse_flow_data(dialog_flow)
        nodes = flow_data.get("nodes", [])
        
        for node in nodes:
            node_data = node.get("data", {})
            if node.get("type") == "llm":
                stream_val = node_data.get("llm_stream", True)
                is_streaming = stream_val is True or (isinstance(stream_val, str) and stream_val.lower() == 'true')
                if is_streaming:
                    return True
        
        for node in nodes:
            if node.get("type") in ("knowledge_retrieval", "api"):
                return True
        
        has_condition = any(n.get("type") == "condition" for n in nodes)
        if has_condition:
            return True
        
        return False

    @staticmethod
    async def execute_dialog_flow(*args, **kwargs) -> DialogFlowExecutionResponse:
        """执行对话流（非流式）"""
        if len(args) == 1 and hasattr(args[0], 'dialog_flow_id'):
            data = args[0]
            dialog_flow_id = data.dialog_flow_id
            input_data = data.input_data
            agent_id = data.agent_id
            user_id = data.user_id
        else:
            dialog_flow_id = kwargs.get('dialog_flow_id') or (args[0] if args else None)
            input_data = kwargs.get('input_data') or (args[1] if len(args) > 1 else None)
            agent_id = kwargs.get('agent_id') or (args[2] if len(args) > 2 else None)
            user_id = kwargs.get('user_id') or (args[3] if len(args) > 3 else None)
        
        execution_data = {
            "dialog_flow_id": dialog_flow_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "input_data": input_data or {}
        }
        execution = await DialogFlowExecution.create(**execution_data)
        
        try:
            dialog_flow = await DialogFlow.get_or_none(id=dialog_flow_id)
            if not dialog_flow:
                raise ValueError("对话流不存在")
            
            flow_data = DialogFlowService._parse_flow_data(dialog_flow)
            nodes = flow_data.get("nodes", [])
            edges = flow_data.get("edges", [])
            
            node_map = DialogFlowService._build_node_map(nodes)
            edge_map = DialogFlowService._build_edge_map(edges)
            
            start_node = DialogFlowService._find_start_node(nodes)
            if not start_node:
                raise ValueError("未找到开始节点")
            
            variables = {}
            variables.update(input_data or {})
            execution_path = []
            
            current_node_id = start_node.get("id")
            
            while current_node_id:
                current_node = node_map.get(current_node_id)
                if not current_node:
                    break
                
                node_result = await DialogFlowService._execute_node(
                    current_node, variables, input_data or {}
                )
                
                execution_path.append({
                    "node_id": current_node_id,
                    "node_type": current_node.get("type"),
                    "output": node_result.get("output", {})
                })
                
                variables.update(node_result.get("output", {}))
                
                if current_node.get("type") == "end":
                    break
                
                next_edges = edge_map.get(current_node_id, [])
                current_node_id = None
                
                for edge in next_edges:
                    if DialogFlowService._evaluate_condition(edge, variables):
                        current_node_id = edge.get("target")
                        break
            
            execution.status = "completed"
            execution.execution_path = execution_path
            execution.output_data = variables
            execution.completed_at = datetime.utcnow()
            await execution.save()
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            await execution.save()
        
        return DialogFlowExecutionResponse.from_orm(execution)

    @staticmethod
    async def sse_execution_generator(
        dialog_flow: DialogFlow,
        input_data: Dict[str, Any],
        execution_id: str = None
    ) -> AsyncGenerator[str, None]:
        """SSE事件生成器 - 实时推送执行过程"""
        import asyncio
        
        def send_event(event_data):
            return f"data: {json.dumps({**event_data, 'timestamp': datetime.now().isoformat()}, ensure_ascii=False)}\n\n"
        
        event_queue = asyncio.Queue()
        
        async def push_event(event_data):
            await event_queue.put(send_event(event_data))
        
        await push_event({'type': 'start', 'execution_id': execution_id, 'message': '开始执行对话流'})
        
        async def execute_flow():
            try:
                flow_data = DialogFlowService._parse_flow_data(dialog_flow)
                nodes = flow_data.get("nodes", [])
                edges = flow_data.get("edges", [])
                
                node_map = DialogFlowService._build_node_map(nodes)
                edge_map = DialogFlowService._build_edge_map(edges)
                
                start_node = DialogFlowService._find_start_node(nodes)
                if not start_node:
                    await push_event({'type': 'error', 'message': '未找到开始节点'})
                    return
                
                variables = {}
                variables.update(input_data or {})
                execution_path = []
                
                current_node_id = start_node.get("id")
                
                while current_node_id:
                    current_node = node_map.get(current_node_id)
                    if not current_node:
                        break
                    
                    await push_event({'type': 'node_start', 'node_id': current_node_id, 'node_type': current_node.get("type")})
                    
                    node_result = await DialogFlowService._execute_node(
                        current_node, variables, input_data or {},
                        sse_yield_func=push_event
                    )
                    
                    execution_path.append({
                        "node_id": current_node_id,
                        "node_type": current_node.get("type"),
                        "output": node_result.get("output", {})
                    })
                    
                    variables.update(node_result.get("output", {}))
                    
                    await push_event({'type': 'node_complete', 'node_id': current_node_id, 'output': node_result.get("output", {})})
                    
                    if current_node.get("type") == "end":
                        break
                    
                    next_edges = edge_map.get(current_node_id, [])
                    current_node_id = None
                    
                    for edge in next_edges:
                        if DialogFlowService._evaluate_condition(edge, variables):
                            current_node_id = edge.get("target")
                            break
                
                await push_event({
                    'type': 'complete',
                    'execution_id': execution_id,
                    'variables': variables,
                    'execution_path': execution_path
                })
                
            except Exception as e:
                logger.error(f"对话流执行失败: {e}", exc_info=True)
                await push_event({'type': 'error', 'message': str(e)})
        
        task = asyncio.create_task(execute_flow())
        
        while True:
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=300)
                yield event
            except asyncio.TimeoutError:
                logger.warning("SSE事件队列超时")
                break
            
            if task.done() and event_queue.empty():
                break
        
        if not task.done():
            task.cancel()

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