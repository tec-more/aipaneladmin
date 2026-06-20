# Agent 智能体节点测试文档

## 一、测试概述

本文档描述 Agent 智能体工作流中各类节点的测试方法和预期结果。测试覆盖所有节点类型，包括流程控制节点、输入输出节点、AI 能力节点、功能扩展节点和数据处理节点。

### 1.1 测试范围

| 节点类别 | 节点类型 | 测试状态 |
|---------|---------|---------|
| 流程控制节点 | start, end, condition, loop, iteration, parallel | ✅ 已覆盖 |
| 输入输出节点 | input, output | ✅ 已覆盖 |
| AI 能力节点 | llm, agent | ✅ 已覆盖 |
| 功能扩展节点 | skill, tool, http, code, template | ✅ 已覆盖 |
| 数据处理节点 | variable_assigner, variable_aggregator, parameter_extractor, json_extractor, document_extractor | ✅ 已覆盖 |

---

## 二、测试环境准备

### 2.1 环境要求

- Python 3.10+
- pytest
- pytest-asyncio

### 2.2 安装依赖

```bash
pip install pytest pytest-asyncio
```

### 2.3 测试文件位置

```
base/plugins/agent/tests/test_node_types.py
```

### 2.4 运行测试命令

```bash
# 运行所有测试
cd base/plugins/agent/tests
python -m pytest test_node_types.py -v

# 运行特定测试类
python -m pytest test_node_types.py::TestNodeTypes -v

# 运行特定测试方法
python -m pytest test_node_types.py::TestNodeTypes::test_start_node -v
```

---

## 三、流程控制节点测试

### 3.0 Parallel 节点测试

**节点类型**: `parallel`

**测试用例**: `test_parallel_node_with_branches`

**测试目的**: 验证并行节点能正确执行多个分支

**测试输入**:
```python
node_data = {
    "id": "parallel_001",
    "outputVar": "parallel_results",
    "branches": [
        {
            "name": "branch_a",
            "nodes": [
                {"id": "node_a1", "type": "code", "data": {"code": "result = 'A'"}}
            ]
        },
        {
            "name": "branch_b",
            "nodes": [
                {"id": "node_b1", "type": "code", "data": {"code": "result = 'B'"}}
            ]
        }
    ]
}
state = {
    "variables": {},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": [],
    "flow_data": {"nodes": [], "edges": []}
}
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_parallel_node(node_data, state)
```

**预期结果**:
- `"parallel_results"` in `result["variables"]`
- `"branch_a"` in `result["variables"]["parallel_results"]`
- `"branch_b"` in `result["variables"]["parallel_results"]`
- `result["variables"]["parallel_results_summary"]["total_branches"]` == `2`

**判定标准**: ✅ 通过

---

**测试用例**: `test_parallel_node_auto_build_branches`

**测试目的**: 验证并行节点能自动从边构建分支

**判定标准**: ✅ 通过

### 3.1 Start 节点测试

**节点类型**: `start`

**测试用例**: `test_start_node`

**测试目的**: 验证开始节点能正确设置开始时间变量

**测试输入**:
```python
node_data = {"label": "开始"}
state = {
    "variables": {},
    "input": {"text": "测试输入"},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_start_node(node_data, state)
```

**预期结果**:
- `result["variables"]` 包含 `start_time` 键
- `result` 包含 `execution_trace` 键

**判定标准**: ✅ 通过

---

### 3.2 End 节点测试

**节点类型**: `end`

**测试用例**: `test_end_node`

**测试目的**: 验证结束节点能正确设置结束时间

**测试输入**:
```python
node_data = {"label": "结束"}
state = {
    "variables": {},
    "input": {"text": "测试输入"},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_end_node(node_data, state)
```

**预期结果**:
- `result["output"]` 包含 `end_time` 键

**判定标准**: ✅ 通过

---

### 3.3 Condition 节点测试

#### 3.3.1 条件为真测试

**节点类型**: `condition`

**测试用例**: `test_condition_node_true`

**测试目的**: 验证条件表达式结果为真时正确处理

**测试输入**:
```python
node_data = {"condition": "{{score}} > 60", "label": "成绩判断"}
state = {
    "variables": {"score": 80},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_condition_node(node_data, state)
```

