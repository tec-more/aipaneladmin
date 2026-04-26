# 技能使用完全指南

---

## 📌 目录
1. [何时使用技能](#何时使用技能)
2. [如何使用技能](#如何使用技能)
3. [大模型如何匹配技能](#大模型如何匹配技能)
4. [创建自定义技能](#创建自定义技能)
5. [最佳实践](#最佳实践)

---

## ✅ 何时使用技能

### 1. 固定的业务逻辑
当你有明确、不会频繁变化的操作时，使用技能：
- 文档翻译
- 数据库查询
- 文件操作
- 第三方 API 调用

### 2. 需要精确控制的操作
- 发送邮件（固定的 SMTP 配置）
- 数据格式化（固定的格式要求）
- 权限验证

### 3. 性能敏感的场景
- 直接执行 Python 代码，比 LLM 生成更可靠
- 可以缓存和复用技能执行结果

---

## 🚀 如何使用技能

### 方式一：在流程图中使用（推荐）

#### 步骤1：创建技能节点
在 `graph_definition` 中配置 skill 类型的节点：

```json
{
  "nodes": [
    {
      "id": "my_skill_node",
      "type": "skill",
      "data": {
        "label": "翻译文档",
        "skill_type": "slang_translation",  // 技能类型
        "input_variable": "text_to_translate",
        "output_variable": "translated_text"
      },
      "position": {"x": 200, "y": 300}
    }
  ],
  "edges": [...]
}
```

#### 步骤2：连接到执行流程
```json
{
  "edges": [
    {
      "id": "edge_input_to_skill",
      "source": "input_node",
      "target": "my_skill_node"
    },
    {
      "id": "edge_skill_to_output",
      "source": "my_skill_node",
      "target": "output_node"
    }
  ]
}
```

---

### 方式二：在代码中直接调用

```python
from base.plugins.agent.skills.registry import SkillRegistry

# 获取技能
skill_class = SkillRegistry.get_skill("slang_translation")

# 执行技能
result = skill_class.execute({
    "text": "Hello world!"
})

if result.get("success"):
    print(result.get("translation"))
else:
    print(result.get("message"))
```

---

## 🤖 大模型如何匹配技能

### 重要说明！ ⚠️
**目前项目中，大模型并不自动匹配技能！**

技能调用是通过以下方式：
1. **完全由流程图配置指定**
2. 节点类型 = `skill` 时，执行对应的技能
3. 技能类型 = `skill_type` 字段的值

---

### 未来要实现自动匹配的话，建议方案

如果你希望大模型自主选择技能，可以按以下步骤：

#### 方案 A：使用 Function Calling 提示词

```python
# 在 LLM 节点中这样配置提示词
system_prompt = """你是一个智能助手，当用户请求时，你可以选择以下技能：

1. 文档翻译 (skill: slang_translation) - 翻译各种语言
2. 任务分解 (skill: task_decomposer) - 拆解任务

请选择合适的技能，并在回答中标注技能名称。"""
```

#### 方案 B：在流程图中添加技能选择逻辑

```json
{
  "nodes": [
    {
      "id": "skill_selector",
      "type": "llm",
      "data": {
        "label": "选择技能",
        "system_prompt": "请根据用户输入，选择合适的技能..."
      }
    },
    {
      "id": "skill_router",
      "type": "condition",
      "data": {
        "label": "路由到对应技能"
      }
    }
  ],
  "edges": [...],
  "skills": [
    {
      "type": "skill",
      "skill": "slang_translation",
      "config": {}
    }
  ]
}
```

---

## 🛠️ 创建自定义技能

### 1. 继承 BaseSkill

```python
from base.plugins.agent.skills.base import BaseSkill
from base.plugins.agent.skills.registry import SkillRegistry


class MyCustomSkill(BaseSkill):
    """我的自定义技能"""
    
    @staticmethod
    def execute(params: dict) -> dict:
        """执行技能"""
        try:
            # 获取参数
            input_text = params.get("text", "")
            
            # 执行业务逻辑
            result = f"处理结果: {input_text}"
            
            # 返回格式
            return {
                "success": True,
                "result": result,
                "message": "执行成功"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"执行失败: {str(e)}"
            }


# 注册技能
SkillRegistry.register("my_custom_skill", MyCustomSkill)
```

### 2. 保存到对应目录
```
base/plugins/agent/skills/my_custom_skill.py
```

---

## 💡 最佳实践

### 1. 技能设计原则

| 原则 | 说明 |
|------|------|
| 单一职责 | 一个技能只做一件事 |
| 无状态 | 技能执行不依赖外部状态 |
| 幂等性 | 重复执行结果相同 |

### 2. 流程图示例：任务分解 + 技能调用

```json
{
  "nodes": [
    {
      "id": "input",
      "type": "start",
      "data": {"label": "开始"}
    },
    {
      "id": "decompose",
      "type": "llm",
      "data": {
        "label": "任务分解",
        "system_prompt": "请分解任务..."
      }
    },
    {
      "id": "translate",
      "type": "skill",
      "data": {
        "label": "翻译结果",
        "skill_type": "slang_translation",
        "output_variable": "translated"
      }
    },
    {
      "id": "output",
      "type": "output",
      "data": {"label": "输出"}
    }
  ],
  "edges": [
    {"source": "input", "target": "decompose"},
    {"source": "decompose", "target": "translate"},
    {"source": "translate", "target": "output"}
  ]
}
```

---

## 📊 对比总结

| 项 | 说明 |
|----|------|
| **技能特点** | 固定的、可靠的、可重用的操作 |
| **何时用技能** | 明确的业务逻辑、精确控制、性能敏感 |
| **何时不用技能** | 灵活的、创造性的任务 → 用 LLM 节点 |
| **大模型匹配** | ❌ 目前不支持，需在流程图配置 |
| **自动匹配建议** | 使用 LLM + Condition 节点实现选择逻辑 |

---

## 📝 已删除内容说明

在本次清理中，我们删除了以下未使用的内容：
- `ReActAgentService` 类（未被任何代码调用）
- `reasoning_strategy` 字段（在模型、API、Schema 中都已移除）

项目现在更简洁，完全基于 `LangGraphExecutor` + `graph_definition` 配置来实现各种流程（包括 ReAct 模式）！
