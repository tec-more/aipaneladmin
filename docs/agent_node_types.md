# 智能体节点类型详解

## 概述

智能体工作流引擎支持多种节点类型，用于构建复杂的业务流程。所有节点类型都由 `LangGraphExecutor` 统一执行，通过 `_execute_node_with_logging` 方法分发到对应的执行器。

---

## 节点类型分类

### 1. 流程控制节点

| 节点类型 | 图标 | 作用 | 使用场景 |
|---------|------|------|---------|
| `start` | ▶️ | 工作流入口，记录开始时间 | 工作流起始点 |
| `end` | ⏹️ | 工作流结束，记录结束时间 | 工作流终点 |
| `condition` | 🔀 | 条件判断，控制流程分支 | 分支逻辑、路由选择 |
| `loop` | 🔄 | 循环控制，设置循环次数 | 重复执行某段流程 |
| `iteration` | 🔁 | 迭代器，遍历集合元素 | 批量处理数据 |
| `parallel` | 🔗 | 并行执行多个分支 | 同时调用多个工具/API |

#### 1.1 Start 节点（开始节点）

**作用**：标记工作流的起始点，初始化执行上下文。

**执行逻辑**：
```python
# 设置开始时间戳
state["variables"]["start_time"] = datetime.now().isoformat()
```

**配置参数**：无需额外配置

**使用示例**：
```json
{
  "id": "node_start",
  "type": "start",
  "data": {
    "label": "开始"
  }
}
```

#### 1.2 End 节点（结束节点）

**作用**：标记工作流的结束点，记录结束时间。

**执行逻辑**：
```python
state["output"]["end_time"] = datetime.now().isoformat()
```

**配置参数**：无需额外配置

**使用示例**：
```json
{
  "id": "node_end",
  "type": "end",
  "data": {
    "label": "结束"
  }
}
```

#### 1.3 Condition 节点（条件判断节点）

**作用**：根据条件表达式的结果控制流程走向，支持多条条件边和默认边。

**执行逻辑**：
- 支持模板语法 `{{variable}}` 引用变量
- 使用安全求值执行条件表达式
- 将结果存入 `condition_result` 变量

**配置参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `condition` | string | 条件表达式，如 `{{score}} > 60` |

**输出变量**：
```python
state["variables"]["condition_result"] = {
    "condition": "条件表达式",
    "result": True/False,
    "error": "错误信息（如有）"
}
```

**使用示例**：
```json
{
  "id": "node_condition",
  "type": "condition",
  "data": {
    "label": "判断成绩是否及格",
    "condition": "{{score}} >= 60"
  }
}
```

**条件边配置**：
```json
// 条件边
{
  "source": "node_condition",
  "target": "node_pass",
  "condition": "{{condition_result.result}} == true",
  "priority": 1
}
// 默认边（无条件时使用）
{
  "source": "node_condition",
  "target": "node_fail",
  "priority": 0
}
```

#### 1.4 Loop 节点（循环节点）

**作用**：设置循环参数，控制重复执行次数。

**执行逻辑**：
```python
# 设置循环次数和当前索引
state["variables"]["loop_iterations"] = [0, 1, 2]  # 循环次数列表
state["variables"][loop_var] = 0  # 当前循环索引
```

**配置参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `loop_count` | int | 3 | 循环次数 |
| `loop_var` | string | "loop_index" | 存储当前索引的变量名 |

**使用示例**：
```json
{
  "id": "node_loop",
  "type": "loop",
  "data": {
    "label": "循环3次",
    "loop_count": 3,
    "loop_var": "index"
  }
}
```

#### 1.5 Iteration 节点（迭代节点）

**作用**：遍历集合，依次处理每个元素。

**执行逻辑**：
```python
collection = state["variables"][collection_var]  # 获取集合
state["variables"][iteration_var] = collection[0]  # 设置第一个元素
state["variables"]["iteration_index"] = 0  # 当前索引
state["variables"]["iteration_count"] = len(collection)  # 元素总数
```

**配置参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `iteration_var` | string | "item" | 存储当前元素的变量名 |
| `collection_var` | string | "items" | 集合变量名 |

**使用示例**：
```json
{
  "id": "node_iteration",
  "type": "iteration",
  "data": {
    "label": "遍历商品列表",
    "iteration_var": "product",
    "collection_var": "products"
  }
}
```

---

### 2. 输入输出节点

| 节点类型 | 图标 | 作用 | 使用场景 |
|---------|------|------|---------|
| `input` | 📥 | 暂停等待用户输入 | 需要人工交互的流程 |
| `output` | 📤 | 输出结果，生成最终响应 | 工作流结果输出 |