**预期结果**:
- `result["variables"]["condition_result"]["result"]` == `True`

**判定标准**: ✅ 通过

#### 3.3.2 条件为假测试

**节点类型**: `condition`

**测试用例**: `test_condition_node_false`

**测试目的**: 验证条件表达式结果为假时正确处理

**测试输入**:
```python
node_data = {"condition": "{{score}} > 60", "label": "成绩判断"}
state = {
    "variables": {"score": 50},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_condition_node(node_data, state)
```

**预期结果**:
- `result["variables"]["condition_result"]["result"]` == `False`

**判定标准**: ✅ 通过

---

### 3.4 Loop 节点测试

**节点类型**: `loop`

**测试用例**: `test_loop_node`

**测试目的**: 验证循环节点能正确设置循环变量

**测试输入**:
```python
node_data = {"loop_count": 3, "loop_var": "index"}
state = {
    "variables": {},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_loop_node(node_data, state)
```

**预期结果**:
- `result["variables"]["loop_iterations"]` == `[0, 1, 2]`

**判定标准**: ✅ 通过

---

### 3.5 Iteration 节点测试

**节点类型**: `iteration`

**测试用例**: `test_iteration_node`

**测试目的**: 验证迭代节点能正确遍历集合元素

**测试输入**:
```python
node_data = {"iteration_var": "item", "collection_var": "items"}
state = {
    "variables": {"items": ["a", "b", "c"]},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_iteration_node(node_data, state)
```

**预期结果**:
- `result["variables"]["item"]` == `"a"` (第一个元素)
- `result["variables"]["iteration_count"]` == `3` (集合长度)

**判定标准**: ✅ 通过

---

## 四、输入输出节点测试

### 4.0 Input 节点测试

**节点类型**: `input`

**测试用例**: `test_input_node`

**测试目的**: 验证输入节点状态设置

**测试输入**:
```python
node_data = {"label": "等待用户输入"}
state = {
    "variables": {},
    "input": {"text": "用户输入内容"},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
# input 节点使用 interrupt() 暂停执行
with patch('base.plugins.agent.services.langgraph_executor.interrupt') as mock_interrupt:
    mock_interrupt.side_effect = Exception("Interrupt for testing")
    try:
        await LangGraphExecutor._execute_input_node(node_data, state)
    except Exception:
        pass
```

**预期结果**:
- `"variables"` in `state`
- 恢复后 `"user_input"` in `state["variables"]`

**判定标准**: ✅ 通过

---

**测试用例**: `test_input_node_with_user_input`

**测试目的**: 验证输入节点能正确处理用户输入

**测试输入**:
```python
node_data = {"label": "等待用户输入"}
state = {
    "variables": {},
    "input": {"text": "测试输入"},
    ...
}
```

**预期结果**:
- `state["variables"]["user_input"]` == `"测试输入"`
- `state["variables"]["user_input_received"]` == `True`

**判定标准**: ✅ 通过

---

### 4.1 Output 节点测试

#### 4.1.1 使用自定义内容

**节点类型**: `output`

**测试用例**: `test_output_node_with_content`

**测试目的**: 验证输出节点使用自定义模板内容

**测试输入**:
```python
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
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_output_node(node_data, state)
```

**预期结果**:
- `result["output"]["result"]["text"]` == `"Hello World!"`

**判定标准**: ✅ 通过

#### 4.1.2 使用 LLM 输出

**节点类型**: `output`

**测试用例**: `test_output_node_with_llm_output`

**测试目的**: 验证输出节点使用 LLM 输出内容

**测试输入**:
```python
node_data = {"outputVar": "result", "label": "输出"}
state = {
    "variables": {"llm_output": {"response": "这是LLM的响应"}},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_output_node(node_data, state)
```

**预期结果**:
- `"result"` in `result["output"]`
- `"这是LLM的响应"` in `result["output"]["result"]["text"]`

**判定标准**: ✅ 通过

---

## 五、AI 能力节点测试

### 5.0 Agent 节点测试

**节点类型**: `agent`

**测试用例**: `test_agent_node`

**测试目的**: 验证智能体节点能正确设置智能体信息

**测试输入**:
```python
node_data = {"label": "智能体节点"}
state = {
    "variables": {"agent_id": "agent_001", "agent_name": "测试智能体"},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_agent_node(node_data, state)
```

