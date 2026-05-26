# Agent 节点类型测试用例说明

## 概述

本测试套件用于验证 Agent 系统中各种节点类型的输入输出是否符合预期逻辑。测试覆盖了 LangGraph 执行器支持的所有节点类型。

## 测试环境

- Python 3.10+
- pytest 7.0+
- 依赖：`pytest`, `asyncio`, `unittest.mock`

## 测试覆盖的节点类型

### 1. 基础节点

| 节点类型 | 测试方法 | 测试目的 |
|---------|---------|---------|
| `start` | `test_start_node` | 验证开始节点正常启动工作流 |
| `end` | `test_start_node` | 验证结束节点正确终止工作流 |
| `input` | `test_input_node` | 验证输入节点正确获取用户输入并存储到变量 |
| `output` | `test_output_node` | 验证输出节点正确输出结果 |

### 2. 业务逻辑节点

| 节点类型 | 测试方法 | 测试目的 |
|---------|---------|---------|
| `llm` | `test_llm_node` | 验证大模型节点正确调用 |
| `condition` | `test_condition_node` | 验证条件节点正确进行分支判断 |
| `code` | `test_code_node` | 验证代码执行节点正确执行 Python 代码 |
| `template` | `test_template_node` | 验证模板渲染节点正确渲染模板 |

### 3. 数据处理节点

| 节点类型 | 测试方法 | 测试目的 |
|---------|---------|---------|
| `variable_assigner` | `test_variable_assigner_node` | 验证变量赋值节点正确设置变量 |
| `parameter_extractor` | `test_parameter_extractor_node` | 验证参数提取节点正确提取用户输入中的参数 |
| `json_extractor` | `test_json_extractor_node` | 验证 JSON 提取节点正确解析 JSON |
| `variable_aggregator` | `test_variable_aggregator_node` | 验证变量聚合节点正确聚合变量 |

### 4. 外部交互节点

| 节点类型 | 测试方法 | 测试目的 |
|---------|---------|---------|
| `http` | `test_http_node` | 验证 HTTP 节点正确发起请求 |
| `loop` | `test_loop_and_iteration_nodes` | 验证循环节点正确控制循环流程 |
| `iteration` | `test_loop_and_iteration_nodes` | 验证迭代节点正确处理迭代项 |

### 5. 复杂工作流

| 测试方法 | 测试目的 |
|---------|---------|
| `test_complex_workflow` | 验证多个节点组合的完整工作流正确执行 |

## 测试用例设计

### 输入输出验证

每个测试用例验证以下核心逻辑：

1. **执行成功**：`result["success"]` 应为 `True`
2. **输出存在**：`result["output"]` 应存在且不为空
3. **变量传递**：`result["variables"]` 应包含预期的变量
4. **节点交互**：节点之间的数据传递正确

### Mock 策略

- **LLM 节点**：使用 `unittest.mock.patch` 模拟 LLM 调用，避免实际 API 调用
- **Agent 对象**：使用 `MagicMock` 创建模拟的 Agent 对象
- **执行器**：直接使用真实的 `LangGraphExecutor`，但传入模拟的 Agent

## 运行测试

### 安装依赖

```bash
pip install pytest
```

### 运行所有测试

```bash
cd d:\Programs\fastapi\aipaneladmin
python -m pytest base/plugins/agent/tests/test_node_types.py -v
```

### 运行特定测试

```bash
# 运行特定节点类型测试
python -m pytest base/plugins/agent/tests/test_node_types.py::TestNodeTypes::test_condition_node -v

# 运行多个测试
python -m pytest base/plugins/agent/tests/test_node_types.py::TestNodeTypes::test_input_node base/plugins/agent/tests/test_node_types.py::TestNodeTypes::test_output_node -v
```

### 生成测试报告

```bash
# 生成详细报告
python -m pytest base/plugins/agent/tests/test_node_types.py -v --tb=long

# 生成简洁报告
python -m pytest base/plugins/agent/tests/test_node_types.py -v --tb=short

# 生成 JUnit 格式报告（用于 CI/CD）
python -m pytest base/plugins/agent/tests/test_node_types.py --junitxml=test-results.xml
```

## 测试文件结构

```
base/plugins/agent/tests/
├── README.md              # 测试说明文档
└── test_node_types.py     # 测试用例代码
```

## 测试用例示例

### 输入节点测试

```python
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
    assert result["variables"].get("user_input") == "用户输入内容"
```

## CI/CD 集成

可以将测试集成到 CI/CD 流程中：

```yaml
# .github/workflows/agent-test.yml
name: Agent Node Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest
          pip install -r requirements.txt
      - name: Run tests
        run: python -m pytest base/plugins/agent/tests/test_node_types.py --junitxml=test-results.xml
      - name: Upload test results
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: test-results.xml
```

## 扩展测试用例

如需添加新的节点类型测试，请按照以下模式：

1. 在 `TestNodeTypes` 类中添加新的测试方法
2. 定义测试用的工作流图数据
3. 设置 mock agent 的 workflow
4. 执行 agent
5. 验证结果

```python
def test_new_node_type(self, executor, mock_agent):
    """测试新节点类型"""
    graph_data = {
        "nodes": [
            {"id": "start", "type": "start", "label": "开始"},
            {"id": "new_node", "type": "new_node_type", "label": "新节点", "param": "value"},
            {"id": "end", "type": "end", "label": "结束"}
        ],
        "edges": [
            {"source": "start", "target": "new_node"},
            {"source": "new_node", "target": "end"}
        ]
    }
    
    mock_agent.workflow = json.dumps(graph_data)
    
    result = asyncio.run(executor.execute_agent(
        input_data={"text": "测试"},
        actor={"type": "user", "id": "test_user"},
        execution_id="test_execution"
    ))
    
    assert result["success"] is True
    # 添加更多断言...
```

## 注意事项

1. 测试需要正确配置数据库连接（如使用）
2. 某些节点类型（如 HTTP）可能需要网络连接
3. LLM 节点测试使用 mock，不会产生实际 API 费用
4. 建议在测试环境中运行，不要在生产环境执行

## 维护说明

- 当添加新的节点类型时，应同步添加对应的测试用例
- 当修改节点逻辑时，应更新相关测试用例
- 定期运行测试确保所有节点正常工作

---

**文档版本**: v1.0  
**创建日期**: 2026-05-26  
**适用模块**: Agent 插件