#### 2.1 Input 节点（输入节点）

**作用**：暂停工作流执行，等待用户输入后继续。

**执行逻辑**：
```python
interrupt("等待用户输入")  # 暂停执行，保存检查点
# 恢复后执行
state["variables"]["user_input"] = input_text
state["variables"]["user_input_received"] = True
```

**配置参数**：无需额外配置

**使用示例**：
```json
{
  "id": "node_input",
  "type": "input",
  "data": {
    "label": "等待用户确认"
  }
}
```

#### 2.2 Output 节点（输出节点）

**作用**：将工作流执行结果输出，支持模板变量替换。

**执行逻辑**：
- 优先使用 `outputContent` 模板
- 支持变量引用 `{{variable}}`
- 自动从 `llm_output`、`final_report` 等变量提取内容

**配置参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `outputVar` | string | "result" | 输出变量名 |
| `outputContent` | string | "" | 输出内容模板 |

**输出变量**：
```python
state["output"][outputVar] = {"text": "输出内容"}
```

**使用示例**：
```json
{
  "id": "node_output",
  "type": "output",
  "data": {
    "label": "输出结果",
    "outputVar": "final_result",
    "outputContent": "尊敬的{{user_name}}，您的订单{{order_id}}已完成！"
  }
}
```

---

### 3. AI 能力节点

| 节点类型 | 图标 | 作用 | 使用场景 |
|---------|------|------|---------|
| `llm` | 🤖 | 调用大语言模型 | 生成文本、分析、决策 |
| `agent` | 👤 | 智能体信息设置 | 设置当前智能体上下文 |

#### 3.1 LLM 节点（大语言模型节点）

**作用**：调用配置的大语言模型，支持流式和非流式输出。

**执行逻辑**：
1. 预加载模型资源（模型ID、API密钥、端点）
2. 构建消息（系统提示、用户输入、历史记忆）
3. 调用LLM服务
4. 解析响应并设置输出变量

**配置参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `prompt` | string | "" | 提示词模板 |
| `model_id` | string | - | 模型ID（必填） |
| `temperature` | float | 0.7 | 温度参数 |
| `max_tokens` | int | None | 最大响应长度 |
| `stream` | bool/bool | false | 是否流式输出 |
| `system_prompt` | string | "" | 系统提示词 |
| `skill_ids` | array | [] | 绑定的技能ID列表 |
| `outputVar` | string | "llm_output" | 输出变量名 |

**输出变量**：
```python
state["variables"]["llm_output"] = {
    "prompt": "原始提示词",
    "model": "模型名称",
    "response": "响应内容"
}
# 如果响应是JSON格式，会自动解析
state["variables"]["llm_output"] = {"key": "value", ...}
```

**使用示例**：
```json
{
  "id": "node_llm",
  "type": "llm",
  "data": {
    "label": "总结助手",
    "prompt": "请总结以下内容：{{input}}",
    "model_id": "model-001",
    "temperature": 0.3,
    "stream": true,
    "system_prompt": "你是一个专业的文本总结助手"
  }
}
```

#### 3.2 Agent 节点（智能体节点）

**作用**：设置当前智能体的上下文信息。

**执行逻辑**：
```python
state["variables"]["agent_info"] = {
    "id": agent_id,
    "name": agent_name,
    "description": ""
}
```

**配置参数**：无需额外配置（自动从上下文中获取）

**使用示例**：
```json
{
  "id": "node_agent",
  "type": "agent",
  "data": {
    "label": "当前智能体"
  }
}
```

---

### 4. 功能扩展节点

| 节点类型 | 图标 | 作用 | 使用场景 |
|---------|------|------|---------|
| `skill` | 🎯 | 执行预定义技能 | 调用组合工具能力 |
| `tool` | 🔧 | 执行单个工具 | 调用外部API或服务 |
| `http` | 🌐 | 发送HTTP请求 | 调用第三方API |
| `code` | 📝 | 执行Python代码 | 自定义逻辑处理 |
| `template` | 📄 | 模板渲染 | 文本模板变量替换 |

#### 4.1 Skill 节点（技能节点）

**作用**：执行预定义的技能，技能可以绑定多个工具。

**执行逻辑**：
1. 根据 `skill_id` 查询技能配置
2. 调用 `SkillService.execute_skill()` 执行
3. 将结果存入 `skill_result`

**配置参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `skill_id` | int/string | 技能ID（必填） |

**输出变量**：
```python
state["variables"]["skill_result"] = {"result": "..."}
```