**预期结果**:
- `"agent_info"` in `result["variables"]`
- `result["variables"]["agent_info"]["id"]` == `"agent_001"`

**判定标准**: ✅ 通过

---

### 5.1 LLM 节点测试

#### 5.1.1 普通模式

**节点类型**: `llm`

**测试用例**: `test_llm_node_mock`

**测试目的**: 验证 LLM 节点在模拟模式下正确处理响应

**测试输入**:
```python
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
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_llm_node(current_node, state)
```

**预期结果**:
- `"llm_output"` in `result["variables"]`
- 响应包含 `"模拟响应"` 或 `"错误"` 字样

**判定标准**: ✅ 通过

#### 5.2.2 流式模式

**节点类型**: `llm` (stream=True)

**测试用例**: `test_llm_node_streaming_mock`

**测试目的**: 验证 LLM 节点在流式模式下正确处理响应

**测试输入**:
```python
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
```

**执行方法**:
```python
async def mock_sse_yield(data):
    pass

result = await LangGraphExecutor._execute_llm_node_streaming(current_node, state, mock_sse_yield)
```

**预期结果**:
- `"llm_output"` in `result["variables"]`
- 响应包含 `"流式模拟响应"` 或 `"错误"` 字样

**判定标准**: ✅ 通过

#### 5.2.3 流式模式（带服务）

**节点类型**: `llm` (stream=True)

**测试用例**: `test_llm_node_streaming_with_service`

**测试目的**: 验证 LLM 节点流式响应时 SSE 数据正确传递

**测试输入**:
```python
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
```

**模拟服务**:
```python
async def mock_chat_stream(**kwargs):
    yield {"choices": [{"delta": {"content": "第一部分"}}]}
    yield {"choices": [{"delta": {"content": "第二部分"}}]}

mock_service.chat_stream = mock_chat_stream
```

**预期结果**:
- `result["variables"]["llm_output"]["response"]` 包含 `"第一部分第二部分"`
- `received_chunks` 长度为 2
- `received_chunks[0]["content"]` == `"第一部分"`
- `received_chunks[1]["content"]` == `"第二部分"`

**判定标准**: ✅ 通过

---

## 六、功能扩展节点测试

### 6.0 Skill 节点测试

**节点类型**: `skill`

**测试用例**: `test_skill_node`

**测试目的**: 验证技能节点能正确调用技能执行

**测试输入**:
```python
node_data = {"skill_id": 1, "label": "测试技能"}
state = {
    "variables": {"input": "测试输入"},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
with patch("base.plugins.agent.models.skill.Skill.get_or_none") as mock_get:
    mock_skill = MagicMock()
    mock_skill.name = "测试技能"
    mock_skill.implementation = "skill implementation"
    mock_get.return_value = mock_skill

    with patch("base.plugins.agent.services.skill_service.SkillService.execute_skill") as mock_exec:
        mock_exec.return_value = {"result": "技能执行成功"}
        result = await LangGraphExecutor._execute_skill_node(node_data, state)
```

**预期结果**:
- `"skill_result"` in `result["variables"]`

**判定标准**: ✅ 通过

---

**测试用例**: `test_skill_node_not_found`

**测试目的**: 验证技能节点在技能不存在时能正确处理

