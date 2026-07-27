# AIPanelAdmin 白皮书

> AI驱动的企业级智能制造管理平台  
> 版本：v1.0.0  
> 日期：2026年7月

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构设计](#2-架构设计)
3. [技术栈与依赖](#3-技术栈与依赖)
4. [核心模块说明](#4-核心模块说明)
5. [数据库模型与ER关系](#5-数据库模型与er关系)
6. [API接口体系](#6-api接口体系)
7. [齐套技术专题](#7-齐套技术专题)
8. [智能体与AI能力](#8-智能体与ai能力)
9. [测试体系与质量保障](#9-测试体系与质量保障)
10. [部署架构与运维监控](#10-部署架构与运维监控)

---

## 1. 项目概述

### 1.1 项目定位

AIPanelAdmin 是一款基于 **FastAPI** 构建的企业级智能制造管理平台，整合了 **MES（制造执行系统）**、**MRPII（制造资源计划）**、**AI智能体** 和 **全栈业务管理** 四大核心能力，为企业提供从销售预测到生产交付的全链路数字化解决方案。

### 1.2 核心价值

| 价值维度 | 描述 |
|---------|------|
| **一体化管理** | 覆盖产品、计划、生产、采购、库存、销售、质量、财务全流程 |
| **AI赋能** | 内置智能体系统，支持RAG检索、技能编排、工作流自动化 |
| **模块化架构** | 插件式设计，各业务模块独立部署、灵活组合 |
| **实时监控** | 生产看板、追溯系统、异常管理实时可视化 |
| **齐套技术** | 创新的BOM级物料齐套检查，确保生产物料保障 |

### 1.3 应用场景

- **离散制造企业**：机械、电子、美妆、服装等行业
- **多工厂协同**：支持多工厂、多车间、多产线协同管理
- **小批量多品种**：支持按单生产、柔性制造场景
- **AI+制造**：利用AI智能体优化生产计划、质量检测、客户服务

---

## 2. 架构设计

### 2.1 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     前端应用层 (Vue.js)                       │
├─────────────────────────────────────────────────────────────┤
│                    API网关 / 路由分发                         │
├─────────────────────────────────────────────────────────────┤
│  用户认证 │ 权限管理 │ 中间件 │ 审计日志 │ 事件总线            │
├─────────────────────────────────────────────────────────────┤
│                    核心业务服务层                              │
├─────────────────────────────────────────────────────────────┤
│  MES │ MRPII │ Product │ Purchase │ Inventory │ Sales │ ...  │
├─────────────────────────────────────────────────────────────┤
│                 AI智能体服务层                                │
├─────────────────────────────────────────────────────────────┤
│  Agent │ RAG │ Skill │ Tool │ Workflow │ LLM │ Memory       │
├─────────────────────────────────────────────────────────────┤
│                    数据存储层                                 │
├─────────────────────────────────────────────────────────────┤
│  OpenGauss │ Redis │ Qdrant │ RabbitMQ │ 文件存储            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块依赖关系

```
                    ┌─────────┐
                    │  Product │
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌─────────┐ ┌─────────┐ ┌──────────┐
         │  MRPII  │ │ Purchase │ │ Inventory│
         └────┬────┘ └────┬────┘ └────┬─────┘
              │           │           │
              ▼           ▼           │
         ┌────────────────────┐       │
         │        MES         │◄──────┘
         └───────┬────────────┘
                 │
    ┌────────────┼────────────┬──────────┐
    ▼            ▼            ▼          ▼
┌──────┐   ┌───────┐   ┌──────┐   ┌───────┐
│Sales │   │Quality│   │Finance│  │Equipment│
└──────┘   └───────┘   └──────┘   └───────┘
```

### 2.3 分层架构

| 层级 | 目录 | 职责 |
|------|------|------|
| **API层** | `base/plugins/*/api/v1/` | RESTful接口定义、请求处理 |
| **Schema层** | `base/plugins/*/schemas/` | Pydantic数据验证模型 |
| **Service层** | `base/plugins/*/services/` | 业务逻辑封装、核心算法实现 |
| **Model层** | `base/plugins/*/models/` | Tortoise ORM数据模型定义 |
| **Middleware层** | `base/common/` | 认证、审计、权限、追踪中间件 |

---

## 3. 技术栈与依赖

### 3.1 后端技术栈

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **语言** | Python | 3.10+ | 主开发语言 |
| **框架** | FastAPI | 0.100+ | 异步Web框架 |
| **ORM** | Tortoise ORM | 0.20+ | 异步ORM框架 |
| **数据库** | OpenGauss | 6.x | PostgreSQL兼容分布式数据库 |
| **缓存** | Redis | 7.x | 内存缓存、会话存储 |
| **消息队列** | RabbitMQ | 3.12+ | 异步消息、事件驱动 |
| **向量数据库** | Qdrant | 1.7+ | AI向量检索 |
| **AI框架** | LangChain/LlamaIndex | - | 智能体与RAG |
| **模型支持** | LLM多平台 | - | 阿里/百度/腾讯/DeepSeek/本地 |

### 3.2 前端技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| **框架** | Vue.js 3.x | 渐进式前端框架 |
| **构建工具** | Vite | 前端构建 |
| **UI组件库** | Element Plus | 企业级UI组件 |
| **图标** | Lucide | 图标库 |

### 3.3 基础设施

| 类别 | 技术 | 说明 |
|------|------|------|
| **容器化** | Docker | 应用容器化 |
| **CI/CD** | 支持流水线 | 持续集成/部署 |
| **监控** | Prometheus | 指标监控 |
| **日志** | ELK/EFK | 日志收集分析 |
| **链路追踪** | Jaeger | 分布式追踪 |

### 3.4 核心依赖包

```
fastapi>=0.100.0          # Web框架
tortoise-orm>=0.20.0      # ORM
asyncpg>=0.27.0           # PostgreSQL驱动
pydantic>=2.0.0           # 数据验证
python-jose>=3.3.0        # JWT认证
passlib[bcrypt]>=1.7.4    # 密码加密
loguru>=0.7.0             # 日志
aiofiles>=23.0.0          # 异步文件操作
httpx>=0.24.0             # HTTP客户端
langchain>=0.1.0          # AI框架
qdrant-client>=1.6.0      # 向量数据库
```

---

## 4. 核心模块说明

### 4.1 模块总览

AIPanelAdmin 包含以下核心业务模块：

| 模块 | 标识 | 路由前缀 | 描述 |
|------|------|---------|------|
| **产品管理** | product | `/v1/product` | 产品分类、属性、变体、规格管理 |
| **MRPII计划** | mrp2 | `/v1/mrp2` | 预测、MPS、MRP、CRP、计划监控 |
| **制造执行** | mes | `/v1/mes` | 基础数据、生产计划/执行/报工、物料流转、追溯 |
| **库存管理** | inventory | `/v1/inventory` | 仓库、库位、批次、包装、分拣、库存量化 |
| **采购管理** | purchase | `/v1/purchase` | 供应商、采购订单、采购入库 |
| **销售管理** | sales | `/v1/sales` | 销售订单、销售统计 |
| **质量管理** | quality | `/v1/quality` | 检验标准、质量检验 |
| **财务管理** | finance | `/v1/finance` | 总账、应收应付、固定资产、成本核算 |
| **客户管理** | customer | `/v1/customer` | 客户信息、会员、消费积分 |
| **CRM** | crm | `/v1/crm` | 线索、商机、联系人、跟进活动 |
| **设备管理** | equipment | `/v1/equipment` | 设备台账、故障、维护保养 |
| **审批流** | approval | `/v1/approval` | 审批流程、实例、任务管理 |
| **审计** | audit | `/v1/audit` | 登录日志、数据变更、风险审计 |
| **智能体** | agent | `/v1/agent` | AI智能体、技能、工具、RAG、工作流 |
| **LLM服务** | llm | `/v1/llm` | 多模型接入、API密钥、用量统计 |
| **邮件通知** | mail | `/v1/mail` | 邮件收发、通知模板、关注者 |
| **委外加工** | subcontracting | `/v1/subcontracting` | 委外订单、发出、收货、结算 |

### 4.2 产品管理模块

**路径**: `base/plugins/product/`

| 子功能 | 说明 |
|--------|------|
| 产品分类管理 | 树形分类结构，支持多级分类 |
| 属性与属性值 | 支持不同产品分类的属性隔离 |
| 产品变体 | 基于属性组合生成产品SKU |
| 产品规格 | 产品规格参数管理 |

**数据模型**:
- `Product` - 产品主表
- `ProductCategory` - 产品分类
- `Attribute` / `AttributeValue` - 属性与属性值
- `ProductVariant` - 产品变体/SKU

### 4.3 MRPII计划模块

**路径**: `base/plugins/mrp2/`

| 子功能 | 说明 |
|--------|------|
| 销售预测 | 基于历史数据的销量预测 |
| 主生产计划(MPS) | 将预测转化为生产计划 |
| 物料需求计划(MRP) | BOM展开、净需求计算 |
| 能力需求计划(CRP) | 产能负荷分析 |
| 计划监控 | 在途订单、执行进度监控 |

**核心算法**：
```
净需求 = 毛需求 - 当前库存 - 在途采购 + 安全库存
毛需求 = 父项需求数量 × BOM用量 × (1 + 损耗率)
```

### 4.4 制造执行模块 (MES)

**路径**: `base/plugins/mes/`

| 子功能 | 说明 |
|--------|------|
| 基础数据 | BOM、工艺路线、工序、版本管理 |
| 生产计划 | 制造订单、工单下达与执行 |
| 生产报工 | 产量报工、工时记录 |
| 物料流转 | 领料、退料、生产入库 |
| 生产追溯 | 条码追溯、质量追溯 |
| 异常管理 | 生产异常记录与处理 |
| 齐套检查 | BOM级物料齐套检查（创新功能） |

**关键服务**:
- `production_service.py` - 生产订单管理
- `material_flow_service.py` - 物料流转
- `kit_check_service.py` - 齐套检查（见第7章）
- `base_data_service.py` - BOM与工艺管理

### 4.5 库存管理模块

**路径**: `base/plugins/inventory/`

| 子功能 | 说明 |
|--------|------|
| 仓库管理 | 多仓库支持 |
| 库位管理 | 仓库库位划分 |
| 批次管理 | 批次号追踪 |
| 包装管理 | 包装规格管理 |
| 库存量化 | 实时库存数量与预留 |
| 分拣管理 | 出库分拣 |

**核心数据模型**: `StockQuant` - 记录每个物料的实时库存数量、预留数量和可用数量。

### 4.6 采购与销售模块

**采购** (`base/plugins/purchase/`):
- 供应商管理（资质、分类、评级）
- 采购订单（创建、下达、入库、结算）
- 采购收货与质检

**销售** (`base/plugins/sales/`):
- 销售订单（报价、下单、发货、结算）
- 销售统计（销售额、订单量、客户分析）

### 4.7 质量管理模块

**路径**: `base/plugins/quality/`

| 子功能 | 说明 |
|--------|------|
| 检验标准 | 物料/产品检验标准与指标 |
| 质量检验 | 来料检、过程检、成品检 |
| 不合格品处理 | 退货、返工、报废处理 |

### 4.8 财务管理模块

**路径**: `base/plugins/finance/`

| 子功能 | 说明 |
|--------|------|
| 总账管理 | 科目、凭证、账簿 |
| 应收应付 | 客户/供应商往来账款 |
| 固定资产 | 资产登记、折旧、处置 |
| 成本核算 | 存货成本、成本差异分析 |
| 财务报表 | 资产负债表、利润表、现金流量表 |

### 4.9 AI智能体模块

**路径**: `base/plugins/agent/`

| 子功能 | 说明 |
|--------|------|
| 智能体(Agent) | 对话式AI助手 |
| 技能(Skill) | 预定义能力模块 |
| 工具(Tool) | 外部API/函数调用 |
| RAG检索 | 基于知识库的问答 |
| 工作流 | 多步骤任务编排 |
| 记忆管理 | 对话上下文记忆 |
| 任务分解 | 复杂任务自动分解 |

### 4.10 其他模块

| 模块 | 路径 | 核心功能 |
|------|------|---------|
| CRM | `base/plugins/crm/` | 线索、商机、联系人管理 |
| 客户管理 | `base/plugins/customer/` | 客户档案、会员、积分 |
| 设备管理 | `base/plugins/equipment/` | 设备台账、故障、保养 |
| 审批流 | `base/plugins/approval/` | 工作流审批引擎 |
| 审计 | `base/plugins/audit/` | 操作审计、风险识别 |
| 邮件通知 | `base/plugins/mail/` | 邮件发送、通知推送 |
| 委外加工 | `base/plugins/subcontracting/` | 委外订单全流程 |
| LLM服务 | `base/plugins/llm/` | 多模型接入与计费 |

---

## 5. 数据库模型与ER关系

### 5.1 核心数据模型

#### 5.1.1 产品域

```
ProductCategory (产品分类)
    ├── id, parent_id, name, code, sort
    └── Product (产品)
         ├── id, category_id, code, name, spec, unit
         ├── ProductVariant (产品变体)
         │    ├── id, product_id, sku_code, price
         │    └── VariantValue (变体属性值)
         └── ProductSpecification (产品规格)
              ├── id, product_id, spec_key, spec_value

Attribute (属性)
    └── AttributeValue (属性值)
         ├── id, attribute_id, value, product_category_id
```

#### 5.1.2 制造域

```
BomVersion (BOM版本)
    └── Bom (BOM明细)
         ├── id, product_code, item_code, quantity
         ├── level, parent_item_code, scrap_rate
         └── is_active

ManufacturingOrder (制造订单)
    ├── id, mo_code, product_code, quantity
    ├── status, planned_start, planned_end
    └── WorkOrder (工单)
         ├── id, mo_id, route_id, status
         └── ProductionReport (生产报工)

MaterialRequisition (领料单)
    ├── id, mo_id, requisition_no, status
    └── MaterialRequisitionDetail (领料明细)
         └── material_code, required_quantity
```

#### 5.1.3 库存域

```
Warehouse (仓库)
    └── Location (库位)
         └── Lot (批次)

StockQuant (库存量化)
    ├── id, product_code, warehouse_id
    ├── quantity, reserved_quantity, available_quantity
    └── package_type

Picking (分拣单)
    └── PickingType (分拣类型)
```

#### 5.1.4 采购域

```
Supplier (供应商)
    ├── id, code, name, contact
    └── PurchaseOrder (采购订单)
         ├── id, po_no, supplier_id, status
         └── PurchaseOrderDetail (采购明细)
              └── item_code, quantity, price
```

#### 5.1.5 销售域

```
SalesOrder (销售订单)
    ├── id, so_no, customer_id, status
    └── SalesOrderDetail (销售明细)
         └── item_code, quantity, price
```

### 5.2 ER关系图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Product    │────<│    Bom      │<────│  ProductCat  │
└──────┬──────┘     └──────┬──────┘     └─────────────┘
       │                   │
       │                   ▼
       │            ┌─────────────┐     ┌─────────────┐
       │            │  Bom (子项)  │────<│  StockQuant  │
       │            └─────────────┘     └─────────────┘
       │                                         │
       ▼                                         │
┌─────────────┐     ┌─────────────┐              │
│Manufacturing │────<│MaterialReq  │              │
│   Order      │     └─────────────┘              │
└──────┬──────┘                                   │
       │                                          │
       ▼                                          ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ PurchaseOrder│────<│PurchaseOrder│     │ SalesOrder   │
└─────────────┘     │  Detail     │     └─────────────┘
                    └─────────────┘
```

### 5.3 数据模型规范

| 规范 | 说明 |
|------|------|
| **主键** | 统一使用自增 `id` 作为主键 |
| **时间戳** | 所有模型包含 `created_at`、`updated_at` |
| **软删除** | 使用 `is_deleted` 字段 |
| **状态字段** | 使用 `CharField` + 枚举值 |
| **精度** | 数量字段使用 `DecimalField`（15位6小数） |
| **索引** | 查询频繁字段建立 `index=True` |

---

## 6. API接口体系

### 6.1 RESTful API规范

| 规范 | 说明 |
|------|------|
| **基础路径** | `/api/v1/{module}` |
| **认证** | JWT Bearer Token |
| **响应格式** | `{code: 0, msg: "success", data: {...}}` |
| **错误码** | 0=成功, 非0=失败 |
| **分页** | `{items: [], total: N, page: N, page_size: N}` |

### 6.2 API接口清单

#### 产品管理 `/api/v1/product`

| 接口 | 方法 | 描述 |
|------|------|------|
| `/product/categories` | GET/POST | 产品分类列表/创建 |
| `/product/categories/{id}` | PUT/DELETE | 分类更新/删除 |
| `/product` | GET/POST | 产品列表/创建 |
| `/product/{id}` | GET/PUT/DELETE | 产品详情/更新/删除 |
| `/product/attributes` | GET/POST | 属性列表/创建 |
| `/product/attributes/{id}/values` | GET/POST | 属性值管理 |
| `/product/variants` | GET/POST | 产品变体 |
| `/product/specifications` | GET/POST | 产品规格 |

#### MRPII计划 `/api/v1/mrp2`

| 接口 | 方法 | 描述 |
|------|------|------|
| `/mrp2/forecast` | GET/POST | 销售预测 |
| `/mrp2/mps` | GET/POST | 主生产计划 |
| `/mrp2/mrp` | GET | 物料需求计划 |
| `/mrp2/crp` | GET | 能力需求计划 |
| `/mrp2/monitor` | GET | 计划执行监控 |
| `/mrp2/planned-orders` | GET/POST | 计划订单 |

#### 制造执行 `/api/v1/mes`

| 接口 | 方法 | 描述 |
|------|------|------|
| `/mes/bom` | GET/POST | BOM管理 |
| `/mes/routes` | GET/POST | 工艺路线 |
| `/mes/manufacturing-orders` | GET/POST | 制造订单 |
| `/mes/manufacturing-orders/{id}/release` | POST | 下达订单（含齐套检查） |
| `/mes/work-orders` | GET/POST | 工单管理 |
| `/mes/production-report` | GET/POST | 生产报工 |
| `/mes/requisitions` | GET/POST | 领料单 |
| `/mes/requisitions/{id}/confirm` | POST | 确认领料（含库存验证） |
| `/mes/kit-check/{mo_id}` | GET | 齐套检查 |
| `/mes/kit-check/bom/{product_code}` | GET | BOM齐套检查 |
| `/mes/kit-check/{mo_id}/shortage` | GET | 缺料清单 |
| `/mes/kit-check/batch` | POST | 批量齐套检查 |

#### 库存管理 `/api/v1/inventory`

| 接口 | 方法 | 描述 |
|------|------|------|
| `/inventory/warehouses` | GET/POST | 仓库管理 |
| `/inventory/locations` | GET/POST | 库位管理 |
| `/inventory/lots` | GET/POST | 批次管理 |
| `/inventory/packages` | GET/POST | 包装管理 |
| `/inventory/quants` | GET | 库存查询 |
| `/inventory/pickings` | GET/POST | 分拣管理 |

#### 采购管理 `/api/v1/purchase`

| 接口 | 方法 | 描述 |
|------|------|------|
| `/purchase/suppliers` | GET/POST | 供应商管理 |
| `/purchase/suppliers/{id}` | PUT/DELETE | 供应商更新/删除 |
| `/purchase/orders` | GET/POST | 采购订单 |
| `/purchase/orders/{id}` | GET/PUT | 采购订单详情/更新 |
| `/purchase/orders/{id}/receive` | POST | 采购入库 |

#### 销售管理 `/api/v1/sales`

| 接口 | 方法 | 描述 |
|------|------|------|
| `/sales/orders` | GET/POST | 销售订单 |
| `/sales/orders/{id}` | GET/PUT | 订单详情/更新 |
| `/sales/orders/{id}/ship` | POST | 订单发货 |
| `/sales/stats` | GET | 销售统计 |

#### 质量管理 `/api/v1/quality`

| 接口 | 方法 | 描述 |
|------|------|------|
| `/quality/standards` | GET/POST | 检验标准 |
| `/quality/inspections` | GET/POST | 质量检验 |

#### 财务管理 `/api/v1/finance`

| 接口 | 方法 | 描述 |
|------|------|------|
| `/finance/accounts` | GET/POST | 会计科目 |
| `/finance/journals` | GET/POST | 凭证管理 |
| `/finance/receivables` | GET | 应收账款 |
| `/finance/payables` | GET | 应付账款 |
| `/finance/assets` | GET/POST | 固定资产 |
| `/finance/reports` | GET | 财务报表 |

### 6.3 请求/响应示例

**齐套检查请求**:
```
GET /api/v1/mes/kit-check/1
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "code": 0,
  "msg": "齐套检查成功",
  "data": {
    "mo_id": 1,
    "mo_code": "MO-20260718-001",
    "product_code": "LIPSTICK-001",
    "product_name": "口红-烈焰红",
    "required_quantity": 50,
    "total_items": 6,
    "shortage_items": 3,
    "kit_rate": 50.0,
    "kit_status": "partial_kit",
    "items": [...],
    "shortage_list": [
      {"item_code": "RAW-002", "shortage": 165.0}
    ]
  }
}
```

---

## 7. 齐套技术专题

### 7.1 技术背景

在离散制造企业中，**齐套（Kit Check）** 是指在下达生产订单前，检查所有物料是否齐备的关键技术。传统的ERP/MES系统往往只在领料环节才发现缺料，导致生产延误、订单交期紧张。

AIPanelAdmin 创新地将**齐套检查**前置到**制造订单下达**环节，通过BOM递归展开、实时库存比对、在途采购计算，在订单规划阶段就能准确识别缺料风险。

### 7.2 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                     KitCheckService                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  check_kit_by_mo(mo_id)        check_kit_by_bom(product, qty)│
│         │                              │                      │
│         ▼                              ▼                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              _get_flattened_bom()                       │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │ │
│  │  │ BOM Level1│→│ BOM Level2│→│ BOM Level3│ → 原材料     │ │
│  │  └──────────┘  └──────────┘  └──────────┘             │ │
│  │         │              │              │                 │ │
│  │         ▼              ▼              ▼                 │ │
│  │  ┌─────────────────────────────────────────────────┐   │ │
│  │  │          _get_available_stock()                  │   │ │
│  │  │  总库存 - 预留库存 = 可用库存                    │   │ │
│  │  └─────────────────────────────────────────────────┘   │ │
│  │         │              │              │                 │ │
│  │         ▼              ▼              ▼                 │ │
│  │  ┌─────────────────────────────────────────────────┐   │ │
│  │  │          _get_on_order_quantity()                │   │ │
│  │  │  在途采购 = 采购数量 - 已收货数量                 │   │ │
│  │  └─────────────────────────────────────────────────┘   │ │
│  │         │              │              │                 │ │
│  │         ▼              ▼              ▼                 │ │
│  │  ┌─────────────────────────────────────────────────┐   │ │
│  │  │         齐套计算引擎                              │   │ │
│  │  │  净可用 = 可用库存 + 在途采购                      │   │ │
│  │  │  缺料 = max(0, 需求数量 - 净可用)                │   │ │
│  │  │  齐套率 = (总数 - 缺料数) / 总数 × 100%         │   │ │
│  │  └─────────────────────────────────────────────────┘   │ │
│  │                                                         │ │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 BOM递归展开流程

```
输入: 产品编码=LIPSTICK-001, 数量=50

Step 1: 查询LIPSTICK-001的BOM
  ├── LIP-001 口红管 (用量1, 损耗2%) → 需求=50×1×1.02=51
  ├── LIP-002 口红膏体 (用量3g, 损耗5%) → 需求=50×3×1.05=157.5
  │   └── 递归查询LIP-002的BOM
  │       ├── RAW-001 色粉 (用量0.5g, 损耗10%) → 需求=157.5×0.5×1.1=86.625
  │       ├── RAW-002 油脂 (用量2g) → 需求=157.5×2=315
  │       └── RAW-003 蜡质 (用量0.5g) → 需求=157.5×0.5=78.75
  ├── LIP-003 口红盖 (用量1) → 需求=50
  └── LIP-004 包装盒 (用量1) → 需求=50

Step 2: 合并原材料（去重累加）
  ├── LIP-001 口红管: 51个
  ├── RAW-001 色粉: 86.625g
  ├── RAW-002 油脂: 315g
  ├── RAW-003 蜡质: 78.75g
  ├── LIP-003 口红盖: 50个
  └── LIP-004 包装盒: 50个

Step 3: 逐项比对库存
  每项: 可用库存 + 在途采购 vs 需求数量 → 缺料清单
```

### 7.4 齐套检查时序图

```
用户        前端        API层       KitCheckService    数据库     库存系统
 │          │           │              │               │          │
 │──请求──→│           │              │               │          │
 │          │──GET kit-check/{id}──→│               │          │
 │          │           │──check_kit_by_mo()────────→│          │
 │          │           │              │──查MO──────→│          │
 │          │           │              │←─MO数据─────│          │
 │          │           │              │──check_kit_by_bom()→│   │
 │          │           │              │               │          │
 │          │           │              │──BOM递归展开→│          │
 │          │           │              │←──物料清单───│          │
 │          │           │              │               │          │
 │          │           │              │──逐项查库存────────────────→│
 │          │           │              │←──库存数据──────────────────│
 │          │           │              │               │          │
 │          │           │              │──查在途采购─→│          │
 │          │           │              │←──PO数据───│          │
 │          │           │              │               │          │
 │          │           │              │──计算齐套结果  │          │
 │          │           │              │               │          │
 │          │           │←──返回齐套结果│              │          │
 │          │←──JSON响应──│             │               │          │
 │←────────展示结果──────│             │               │          │
```

### 7.5 核心代码实现

#### KitCheckService 核心方法

```python
# base/plugins/mes/services/kit_check_service.py

class KitCheckService:
    """齐套检查服务"""

    @staticmethod
    async def check_kit_by_mo(mo_id: int) -> Dict[str, Any]:
        """检查制造订单齐套情况"""
        mo = await ManufacturingOrder.filter(id=mo_id).first()
        result = await KitCheckService.check_kit_by_bom(
            mo.product_code, mo.quantity
        )
        result["mo_id"] = mo_id
        result["mo_code"] = mo.mo_code
        return result

    @staticmethod
    async def check_kit_by_bom(product_code: str, quantity: int) -> Dict[str, Any]:
        """检查BOM齐套情况"""
        bom_items = await KitCheckService._get_flattened_bom(
            product_code, Decimal(str(quantity))
        )
        # 逐项比对库存与需求
        for item in bom_items:
            _, _, available = await KitCheckService._get_available_stock(
                item["item_code"]
            )
            on_order = await KitCheckService._get_on_order_quantity(
                item["item_code"]
            )
            net_available = available + on_order
            shortage = max(0, item["required_quantity"] - net_available)
            # ... 汇总缺料清单
        return result
```

#### 制造订单下达集成

```python
# base/plugins/mes/services/production_service.py

@staticmethod
async def release_mo(mo_id: int, skip_kit_check: bool = False):
    # ... BOM存在性检查 ...
    
    # 齐套检查
    if KIT_CHECK_AVAILABLE and not skip_kit_check:
        kit_result = await KitCheckService.check_kit_by_mo(mo_id)
        if kit_result.get("kit_status") != "full_kit":
            shortage_info = "; ".join([
                f"{item['item_name']}缺{item['shortage']}{item['unit']}"
                for item in kit_result["shortage_list"]
            ])
            raise ValueError(f"物料不齐套，无法下达。缺料: {shortage_info}")
    
    mo.status = "released"
    await mo.save()
```

### 7.6 齐套状态说明

| 状态 | 标识 | 说明 | 业务动作 |
|------|------|------|---------|
| **完全齐套** | `full_kit` | 所有物料库存充足 | 允许下达生产订单 |
| **部分齐套** | `partial_kit` | 部分物料短缺 | 需补充缺料后再下达 |
| **不齐套** | `no_kit` | 全部物料或BOM异常 | 需立即处理 |

### 7.7 单元测试覆盖

| 测试用例 | 场景 | 结果 |
|---------|------|------|
| 口红50支齐套检查 | 多级BOM展开+库存比对 | ✅ 通过 |
| 制造订单齐套检查 | MO关联产品齐套检查 | ✅ 通过 |
| 缺料清单获取 | 精准识别缺料项和数量 | ✅ 通过 |
| 齐套状态查询 | 返回full_kit/partial_kit/no_kit | ✅ 通过 |
| 精华液完全齐套 | 库存充足场景 | ✅ 通过 |
| 粉底液部分齐套 | 部分缺料场景 | ✅ 通过 |
| 不存在产品不齐套 | BOM未维护场景 | ✅ 通过 |
| 批量齐套检查 | 多订单批量检查 | ✅ 通过 |
| 多级BOM递归展开 | 原材料正确展开 | ✅ 通过 |

**测试统计**: **9/9 通过**

### 7.8 技术亮点

| 亮点 | 说明 |
|------|------|
| **多级BOM递归** | 支持无限层级BOM递归展开，自动识别原材料 |
| **损耗率计算** | 需求数量自动乘以(1+损耗率)，精准计算 |
| **在途采购** | 将在途采购数量计入净可用，避免重复采购 |
| **分类属性隔离** | 不同产品分类的属性值通过product_category_id隔离 |
| **前置检查** | 在订单下达环节即进行齐套检查，避免生产延误 |
| **灵活跳过** | 支持skip_kit_check参数，允许特殊场景跳过检查 |

---

## 8. 智能体与AI能力

### 8.1 AI智能体架构

```
┌─────────────────────────────────────────────────────┐
│                   Agent 管理器                        │
│  ┌─────────────────────────────────────────────────┐│
│  │              对话流程引擎 (DialogFlow)             ││
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ││
│  │  │ 意图识别  │→│ 技能选择  │→│ 执行规划  │  ││
│  │  └───────────┘  └───────────┘  └───────────┘  ││
│  └─────────────────────────────────────────────────┘│
│                                                     │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐      │
│  │  技能库   │  │  工具库   │  │ 知识库    │      │
│  └───────────┘  └───────────┘  └───────────┘      │
│                                                     │
│  ┌─────────────────────────────────────────────────┐│
│  │              LLM 多模型接入                      ││
│  │  阿里 │ 百度 │ 腾讯 │ DeepSeek │ 本地模型        ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### 8.2 核心AI能力

| 能力 | 说明 | 技术实现 |
|------|------|---------|
| **对话管理** | 多轮对话上下文管理 | Session+Memory |
| **意图识别** | 自然语言意图理解 | LLM + 分类器 |
| **技能编排** | 根据意图自动选择技能 | 技能注册中心 |
| **工具调用** | 外部API/函数调用 | Tool Registry |
| **RAG检索** | 知识库增强生成 | Qdrant向量检索 |
| **工作流** | 多步骤任务自动编排 | LangGraph |
| **任务分解** | 复杂任务自动分解 | LLM规划 |
| **代码执行** | 安全沙箱代码执行 | safe_eval |

### 8.3 支持的LLM平台

| 平台 | 接口 | 说明 |
|------|------|------|
| 阿里通义 | `alibaba_service.py` | 中文优化 |
| 百度千帆 | `baidu_service.py` | 多模型支持 |
| 腾讯混元 | `tencent_service.py` | 企业级 |
| DeepSeek | `deepseek_service.py` | 代码能力强 |
| 本地模型 | `localai_service.py` | 私有化部署 |
| 通用接口 | `openai_service.py` | OpenAI兼容 |

### 8.4 应用场景

- **智能客服**: 7×24小时客户咨询应答
- **生产优化**: AI辅助生产计划排程
- **质量检测**: 智能质量分析与预警
- **数据洞察**: 自然语言数据查询
- **文档处理**: 文档自动摘要与提取
- **流程自动化**: 重复性工作自动化

---

## 9. 测试体系与质量保障

### 9.1 测试架构

```
┌─────────────────────────────────────────────┐
│                 测试金字塔                    │
│                                              │
│                    ╱  E2E测试  ╲             │
│                   ╱  API集成测试 ╲            │
│                  ╱  服务层单元测试  ╱          │
│                 ╱   数据模型测试    ╱          │
│                ╱     基础组件测试    ╱         │
│               ╱────────────────────╱          │
└─────────────────────────────────────────────┘
```

### 9.2 测试工具

| 工具 | 用途 |
|------|------|
| **pytest** | 单元测试框架 |
| **httpx/requests** | API接口测试 |
| **Tortoise Test** | ORM层测试 |
| **覆盖率工具** | 代码覆盖率统计 |

### 9.3 测试用例

#### 美妆产品全流程测试

| 测试计划 | 文件 | 覆盖范围 |
|---------|------|---------|
| 美妆产品测试 | `docs/Cosmetics-Test-Cases.md` | 产品→MRP→采购→库存→销售→质量 |
| 美妆API测试 | `tests/test_cosmetics_api.py` | 全流程API自动化 |
| 齐套单元测试 | `tests/test_kit_check_unit.py` | 齐套检查核心逻辑 |

#### 蓝牙耳机测试

| 测试计划 | 文件 | 覆盖范围 |
|---------|------|---------|
| 蓝牙耳机测试 | `docs/Bluetooth-Headset-Test-Cases.md` | 产品→MRP→采购→库存→销售 |
| API测试 | `tests/test_bluetooth_api.py` | 蓝牙耳机全流程 |

#### MES手动测试

| 文件 | 说明 |
|------|------|
| `docs/MES-Manual-Test-Cases.md` | MES模块手动测试用例 |

### 9.4 质量保障

| 措施 | 说明 |
|------|------|
| **代码审查** | PR合并前必须审查 |
| **静态分析** | 代码风格、类型检查 |
| **单元测试** | 核心服务必须有单元测试 |
| **集成测试** | 关键业务流程端到端测试 |
| **性能测试** | 接口响应时间、并发量测试 |
| **安全测试** | 权限、注入、XSS等安全扫描 |

---

## 10. 部署架构与运维监控

### 10.1 部署架构

```
┌───────────────────────────────────────────────────────┐
│                      负载均衡 (Nginx)                  │
├───────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐                     │
│  │  应用实例 1  │  │  应用实例 2  │                     │
│  │  (FastAPI)   │  │  (FastAPI)   │                     │
│  └─────────────┘  └─────────────┘                     │
├───────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │OpenGauss │  │  Redis   │  │RabbitMQ  │             │
│  └──────────┘  └──────────┘  └──────────┘             │
├───────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Qdrant   │  │ 文件存储 │  │ 日志存储 │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└───────────────────────────────────────────────────────┘
```

### 10.2 快速启动

```bash
# 1. 克隆项目
git clone <repo-url> aipaneladmin
cd aipaneladmin

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置数据库
# 编辑 config.conf 修改数据库连接信息

# 4. 启动OpenGauss
cd deploy/openguass
docker-compose up -d

# 5. 启动服务
python run.py

# 6. 访问系统
# API文档: http://localhost:9998/docs
# 管理后台: http://localhost:9998
```

### 10.3 配置说明

核心配置文件 `config.conf`:

```ini
[app]
name = AIPanelAdmin
version = v0.1.0
debug = true

[db]
db_host = 127.0.0.1
db_name = aipaneladmin
db_user = admin
db_password = Admin@123
db_port = 15432

[redis]
enabled = false
host = 127.0.0.1
port = 6379

[rabbitmq]
enabled = true
host = 127.0.0.1
port = 5672

[qdrant]
enabled = true
host = http://localhost:6333

[audit]
enabled = true
retention_days = 90
```

### 10.4 监控与告警

| 监控项 | 工具 | 说明 |
|--------|------|------|
| **应用指标** | Prometheus | API调用量、响应时间、错误率 |
| **系统指标** | Prometheus | CPU、内存、磁盘、网络 |
| **日志收集** | ELK/EFK | 全链路日志收集分析 |
| **链路追踪** | Jaeger | 分布式调用追踪 |
| **告警规则** | AlertManager | 异常事件告警通知 |

### 10.5 目录结构

```
aipaneladmin/
├── base/
│   ├── common/          # 公共组件（中间件、响应、路由）
│   ├── core/            # 核心模块（用户、权限）
│   ├── plugins/         # 业务插件
│   │   ├── agent/       # AI智能体
│   │   ├── mes/         # 制造执行
│   │   ├── mrp2/        # MRPII计划
│   │   ├── product/     # 产品管理
│   │   ├── inventory/   # 库存管理
│   │   ├── purchase/    # 采购管理
│   │   ├── sales/       # 销售管理
│   │   ├── quality/     # 质量管理
│   │   ├── finance/     # 财务管理
│   │   ├── equipment/   # 设备管理
│   │   ├── crm/         # CRM
│   │   ├── customer/    # 客户管理
│   │   ├── approval/    # 审批流
│   │   ├── audit/       # 审计
│   │   ├── llm/         # LLM服务
│   │   ├── mail/        # 邮件通知
│   │   └── subcontracting/ # 委外加工
│   └── app_wrapper.py   # 应用封装
├── web/                 # 前端应用
├── tests/               # 测试脚本
├── docs/                # 文档
├── config.conf          # 配置文件
├── run.py               # 启动脚本
└── requirements.txt     # 依赖清单
```

---

## 附录

### A. 模块清单

| # | 模块 | 路径 | 功能描述 |
|---|------|------|---------|
| 1 | Agent | `base/plugins/agent/` | AI智能体、技能、工具、RAG |
| 2 | 审批流 | `base/plugins/approval/` | 工作流审批引擎 |
| 3 | 审计 | `base/plugins/audit/` | 操作审计与风险识别 |
| 4 | CRM | `base/plugins/crm/` | 线索、商机、联系人 |
| 5 | 客户 | `base/plugins/customer/` | 客户档案、会员、积分 |
| 6 | 设备 | `base/plugins/equipment/` | 设备台账、故障、保养 |
| 7 | 财务 | `base/plugins/finance/` | 总账、应收应付、报表 |
| 8 | 库存 | `base/plugins/inventory/` | 仓库、库位、批次、量化 |
| 9 | LLM | `base/plugins/llm/` | 多模型接入与计费 |
| 10 | 邮件 | `base/plugins/mail/` | 邮件收发与通知 |
| 11 | MES | `base/plugins/mes/` | 制造执行与齐套检查 |
| 12 | MRPII | `base/plugins/mrp2/` | MRP、MPS、CRP |
| 13 | 产品 | `base/plugins/product/` | 产品分类、属性、变体 |
| 14 | 采购 | `base/plugins/purchase/` | 供应商、采购订单 |
| 15 | 质量 | `base/plugins/quality/` | 检验标准与质量检验 |
| 16 | 销售 | `base/plugins/sales/` | 销售订单与统计 |
| 17 | 委外 | `base/plugins/subcontracting/` | 委外加工全流程 |

### B. 关键文件索引

| 文件 | 说明 |
|------|------|
| `run.py` | 应用启动入口 |
| `config.conf` | 系统配置文件 |
| `base/app_wrapper.py` | FastAPI应用封装 |
| `base/plugins/mes/services/kit_check_service.py` | 齐套检查核心服务 |
| `base/plugins/mes/services/production_service.py` | 生产订单管理（含齐套集成） |
| `base/plugins/mes/services/material_flow_service.py` | 物料流转（含库存验证） |
| `base/plugins/mes/api/v1/kit_check_router.py` | 齐套检查API路由 |
| `tests/test_kit_check_unit.py` | 齐套检查单元测试 |

### C. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-07-27 | 首个正式版本，包含MES/MRPII/AI智能体/齐套技术 |

---

> **文档维护**: 本白皮书随项目迭代持续更新。  
> **技术支持**: hepan@aipanel.admin  
> **版权所有**: AIPanelAdmin Team