**使用示例**：
```json
{
  "id": "node_skill",
  "type": "skill",
  "data": {
    "label": "机票预订技能",
    "skill_id": 1
  }
}
```

#### 4.2 Tool 节点（工具节点）

**作用**：执行单个注册的工具。

**执行逻辑**：
1. 根据 `tool_name` 从 `ToolRegistry` 获取工具类
2. 解析参数（支持变量引用）
3. 执行工具并返回结果

**配置参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `tool_name` | string | 工具名称（必填） |
| `tool_params` | dict | 工具参数 |
| `params` | dict | 附加参数（同tool_params） |

**参数支持变量引用**：
```json
{
  "tool_params": {
    "query": "{{search_query}}",
    "limit": "{{page_size}}"
  }
}
```

**输出变量**：
```python
state["variables"][tool_name] = {"result": "..."}
state["variables"]["tool_result"] = {"result": "..."}
```

**使用示例**：
```json
{
  "id": "node_tool",
  "type": "tool",
  "data": {
    "label": "天气查询",
    "tool_name": "weather_query",
    "tool_params": {
      "city": "{{city}}",
      "date": "{{query_date}}"
    }
  }
}
```

#### 4.3 HTTP 节点（HTTP请求节点）

**作用**：发送HTTP请求，调用外部API。

**执行逻辑**：
1. 变量替换（URL、headers、body）
2. 使用 `aiohttp` 发送请求
3. 返回响应状态和数据

**配置参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | "" | 请求URL（必填） |
| `method` | string | "GET" | HTTP方法 |
| `headers` | dict | {} | 请求头 |
| `body` | string/dict | "" | 请求体 |

**输出变量**：
```python
state["variables"]["http_response"] = {
    "status": 200,
    "data": {"response": "..."}
}
```

**使用示例**：
```json
{
  "id": "node_http",
  "type": "http",
  "data": {
    "label": "调用用户API",
    "url": "https://api.example.com/users/{{user_id}}",
    "method": "GET",
    "headers": {
      "Authorization": "Bearer {{access_token}}"
    }
  }
}
```

#### 4.4 Code 节点（代码节点）

**作用**：执行自定义Python代码，实现复杂逻辑。

**执行逻辑**：
```python
exec(code, {}, local_vars)  # 安全执行代码
state["variables"].update(local_vars)  # 合并结果
```

**配置参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `code` | string | Python代码（必填） |

**可用变量**：代码中可直接使用 `variables` 字典

**输出变量**：代码中定义的所有变量都会合并到 `state["variables"]`

**使用示例**：
```json
{
  "id": "node_code",
  "type": "code",
  "data": {
    "label": "数据处理",
    "code": "total = variables.get('price', 0) * variables.get('quantity', 1)\ndiscount = total * 0.1\nvariables['final_price'] = total - discount"
  }
}
```

#### 4.5 Template 节点（模板节点）

**作用**：渲染文本模板，支持变量替换。

**执行逻辑**：
```python
# 变量替换
for key, value in variables.items():
    template = template.replace(f"{{{{{key}}}}}", str(value))
state["variables"][output_var] = template
```

**配置参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `template` | string | "" | 模板文本 |
| `outputVar` | string | "template_output" | 输出变量名 |

**使用示例**：
```json
{
  "id": "node_template",
  "type": "template",
  "data": {
    "label": "生成邮件内容",
    "template": "尊敬的{{customer_name}}：\n\n您的订单{{order_no}}已发货，预计{{delivery_date}}送达。\n\n感谢您的购买！",
    "outputVar": "email_content"
  }
}
```

---

### 5. 数据处理节点

| 节点类型 | 图标 | 作用 | 使用场景 |
|---------|------|------|---------|
| `variable_assigner` | ⚙️ | 变量赋值 | 设置变量值 |
| `variable_aggregator` | 📊 | 变量聚合 | 合并多个变量 |
| `parameter_extractor` | 🔍 | 参数提取 | 从对象中提取字段 |
| `json_extractor` | 📋 | JSON解析 | 解析JSON字符串 |
| `document_extractor` | 📄 | 文档提取 | 提取文档字段 |

#### 5.1 Variable Assigner 节点（变量赋值节点）

**作用**：设置或更新变量值，支持变量引用。

**执行逻辑**：
```python
if value.startswith("{{") and value.endswith("}}"):
    var_name = value[2:-2]
    value = variables.get(var_name, value)
state["variables"][variable_name] = value
```

**配置参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `variable_name` | string | 变量名（必填） |
| `value` | any | 变量值（支持 `{{var}}` 引用） |