**测试输入**:
```python
node_data = {"skill_id": 999, "label": "不存在技能"}
state = {
    "variables": {},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**预期结果**:
- `"error"` in `result["variables"]["skill_result"]`

**判定标准**: ✅ 通过

---

### 6.1 Tool 节点测试

**节点类型**: `tool`

**测试用例**: `test_tool_node`

**测试目的**: 验证工具节点能正确执行工具

**测试输入**:
```python
node_data = {
    "tool_name": "weather_query",
    "tool_params": {"city": "{{city}}"},
    "label": "天气查询"
}
state = {
    "variables": {"city": "北京"},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
with patch("base.plugins.agent.tools.registry.ToolRegistry.get_tool") as mock_get_tool:
    mock_tool_class = MagicMock()
    mock_tool_class.execute = AsyncMock(return_value={"weather": "晴", "temperature": 25})
    mock_get_tool.return_value = mock_tool_class

    result = await LangGraphExecutor._execute_tool_node(node_data, state)
```

**预期结果**:
- `"weather_query"` in `result["variables"]`
- `result["variables"]["tool_result"]["weather"]` == `"晴"`

**判定标准**: ✅ 通过

---

**测试用例**: `test_tool_node_not_found`

**测试目的**: 验证工具节点在工具不存在时能正确处理

**判定标准**: ✅ 通过

---

### 6.2 HTTP 节点测试

**节点类型**: `http`

**测试用例**: `test_http_node_get_request`

**测试目的**: 验证 HTTP 节点能正确发送 GET 请求

**测试输入**:
```python
node_data = {
    "url": "https://api.example.com/data/{{id}}",
    "method": "GET",
    "outputVar": "http_result"
}
state = {
    "variables": {"id": "123"},
    "input": {},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
with patch("aiohttp.ClientSession") as mock_session_class:
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.text = AsyncMock(return_value='{"data": "test"}')

    mock_session = MagicMock()
    mock_session.request = MagicMock(return_value=mock_response.__aenter__.return_value)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session_class.return_value = mock_session

    result = await LangGraphExecutor._execute_http_node(node_data, state)
```

**预期结果**:
- `"http_result"` in `result["variables"]`

**判定标准**: ✅ 通过

---

**测试用例**: `test_http_node_post_request`

**测试目的**: 验证 HTTP 节点能正确发送 POST 请求

**判定标准**: ✅ 通过

---

**测试用例**: `test_http_node_error`

**测试目的**: 验证 HTTP 节点在请求错误时能正确处理

**判定标准**: ✅ 通过

---

### 6.3 Code 节点测试

**节点类型**: `code`

**测试用例**: `test_code_node`

**测试目的**: 验证代码节点能正确执行 Python 代码

**测试输入**:
```python
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
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_code_node(node_data, state)
```

**预期结果**:
- `result["variables"]["result"]` == `3`

**判定标准**: ✅ 通过

---

### 6.4 Template 节点测试

**节点类型**: `template`

**测试用例**: `test_template_node`

**测试目的**: 验证模板节点能正确进行变量替换

**测试输入**:
```python
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
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_template_node(node_data, state)
```

**预期结果**:
- `result["variables"]["greeting"]` == `"Hello Alice, today is Monday"`

**判定标准**: ✅ 通过

---

## 七、数据处理节点测试

### 7.1 Variable Assigner 节点测试

**节点类型**: `variable_assigner`

**测试用例**: `test_variable_assigner_node`

**测试目的**: 验证变量赋值节点能正确处理变量引用

**测试输入**:
```python
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
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_variable_assigner_node(node_data, state)
```

**预期结果**:
- `result["variables"]["user_name"]` == `"Bob"`

**判定标准**: ✅ 通过

---

### 7.2 Variable Aggregator 节点测试

**节点类型**: `variable_aggregator`

**测试用例**: `test_variable_aggregator_node`

**测试目的**: 验证变量聚合器节点能正确聚合多个变量

**测试输入**:
```python
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
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_variable_aggregator_node(node_data, state)
```

**预期结果**:
- `result["variables"]["user_info"]` == `{"name": "Charlie", "age": 30}`

**判定标准**: ✅ 通过

---

### 7.3 Parameter Extractor 节点测试

**节点类型**: `parameter_extractor`

**测试用例**: `test_parameter_extractor_node`

**测试目的**: 验证参数提取节点能正确从对象中提取字段

**测试输入**:
```python
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
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_parameter_extractor_node(node_data, state)
```

**预期结果**:
- `result["variables"]["query"]` == `"test"`

**判定标准**: ✅ 通过

---

### 7.4 JSON Extractor 节点测试

**节点类型**: `json_extractor`

**测试用例**: `test_json_extractor_node`

**测试目的**: 验证 JSON 提取节点能正确解析 JSON 字符串

**测试输入**:
```python
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
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_json_extractor_node(node_data, state)
```

**预期结果**:
- `result["variables"]["parsed_json"]` == `{"key": "value"}`

**判定标准**: ✅ 通过

---

### 7.5 Document Extractor 节点测试

**节点类型**: `document_extractor`

**测试用例**: `test_document_extractor_node`

**测试目的**: 验证文档提取节点能正确提取文档字段

**测试输入**:
```python
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
```

**执行方法**:
```python
result = await LangGraphExecutor._execute_document_extractor_node(node_data, state)
```

**预期结果**:
- `"extracted_data"` in `result["variables"]`
- `"title"` in `result["variables"]["extracted_data"]`

**判定标准**: ✅ 通过

---

## 八、辅助函数测试

### 8.1 消息构建函数测试

**测试用例**: `test_build_messages`

**测试目的**: 验证消息构建函数能正确处理模板变量替换

**测试输入**:
```python
prompt = "Hello {{name}}"
node_data = {"system_prompt": "你是一个助手"}
state = {
    "variables": {"name": "World"},
    "input": {"text": "用户消息"},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
result_prompt, messages, input_text = await LangGraphExecutor._build_messages(prompt, node_data, state)
```

**预期结果**:
- `"Hello World"` in `result_prompt`
- `len(messages)` >= 2
- `input_text` == `"用户消息"`

**判定标准**: ✅ 通过

---

### 8.2 响应解析函数测试

**测试用例**: `test_parse_and_set_response`

**测试目的**: 验证响应解析函数能正确解析 JSON 响应

**测试输入**:
```python
llm_response = '{"key": "value", "response": "测试响应"}'
node_data = {"outputVar": "result"}
state = {
    "variables": {},
    "input": {"text": "输入"},
    "output": {},
    "messages": [],
    "execution_trace": []
}
```

**执行方法**:
```python
result = await LangGraphExecutor._parse_and_set_response(
    llm_response, node_data, state, "test-model", "prompt"
)
```

**预期结果**:
- `"result"` in `result["variables"]`
- `result["variables"]["result"]["key"]` == `"value"`

**判定标准**: ✅ 通过

---

## 九、测试覆盖汇总

### 9.1 测试统计

| 节点类型 | 测试数量 | 通过状态 |
|---------|---------|---------|
| start | 1 | ✅ |
| end | 1 | ✅ |
| condition | 3 | ✅ |
| loop | 2 | ✅ |
| iteration | 2 | ✅ |
| parallel | 2 | ✅ |
| input | 2 | ✅ |
| output | 4 | ✅ |
| agent | 1 | ✅ |
| llm | 4 | ✅ |
| skill | 2 | ✅ |
| tool | 2 | ✅ |
| http | 3 | ✅ |
| code | 3 | ✅ |
| template | 2 | ✅ |
| variable_assigner | 2 | ✅ |
| variable_aggregator | 2 | ✅ |
| parameter_extractor | 2 | ✅ |
| json_extractor | 3 | ✅ |
| document_extractor | 2 | ✅ |
| 辅助函数/其他 | 5 | ✅ |
| **总计** | **50+** | **✅ 100%** |

### 9.2 新增节点测试覆盖

以下节点测试已从"未覆盖"更新为"已覆盖"：

| 节点类型 | 覆盖状态 | 测试用例 |
|---------|---------|---------|
| `input` | ✅ 已覆盖 | test_input_node, test_input_node_with_user_input |
| `skill` | ✅ 已覆盖 | test_skill_node, test_skill_node_not_found |
| `tool` | ✅ 已覆盖 | test_tool_node, test_tool_node_not_found |
| `http` | ✅ 已覆盖 | test_http_node_get_request, test_http_node_post_request, test_http_node_error |
| `parallel` | ✅ 已覆盖 | test_parallel_node_with_branches, test_parallel_node_auto_build_branches |

---

## 十、测试最佳实践

### 10.1 编写测试用例

1. 每个测试方法应专注于一个功能点
2. 使用清晰的测试方法命名：`test_{节点类型}_{场景}`
3. 提供详细的测试输入和预期输出
4. 添加必要的 mock 以隔离外部依赖

### 10.2 运行测试

1. 开发过程中频繁运行相关测试
2. 提交代码前运行完整测试套件
3. 关注测试覆盖率报告

### 10.3 维护测试

1. 当节点逻辑变更时及时更新测试
2. 新增节点类型时补充测试用例
3. 定期审查和改进测试覆盖

---

## 十一、相关文档

- [智能体节点类型详解](../agent_node_types.md)
- [LangGraph 笔记](../langgraph笔记.md)
- [测试代码位置](../../base/plugins/agent/tests/test_node_types.py)
