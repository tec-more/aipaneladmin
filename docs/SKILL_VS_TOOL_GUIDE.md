# Skill（技能）架构设计

---

## 🎯 核心概念

| 概念 | 形式 | 本质 | 管理方式 |
|------|------|------|---------|
| **Tool（工具）** | Python 代码 (.py) | 单一、原子操作 | 代码层面管理 |
| **Skill（技能）** | Markdown 文档 | 约束 + 规范 + 思维流程 | **后台数据库管理** |

---

## 🔧 Tool（工具）

### 定义
工具是**单一、原子**的操作，用 Python 代码实现。

### 特点
- 单一职责：只做一件事
- 存储在 `tools/` 目录
- 需要手动编写代码

### 示例
```
tools/
├── base.py
├── registry.py
└── amazon/
    ├── order_query.py      # 只查订单
    └── fee_query.py         # 只查费用
```

---

## ⚡ Skill（技能）

### 定义
技能是一份**文档**，包含「约束 + 规范 + 思维流程」，由**后台管理员**通过数据库管理。

### 管理方式
- 技能内容存储在数据库的 `implementation` 字段（Markdown 格式）
- 通过后台界面创建、编辑、删除技能
- **不**存在代码级别的技能

### 数据库字段
| 字段 | 说明 |
|------|------|
| `name` | 技能名称 |
| `type` | 技能类型标识 |
| `description` | 技能描述 |
| `implementation` | 技能内容（Markdown 格式） |
| `status` | 状态（active/inactive） |

### 后台管理流程
```
后台界面
    ↓
创建/编辑技能（输入 Markdown 内容）
    ↓
保存到数据库的 implementation 字段
    ↓
运行时加载使用
```

---

## 📝 Skill 文档格式

在后台创建技能时，`implementation` 字段应包含完整的 Markdown 文档：

```markdown
# 订单查询处理技能

## 📋 技能概述
处理客户的订单查询请求，提供友好、专业的回复。

---

## 🎯 约束条件

### 1. 数据来源
- 只能调用 `amazon_order_query` 工具获取订单信息
- 只能调用 `amazon_fee_query` 工具获取费用信息
- 不能编造或猜测订单数据

### 2. 回复风格
- 保持专业、友好的语气
- 使用客户的语言（英文用户用英文，中文用户用中文）

---

## 📝 规范流程

### 步骤 1：理解用户意图
分析用户问题，确定需要查询什么

### 步骤 2：调用工具获取数据
根据用户需求，调用相应的工具

### 步骤 3：整理信息并生成回复
把工具返回的数据整理成友好的格式

---

## 💬 示例对话

### 示例 1：简单订单查询
**用户**：Where is my order 123-4567890-1234567?

**助手思考**：
1. 用户想知道特定订单的位置
2. 需要调用 `amazon_order_query` 工具
3. 参数：order_id=123-4567890-1234567

**助手回复**：
> Your order 123-4567890-1234567 has been shipped! 📦
> - Carrier: UPS
> - Tracking: 1Z999AA10123456784
> - Estimated delivery: May 10, 2026
```

---

## 🏗️ 运行时架构

```
用户问题
    ↓
[Skill] 从数据库加载 implementation 字段（Markdown）
    ↓
[Tool] 调用具体的工具（order_query, fee_query 等）
    ↓
LLM 按照 Skill 文档的要求组织回复
    ↓
用户收到友好、专业的回答
```

---

## 📊 Tool vs Skill 对比

| 维度 | Tool | Skill |
|------|------|-------|
| **形式** | .py 代码 | Markdown（存数据库） |
| **管理方式** | 代码层面 | **后台数据库管理** |
| **创建方式** | 写代码 | 后台输入/编辑 |
| **用途** | 执行具体操作 | 指导 LLM 如何思考和行动 |
| **维护** | 需要开发者修改代码 | 管理员可在后台修改 |

---

## 📁 目录结构

```
base/plugins/agent/
├── tools/                           # 🔧 Tools - 代码实现
│   ├── base.py
│   ├── registry.py
│   ├── __init__.py
│   └── amazon/
│       ├── order_query.py
│       └── fee_query.py
│
├── skills/                          # ⚡ Skills - 仅保留基础框架
│   ├── base.py                      # 技能基类
│   ├── registry.py                   # 技能注册表（从数据库加载）
│   └── __init__.py
│
├── models/
│   └── skill.py                     # 技能数据库模型
│
├── schemas/
│   └── skill.py                     # 技能数据结构定义
│
├── services/
│   └── skill_service.py             # 技能服务层
│
└── api/v1/
    └── skill.py                     # 技能 API 端点
```

---

## 🔌 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/skills` | GET | 获取技能列表 |
| `/skills` | POST | 创建新技能 |
| `/skills/{skill_id}` | GET | 获取技能详情 |
| `/skills/{skill_id}/content` | GET | 获取技能内容（Markdown） |
| `/skills/{skill_id}` | PUT | 更新技能 |
| `/skills/{skill_id}` | DELETE | 删除技能 |
| `/skills/{skill_id}/execute` | POST | 执行技能 |
| `/skills/{skill_id}/usage` | GET | 获取技能使用信息 |
| `/skills/type/{skill_type}` | GET | 按类型获取技能 |
| `/skills/active/list` | GET | 获取活跃技能列表 |

---

## 💡 优势

### 对于 Tool
- 精确、可控
- 性能好
- 适合单一、固定的操作

### 对于 Skill
- **完全由后台管理**，无需修改代码
- 管理员可以直接编辑技能内容
- 快速迭代：修改文档即可生效
- 业务人员也能参与编辑