**使用示例**：
```json
{
  "id": "node_assign",
  "type": "variable_assigner",
  "data": {
    "label": "设置用户ID",
    "variable_name": "user_id",
    "value": "{{input.user_id}}"
  }
}
```

#### 5.2 Variable Aggregator 节点（变量聚合器节点）

**作用**：将多个变量聚合到一个对象中。

**执行逻辑**：
```python
aggregated = {}
for var_name in input_vars:
    if var_name in variables:
        aggregated[var_name] = variables[var_name]
state["variables"][output_var] = aggregated
```

**配置参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_vars` | array | [] | 要聚合的变量名列表 |
| `outputVar` | string | "aggregated" | 输出变量名 |

**使用示例**：
```json
{
  "id": "node_aggregate",
  "type": "variable_aggregator",
  "data": {
    "label": "聚合用户信息",
    "input_vars": ["name", "email", "phone"],
    "outputVar": "user_profile"
  }
}
```

#### 5.3 Parameter Extractor 节点（参数提取节点）

**作用**：从字典类型变量中提取指定字段。

**执行逻辑**：
```python
source = state["variables"].get(source_var, "")
if isinstance(source, dict):
    state["variables"][parameter_name] = source.get(parameter_name, "")
else:
    state["variables"][parameter_name] = ""
```

**配置参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `source_var` | string | 源变量名（必填） |
| `parameter_name` | string | 要提取的字段名（必填） |

**使用示例**：
```json
{
  "id": "node_extract",
  "type": "parameter_extractor",
  "data": {
    "label": "提取城市",
    "source_var": "location",
    "parameter_name": "city"
  }
}
```

#### 5.4 JSON Extractor 节点（JSON提取节点）

**作用**：解析JSON字符串为对象。

**执行逻辑**：
```python
source = state["variables"].get(source_var, "")
if isinstance(source, str):
    source = json.loads(source)
state["variables"][output_var] = source
```

**配置参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `inputVariable` | string | "" | 源变量名 |
| `outputVar` | string | "extracted_json" | 输出变量名 |

**使用示例**：
```json
{
  "id": "node_json",
  "type": "json_extractor",
  "data": {
    "label": "解析API响应",
    "inputVariable": "http_response.data",
    "outputVar": "parsed_data"
  }
}
```

#### 5.5 Document Extractor 节点（文档提取节点）

**作用**：从文档内容中提取指定字段。

**执行逻辑**：
```python
document = state["variables"].get(document_var, "")
extracted = {}
for field in extract_fields:
    extracted[field] = document[:100]  # 提取前100字符
