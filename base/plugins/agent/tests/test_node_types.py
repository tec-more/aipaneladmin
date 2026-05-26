"""
智能体节点类型测试用例

本测试文件包含智能体工作流中所有节点类型的单元测试，覆盖：
- 流程控制节点 (start, end, condition, loop, iteration)
- 输入输出节点 (input, output)
- AI能力节点 (llm, agent)
- 功能扩展节点 (skill, tool, http, code, template)
- 数据处理节点 (variable_assigner, variable_aggregator, parameter_extractor, json_extractor, document_extractor)
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from base.plugins.agent.services.langgraph_executor import LangGraphExecutor


class TestNodeTypes:
    """节点类型测试类"""

    # ==================== 流程控制节点 ====================

    @pytest.mark.asyncio
    async def test_start_node(self):
        """测试开始节点 - 应设置开始时间变量"""
        node_data = {"label": "开始"}
        state = {
            "variables": {},
            "input": {"text": "测试输入"},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_start_node(node_data, state)
        
        assert "start_time" in result["variables"]
        assert "execution_trace" in result

    @pytest.mark.asyncio
    async def test_end_node(self):
        """测试结束节点 - 应设置结束时间"""
        node_data = {"label": "结束"}
        state = {
            "variables": {},
            "input": {"text": "测试输入"},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_end_node(node_data, state)
        
        assert "end_time" in result["output"]

    @pytest.mark.asyncio
    async def test_condition_node_true(self):
        """测试条件节点 - 条件为真"""
        node_data = {"condition": "{{score}} > 60", "label": "成绩判断"}
        state = {
            "variables": {"score": 80},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_condition_node(node_data, state)
        
        assert result["variables"]["condition_result"]["result"] == True

    @pytest.mark.asyncio
    async def test_condition_node_false(self):
        """测试条件节点 - 条件为假"""
        node_data = {"condition": "{{score}} > 60", "label": "成绩判断"}
        state = {
            "variables": {"score": 50},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_condition_node(node_data, state)
        
        assert result["variables"]["condition_result"]["result"] == False

    @pytest.mark.asyncio
    async def test_loop_node(self):
        """测试循环节点 - 应设置循环变量"""
        node_data = {"loop_count": 3, "loop_var": "index"}
        state = {
            "variables": {},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_loop_node(node_data, state)
        
        assert result["variables"]["loop_iterations"] == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_iteration_node(self):
        """测试迭代节点 - 应设置迭代变量"""
        node_data = {"iteration_var": "item", "collection_var": "items"}
        state = {
            "variables": {"items": ["a", "b", "c"]},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_iteration_node(node_data, state)
        
        assert result["variables"]["item"] == "a"
        assert result["variables"]["iteration_count"] == 3

    # ==================== 输入输出节点 ====================

    @pytest.mark.asyncio
    async def test_output_node_with_content(self):
        """测试输出节点 - 使用自定义内容"""
        node_data = {
            "outputVar": "result",
            "outputContent": "Hello {{name}}!",
            "label": "输出"
        }
        state = {
            "variables": {"name": "World"},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_output_node(node_data, state)
        
        assert result["output"]["result"]["text"] == "Hello World!"

    @pytest.mark.asyncio
    async def test_output_node_with_llm_output(self):
        """测试输出节点 - 使用LLM输出"""
        node_data = {"outputVar": "result", "label": "输出"}
        state = {
            "variables": {"llm_output": {"response": "这是LLM的响应"}},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_output_node(node_data, state)
        
        assert "result" in result["output"]
        assert "这是LLM的响应" in result["output"]["result"]["text"]

    # ==================== AI能力节点 ====================

    @pytest.mark.asyncio
    async def test_agent_node(self):
        """测试智能体节点 - 应设置智能体信息"""
        node_data = {"label": "智能体节点"}
        state = {
            "variables": {"agent_id": "agent_001", "agent_name": "测试智能体"},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_agent_node(node_data, state)
        
        assert "agent_info" in result["variables"]
        assert result["variables"]["agent_info"]["id"] == "agent_001"

    @pytest.mark.asyncio
    @patch("base.plugins.agent.services.langgraph_executor.LangGraphExecutor._get_llm_resource")
    @patch("base.plugins.agent.services.langgraph_executor.LangGraphExecutor._generate_mock_response")
    async def test_llm_node_mock(self, mock_generate, mock_resource):
        """测试LLM节点 - 使用模拟响应"""
        mock_resource.return_value = (None, None, "资源不可用")
        mock_generate.return_value = "模拟响应内容"
        
        current_node = {
            "id": "llm_001",
            "type": "llm",
            "data": {
                "prompt": "你好",
                "label": "LLM节点"
            }
        }
        state = {
            "variables": {},
            "input": {"text": "用户输入"},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_llm_node(current_node, state)
        
        assert "llm_output" in result["variables"]
        # 当资源不可用时，返回错误信息
        assert "错误" in result["variables"]["llm_output"]["response"] or "模拟响应" in result["variables"]["llm_output"]["response"]

    @pytest.mark.asyncio
    @patch("base.plugins.agent.services.langgraph_executor.LangGraphExecutor._get_llm_resource")
    @patch("base.plugins.agent.services.langgraph_executor.LangGraphExecutor._generate_mock_response")
    async def test_llm_node_streaming_mock(self, mock_generate, mock_resource):
        """测试LLM节点（流式）- 使用模拟响应"""
        mock_resource.return_value = (None, None, "资源不可用")
        mock_generate.return_value = "流式模拟响应"
        
        async def mock_sse_yield(data):
            pass
        
        current_node = {
            "id": "llm_stream_001",
            "type": "llm",
            "data": {
                "prompt": "流式测试",
                "stream": True,
                "label": "流式LLM节点"
            }
        }
        state = {
            "variables": {},
            "input": {"text": "用户输入"},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_llm_node_streaming(current_node, state, mock_sse_yield)
        
        assert "llm_output" in result["variables"]
        # 当资源不可用时，返回错误信息
        assert "错误" in result["variables"]["llm_output"]["response"] or "流式模拟响应" in result["variables"]["llm_output"]["response"]

    @pytest.mark.asyncio
    @patch("base.plugins.agent.services.langgraph_executor.LangGraphExecutor._get_llm_resource")
    async def test_llm_node_streaming_with_service(self, mock_resource):
        """测试LLM节点（流式）- 模拟流式响应"""
        mock_service = MagicMock()
        
        async def mock_chat_stream(**kwargs):
            yield {"choices": [{"delta": {"content": "第一部分"}}]}
            yield {"choices": [{"delta": {"content": "第二部分"}}]}
        
        mock_service.chat_stream = mock_chat_stream
        mock_resource.return_value = (mock_service, "test-model", None)
        
        received_chunks = []
        
        async def mock_sse_yield(data):
            received_chunks.append(data)
        
        current_node = {
            "id": "llm_stream_002",
            "type": "llm",
            "data": {
                "prompt": "流式测试",
                "stream": True,
                "label": "流式LLM节点"
            }
        }
        state = {
            "variables": {},
            "input": {"text": "用户输入"},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_llm_node_streaming(current_node, state, mock_sse_yield)
        
        assert "llm_output" in result["variables"]
        assert "第一部分第二部分" in result["variables"]["llm_output"]["response"]
        assert len(received_chunks) == 2
        assert received_chunks[0]["content"] == "第一部分"
        assert received_chunks[1]["content"] == "第二部分"

    # ==================== 功能扩展节点 ====================

    @pytest.mark.asyncio
    async def test_code_node(self):
        """测试代码节点 - 执行Python代码"""
        node_data = {
            "code": "result = 1 + 2",
            "label": "代码节点"
        }
        state = {
            "variables": {},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_code_node(node_data, state)
        
        assert result["variables"]["result"] == 3

    @pytest.mark.asyncio
    async def test_template_node(self):
        """测试模板节点 - 变量替换"""
        node_data = {
            "template": "Hello {{name}}, today is {{day}}",
            "outputVar": "greeting",
            "label": "模板节点"
        }
        state = {
            "variables": {"name": "Alice", "day": "Monday"},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_template_node(node_data, state)
        
        assert result["variables"]["greeting"] == "Hello Alice, today is Monday"

    # ==================== 数据处理节点 ====================

    @pytest.mark.asyncio
    async def test_variable_assigner_node(self):
        """测试变量赋值节点"""
        node_data = {
            "variable_name": "user_name",
            "value": "{{name}}",
            "label": "变量赋值"
        }
        state = {
            "variables": {"name": "Bob"},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_variable_assigner_node(node_data, state)
        
        assert result["variables"]["user_name"] == "Bob"

    @pytest.mark.asyncio
    async def test_variable_aggregator_node(self):
        """测试变量聚合器节点"""
        node_data = {
            "input_vars": ["name", "age"],
            "outputVar": "user_info",
            "label": "变量聚合"
        }
        state = {
            "variables": {"name": "Charlie", "age": 30, "other": "ignored"},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_variable_aggregator_node(node_data, state)
        
        assert result["variables"]["user_info"] == {"name": "Charlie", "age": 30}

    @pytest.mark.asyncio
    async def test_parameter_extractor_node(self):
        """测试参数提取节点"""
        node_data = {
            "source_var": "params",
            "parameter_name": "query",
            "label": "参数提取"
        }
        state = {
            "variables": {"params": {"query": "test", "limit": 10}},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_parameter_extractor_node(node_data, state)
        
        assert result["variables"]["query"] == "test"

    @pytest.mark.asyncio
    async def test_json_extractor_node(self):
        """测试JSON提取节点"""
        node_data = {
            "inputVariable": "json_str",
            "outputVar": "parsed_json",
            "label": "JSON提取"
        }
        state = {
            "variables": {"json_str": '{"key": "value"}'},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_json_extractor_node(node_data, state)
        
        assert result["variables"]["parsed_json"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_document_extractor_node(self):
        """测试文档提取节点"""
        node_data = {
            "document_var": "document",
            "extract_fields": ["title", "content"],
            "label": "文档提取"
        }
        state = {
            "variables": {"document": "这是一段测试文档内容，用于测试文档提取功能。"},
            "input": {},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._execute_document_extractor_node(node_data, state)
        
        assert "extracted_data" in result["variables"]
        assert "title" in result["variables"]["extracted_data"]

    # ==================== 节点执行辅助测试 ====================

    @pytest.mark.asyncio
    async def test_build_messages(self):
        """测试消息构建函数"""
        prompt = "Hello {{name}}"
        node_data = {"system_prompt": "你是一个助手"}
        state = {
            "variables": {"name": "World"},
            "input": {"text": "用户消息"},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result_prompt, messages, input_text = await LangGraphExecutor._build_messages(prompt, node_data, state)
        
        assert "Hello World" in result_prompt
        assert len(messages) >= 2
        assert input_text == "用户消息"

    @pytest.mark.asyncio
    async def test_parse_and_set_response(self):
        """测试响应解析函数"""
        llm_response = '{"key": "value", "response": "测试响应"}'
        node_data = {"outputVar": "result"}
        state = {
            "variables": {},
            "input": {"text": "输入"},
            "output": {},
            "messages": [],
            "execution_trace": []
        }
        
        result = await LangGraphExecutor._parse_and_set_response(llm_response, node_data, state, "test-model", "prompt")
        
        assert "result" in result["variables"]
        assert result["variables"]["result"]["key"] == "value"
