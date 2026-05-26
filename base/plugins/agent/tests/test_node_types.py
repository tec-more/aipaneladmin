"""
Agent 节点类型测试用例
测试各种节点类型的输入输出是否符合逻辑
"""
import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch

from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.models.dialog_flow import DialogFlow


class TestNodeTypes:
    """测试各种节点类型"""

    @pytest.fixture
    def mock_agent(self):
        """创建一个模拟的agent对象"""
        agent = MagicMock(spec=Agent)
        agent.id = "test_agent_id"
        agent.name = "测试智能体"
        agent.description = "测试智能体描述"
        agent.workflow = None
        agent.enabled = True
        return agent

    @pytest.fixture
    def executor(self, mock_agent):
        """创建执行器实例"""
        return LangGraphExecutor(agent=mock_agent)

    def test_start_node(self, executor, mock_agent):
        """测试 start 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [{"source": "start", "target": "end"}]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "测试"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True
        assert "output" in result

    def test_input_node(self, executor, mock_agent):
        """测试 input 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "input", "type": "input", "label": "输入", "inputKey": "user_input"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "input"},
                {"source": "input", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "用户输入内容"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True
        assert "variables" in result
        assert result["variables"].get("user_input") == "用户输入内容"

    def test_output_node(self, executor, mock_agent):
        """测试 output 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "output", "type": "output", "label": "输出", "outputVar": "result"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "output"},
                {"source": "output", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "测试"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True
        assert "output" in result

    @patch('base.plugins.agent.services.langgraph_executor.LangGraphExecutor._create_llm_node')
    def test_llm_node(self, mock_create_llm, executor, mock_agent):
        """测试 llm 节点"""
        mock_create_llm.return_value = lambda state: {"output": {"text": "LLM响应"}, "variables": {}}
        
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "llm", "type": "llm", "label": "大模型", "model": "test-model", "prompt": "你好"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "llm"},
                {"source": "llm", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "测试"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True
        mock_create_llm.assert_called_once()

    def test_condition_node(self, executor, mock_agent):
        """测试 condition 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "condition", "type": "condition", "label": "条件判断"},
                {"id": "true_branch", "type": "output", "label": "真分支", "outputVar": "result"},
                {"id": "false_branch", "type": "output", "label": "假分支", "outputVar": "result"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "condition"},
                {"source": "condition", "target": "true_branch", "condition": "1 == 1"},
                {"source": "condition", "target": "false_branch", "condition": "1 == 2"},
                {"source": "true_branch", "target": "end"},
                {"source": "false_branch", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "测试"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True

    def test_code_node(self, executor, mock_agent):
        """测试 code 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "code", "type": "code", "label": "代码执行", "code": "result = input_data.get('text', '') + ' processed'"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "code"},
                {"source": "code", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "hello"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True
        assert "variables" in result

    def test_template_node(self, executor, mock_agent):
        """测试 template 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "template", "type": "template", "label": "模板", "template": "Hello {{name}}", "outputVar": "greeting"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "template"},
                {"source": "template", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "测试"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True

    def test_variable_assigner_node(self, executor, mock_agent):
        """测试 variable_assigner 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "assign", "type": "variable_assigner", "label": "变量赋值", 
                 "variables": [{"name": "count", "value": 10}, {"name": "message", "value": "hello"}]},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "assign"},
                {"source": "assign", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "测试"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True
        assert result["variables"].get("count") == 10
        assert result["variables"].get("message") == "hello"

    def test_parameter_extractor_node(self, executor, mock_agent):
        """测试 parameter_extractor 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "extractor", "type": "parameter_extractor", "label": "参数提取",
                 "parameters": [
                     {"name": "destination", "label": "目的地"},
                     {"name": "budget", "label": "预算"}
                 ]},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "extractor"},
                {"source": "extractor", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "去北京，预算5000"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True
        assert "variables" in result

    def test_json_extractor_node(self, executor, mock_agent):
        """测试 json_extractor 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "json_extractor", "type": "json_extractor", "label": "JSON提取", "sourceVar": "input"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "json_extractor"},
                {"source": "json_extractor", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": '{"name": "test", "value": 123}'},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True

    def test_variable_aggregator_node(self, executor, mock_agent):
        """测试 variable_aggregator 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "assign1", "type": "variable_assigner", "label": "赋值1", 
                 "variables": [{"name": "items", "value": ["a"]}]},
                {"id": "assign2", "type": "variable_assigner", "label": "赋值2", 
                 "variables": [{"name": "items", "value": ["b"]}]},
                {"id": "aggregator", "type": "variable_aggregator", "label": "聚合", 
                 "variableName": "items", "aggregateType": "append"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "assign1"},
                {"source": "assign1", "target": "assign2"},
                {"source": "assign2", "target": "aggregator"},
                {"source": "aggregator", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "测试"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True
        assert "variables" in result

    def test_http_node(self, executor, mock_agent):
        """测试 http 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "http", "type": "http", "label": "HTTP请求", 
                 "method": "GET", "url": "https://api.example.com/test"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "http"},
                {"source": "http", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "测试"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True

    def test_loop_and_iteration_nodes(self, executor, mock_agent):
        """测试 loop 和 iteration 节点"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "loop", "type": "loop", "label": "循环开始", "iterableVar": "items"},
                {"id": "iteration", "type": "iteration", "label": "迭代", "itemVar": "item"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "loop"},
                {"source": "loop", "target": "iteration"},
                {"source": "iteration", "target": "loop"},
                {"source": "loop", "target": "end"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "测试"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True

    def test_complex_workflow(self, executor, mock_agent):
        """测试复杂工作流：多个节点组合"""
        graph_data = {
            "nodes": [
                {"id": "start", "type": "start", "label": "开始"},
                {"id": "input", "type": "input", "label": "获取输入", "inputKey": "user_input"},
                {"id": "assign", "type": "variable_assigner", "label": "设置变量",
                 "variables": [{"name": "status", "value": "processing"}]},
                {"id": "condition", "type": "condition", "label": "判断"},
                {"id": "llm", "type": "llm", "label": "处理", "model": "test", "prompt": "处理: {{user_input}}"},
                {"id": "output", "type": "output", "label": "输出", "outputVar": "result"},
                {"id": "end", "type": "end", "label": "结束"}
            ],
            "edges": [
                {"source": "start", "target": "input"},
                {"source": "input", "target": "assign"},
                {"source": "assign", "target": "condition"},
                {"source": "condition", "target": "llm", "condition": "status == 'processing'"},
                {"source": "llm", "target": "output"},
                {"source": "output", "target": "end"},
                {"source": "condition", "target": "end", "condition": "status != 'processing'"}
            ]
        }
        
        mock_agent.workflow = json.dumps(graph_data)
        
        result = asyncio.run(executor.execute_agent(
            input_data={"text": "复杂测试"},
            actor={"type": "user", "id": "test_user"},
            execution_id="test_execution"
        ))
        
        assert result["success"] is True
        assert "output" in result
        assert "variables" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])