state["variables"]["extracted_data"] = extracted
```

**配置参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `document_var` | string | "document" | 文档变量名 |
| `extract_fields` | array | [] | 要提取的字段名列表 |

**使用示例**：
```json
{
  "id": "node_doc_extract",
  "type": "document_extractor",
  "data": {
    "label": "提取文档信息",
    "document_var": "article",
    "extract_fields": ["title", "summary", "author"]
  }
}
```

---

## 节点变量引用语法

所有节点都支持使用双花括号语法引用变量：

```
{{variable_name}}           - 引用顶层变量
{{variable.subfield}}       - 引用嵌套字段
{{params.query}}            - 引用params对象中的query字段
```

### 内置变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `agent_id` | string | 当前智能体ID |
| `agent_name` | string | 当前智能体名称 |
| `input` | dict | 用户输入数据 |
| `input.text` | string | 用户输入文本 |
| `llm_output` | dict | LLM节点输出 |
| `tool_result` | dict | 工具执行结果 |
| `skill_result` | dict | 技能执行结果 |
| `http_response` | dict | HTTP响应 |
| `condition_result` | dict | 条件判断结果 |

---

## 节点执行流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraphExecutor                        │
├─────────────────────────────────────────────────────────────┤
│  _execute_node_with_logging(current_node, state)           │
│       │                                                    │
│       ▼                                                    │
│  ┌───────────────────────────────────────┐                 │
│  │        根据 node_type 分发             │                 │
│  └───────────────────────────────────────┘                 │
│       │                                                    │
│       ├── start     → _execute_start_node()                │
│       ├── end       → _execute_end_node()                  │
│       ├── input     → _execute_input_node()                │
│       ├── output    → _execute_output_node()               │
│       ├── agent     → _execute_agent_node()                │
│       ├── llm       → _execute_llm_node()                 │
│       ├── skill     → _execute_skill_node()                │
│       ├── tool      → _execute_tool_node()                 │
│       ├── condition → _execute_condition_node()            │
│       ├── loop      → _execute_loop_node()                 │
│       ├── iteration → _execute_iteration_node()            │
│       ├── http      → _execute_http_node()                 │
│       ├── code      → _execute_code_node()                 │
│       ├── template  → _execute_template_node()             │
│       ├── variable_assigner      → _execute_..._node()     │
│       ├── variable_aggregator    → _execute_..._node()     │
│       ├── parameter_extractor    → _execute_..._node()     │
│       ├── json_extractor         → _execute_..._node()     │
│       └── document_extractor     → _execute_..._node()     │
│                                                            │
│       ▼                                                    │
│  更新 execution_trace                                      │
│  推送 SSE 事件（如配置）                                     │
│  返回更新后的 state                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 最佳实践

### 1. 流程设计原则
- 每个工作流应有且仅有一个 `start` 节点
- `end` 节点应作为流程终点
- 条件节点后应配置多条条件边和一条默认边

### 2. 变量命名规范
- 使用小写蛇形命名：`user_name` 而非 `userName`
- 避免使用保留字：`input`, `output`, `messages`, `variables`

### 3. 性能优化
- 对于重复使用的LLM节点，预加载资源可提升性能
- 避免在循环中频繁调用外部API
- 使用 `variable_aggregator` 减少变量传递

### 4. 错误处理
- 在关键节点后添加条件判断处理异常情况
- 使用 `code` 节点实现自定义错误处理逻辑
- 利用 `output` 节点统一输出格式

---

## 测试用例

测试文件位置：[base/plugins/agent/tests/test_node_types.py](file:///d:/Programs/fastapi/aipaneladmin/base/plugins/agent/tests/test_node_types.py)

包含以下 **21 个单元测试**：

| 测试类别 | 测试数量 | 覆盖节点 |
|---------|---------|---------|
| 流程控制节点 | 6 | start, end, condition(true/false), loop, iteration |
| 输入输出节点 | 2 | output(content/llm_output) |
| AI能力节点 | 3 | agent, llm(normal), llm(streaming) |
| 功能扩展节点 | 2 | code, template |
| 数据处理节点 | 5 | variable_assigner, variable_aggregator, parameter_extractor, json_extractor, document_extractor |
| 辅助函数 | 2 | build_messages, parse_and_set_response |

**运行测试**：
```bash
cd base/plugins/agent/tests
python -m pytest test_node_types.py -v
```

**测试覆盖说明**：

| 节点类型 | 测试状态 | 备注 |
|---------|---------|------|
| `start` | ✅ 已覆盖 | 测试开始时间设置 |
| `end` | ✅ 已覆盖 | 测试结束时间设置 |
| `condition` | ✅ 已覆盖 | 测试条件为真和假两种情况 |
| `loop` | ✅ 已覆盖 | 测试循环变量设置 |
| `iteration` | ✅ 已覆盖 | 测试迭代变量设置 |
| `input` | ⚠️ 未覆盖 | 需要LangGraph运行时上下文，建议集成测试 |
| `output` | ✅ 已覆盖 | 测试自定义内容和LLM输出两种模式 |
| `agent` | ✅ 已覆盖 | 测试智能体信息设置 |
| `llm` | ✅ 已覆盖 | 测试普通模式和流式模式 |
| `skill` | ⚠️ 未覆盖 | 需要数据库连接，建议集成测试 |
| `tool` | ⚠️ 未覆盖 | 需要工具注册，建议集成测试 |
| `http` | ⚠️ 未覆盖 | 需要网络连接，建议集成测试 |
| `code` | ✅ 已覆盖 | 测试Python代码执行 |
| `template` | ✅ 已覆盖 | 测试模板变量替换 |
| `variable_assigner` | ✅ 已覆盖 | 测试变量赋值 |
| `variable_aggregator` | ✅ 已覆盖 | 测试变量聚合 |
| `parameter_extractor` | ✅ 已覆盖 | 测试参数提取 |
| `json_extractor` | ✅ 已覆盖 | 测试JSON解析 |
| `document_extractor` | ✅ 已覆盖 | 测试文档提取 |

**未覆盖节点的测试建议**：

1. **`input` 节点**：需要在 LangGraph 运行时上下文中测试，建议添加集成测试
2. **`skill` 节点**：需要数据库连接和技能配置，建议添加集成测试
3. **`tool` 节点**：需要工具注册和工具实现，建议添加集成测试  
4. **`http` 节点**：需要网络连接，建议使用 mock server 进行测试
5. **`parallel` 节点**：需要异步测试环境，建议使用 asyncio 测试框架进行单元测试