# Odoo风格库存模块架构设计文档

## 目录
- [1. 核心模型设计](#1-核心模型设计)
- [2. 关键机制设计](#2-关键机制设计)
- [3. 状态流转设计](#3-状态流转设计)
- [4. API接口设计](#4-api接口设计)
- [5. 模型关系图](#5-模型关系图)
- [6. 数据库索引设计](#6-数据库索引设计)

---

## 1. 核心模型设计

### 1.1 StockLocation（库位）

库位是库存管理的基础单元，支持层级结构（树形结构）。

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Integer | 是 | 主键ID |
| name | String(100) | 是 | 库位名称 |
| complete_name | String(500) | 是 | 完整路径名称（如：仓库A/库区1/货架A/层1） |
| code | String(50) | 否 | 库位编码 |
| location_id | Integer(FK) | 否 | 父库位ID |
| active | Boolean | 是 | 是否激活（软删除） |
| usage | Enum | 是 | 用途类型：view(视图)/internal(内部)/customer(客户)/supplier(供应商)/inventory(盘点)/production(生产) |
| is_scrap_location | Boolean | 是 | 是否报废库位 |
| return_location | Boolean | 是 | 是否退货库位 |
| company_id | Integer(FK) | 是 | 所属公司ID |
| partner_id | Integer(FK) | 否 | 关联合作伙伴（客户/供应商库位） |
| comment | Text | 否 | 备注 |
| posx/posy/posz | Integer | 否 | 库位坐标（用于仓库布局） |
| parent_path | String(500) | 否 | 物化路径（如：1/5/12/，用于高效查询子树） |
| create_time | DateTime | 是 | 创建时间 |
| write_time | DateTime | 是 | 最后更新时间 |

#### 约束规则
- usage='view'的库位不能存放实际库存
- 报废库位只能有一个
- 删除库位时需检查是否存在子库位或库存

---

### 1.2 StockWarehouse（仓库）

仓库是物流管理的中心单元，关联关键库位。

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Integer | 是 | 主键ID |
| name | String(100) | 是 | 仓库名称 |
| code | String(10) | 是 | 仓库编码（唯一） |
| company_id | Integer(FK) | 是 | 所属公司ID |
| partner_id | Integer(FK) | 否 | 仓库地址（关联合作伙伴） |
| active | Boolean | 是 | 是否激活 |
| lot_stock_id | Integer(FK) | 是 | 默认库存库位（存货位置） |
| input_stock_id | Integer(FK) | 是 | 入库库位（收货暂存） |
| output_stock_id | Integer(FK) | 是 | 出库库位（发货暂存） |
| qc_stock_id | Integer(FK) | 否 | 质检库位 |
| pack_stock_id | Integer(FK) | 否 | 打包库位 |
| view_location_id | Integer(FK) | 是 | 视图库位（仓库顶层视图） |
| create_time | DateTime | 是 | 创建时间 |
| write_time | DateTime | 是 | 最后更新时间 |

#### 自动创建库位逻辑
创建仓库时，系统自动创建以下库位结构：
```
仓库A（view）
├── 库存（internal）- lot_stock_id
├── 入库（internal）- input_stock_id
├── 出库（internal）- output_stock_id
├── 质检（internal）- qc_stock_id
└── 打包（internal）- pack_stock_id
```

---

### 1.3 StockPickingType（调拨类型）

定义调拨单的类型和序列码规则。

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Integer | 是 | 主键ID |
| name | String(100) | 是 | 类型名称 |
| code | String(20) | 是 | 类型编码：incoming/outgoing/internal/dropship |
| sequence_id | Integer(FK) | 是 | 序列号规则ID |
| sequence_code | String(10) | 是 | 序列码前缀 |
| warehouse_id | Integer(FK) | 否 | 所属仓库ID |
| default_location_src_id | Integer(FK) | 否 | 默认源库位 |
| default_location_dest_id | Integer(FK) | 否 | 默认目标库位 |
| active | Boolean | 是 | 是否激活 |
| show_operations | Boolean | 是 | 是否显示明细行 |
| show_reserved | Boolean | 是 | 是否显示预留数量 |
| create_move_type | Enum | 是 | 创建移动类型：one/many（一次移动/多次移动） |
| reservation_method | Enum | 是 | 预留方式：manual/auto_at_confirm/by_product |
| reservation_days | Integer | 否 | 预留提前天数 |
| create_time | DateTime | 是 | 创建时间 |
| write_time | DateTime | 是 | 最后更新时间 |

#### 预定义调拨类型
| 类型编码 | 名称 | 源库位 | 目标库位 | 说明 |
|---------|------|--------|---------|------|
| incoming | 收货单 | 供应商库位 | 入库库位 | 采购入库 |
| outgoing | 发货单 | 出库库位 | 客户库位 | 销售出库 |
| internal | 内部调拨 | 内部库位 | 内部库位 | 库位间调拨 |
| dropship | 直发单 | 供应商库位 | 客户库位 | 不入库直接发货 |

---

### 1.4 StockPicking（调拨单）

调拨单是库存移动的载体，记录完整的出入库流程。

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Integer | 是 | 主键ID |
| name | String(50) | 是 | 调拨单号（自动生成） |
| picking_type_id | Integer(FK) | 是 | 调拨类型ID |
| location_id | Integer(FK) | 是 | 源库位ID |
| location_dest_id | Integer(FK) | 是 | 目标库位ID |
| partner_id | Integer(FK) | 否 | 合作伙伴ID（客户/供应商） |
| state | Enum | 是 | 状态：draft/confirmed/assigned/done/cancel |
| origin | String(100) | 否 | 来源单据（销售单号/采购单号） |
| note | Text | 否 | 备注 |
| move_type | Enum | 是 | 移动类型：direct/one（直接交付/一起交付） |
| priority | Enum | 否 | 优先级：0=普通/1=紧急/2=非常紧急/3=加急 |
| scheduled_date | DateTime | 否 | 计划日期 |
| date_done | DateTime | 否 | 完成日期 |
| company_id | Integer(FK) | 是 | 所属公司ID |
| owner_id | Integer(FK) | 否 | 货主ID（代管业务） |
| printed | Boolean | 是 | 是否已打印 |
| immediate_transfer | Boolean | 是 | 是否立即转移 |
| create_time | DateTime | 是 | 创建时间 |
| write_time | DateTime | 是 | 最后更新时间 |

#### 计算字段
| 字段名 | 说明 |
|--------|------|
| move_ids | 关联的移动明细 |
| move_line_ids | 关联的移动明细行 |
| move_lines_exist | 是否存在移动明细 |
| quantity_done | 已完成数量 |
| has_packages | 是否包含包裹 |

---

### 1.5 StockMove（移动明细）

移动明细关联产品和库位，是调拨单的明细行。

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Integer | 是 | 主键ID |
| name | String(200) | 是 | 移动描述（产品名称+规格） |
| picking_id | Integer(FK) | 否 | 所属调拨单ID |
| product_id | Integer(FK) | 是 | 产品ID |
| product_uom | Integer(FK) | 是 | 计量单位ID |
| product_uom_qty | Decimal(16,4) | 是 | 初始需求数量 |
| quantity_done | Decimal(16,4) | 是 | 已完成数量 |
| reserved_availability | Decimal(16,4) | 是 | 已预留数量 |
| available_not_reserved | Decimal(16,4) | 是 | 可用但未预留数量 |
| location_id | Integer(FK) | 是 | 源库位ID |
| location_dest_id | Integer(FK) | 是 | 目标库位ID |
| state | Enum | 是 | 状态：draft/confirmed/assigned/done/cancel |
| origin | String(100) | 否 | 来源单据 |
| procure_method | Enum | 是 | 采购方法：make_to_stock/make_to_order |
| company_id | Integer(FK) | 是 | 所属公司ID |
| rule_id | Integer(FK) | 否 | 补货规则ID |
| push_rule_id | Integer(FK) | 否 | 推式规则ID |
| create_time | DateTime | 是 | 创建时间 |
| write_time | DateTime | 是 | 最后更新时间 |

#### 计算字段
| 字段名 | 说明 |
|--------|------|
| move_line_ids | 关联的移动明细行 |
| remaining_qty | 剩余未完成数量 |

#### 约束规则
- product_uom_qty >= 0
- quantity_done <= product_uom_qty
- 同一调拨单内同一产品可有多条移动明细

---

### 1.6 StockMoveLine（移动明细行）

移动明细行是批次/序列号级别的详细记录。

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Integer | 是 | 主键ID |
| picking_id | Integer(FK) | 否 | 所属调拨单ID |
| move_id | Integer(FK) | 是 | 所属移动明细ID |
| product_id | Integer(FK) | 是 | 产品ID |
| product_uom_id | Integer(FK) | 是 | 计量单位ID |
| location_id | Integer(FK) | 是 | 源库位ID |
| location_dest_id | Integer(FK) | 是 | 目标库位ID |
| lot_id | Integer(FK) | 否 | 批次ID |
| lot_name | String(50) | 否 | 批次名称 |
| package_id | Integer(FK) | 否 | 包裹ID |
| result_package_id | Integer(FK) | 否 | 结果包裹ID |
| owner_id | Integer(FK) | 否 | 货主ID |
| qty_done | Decimal(16,4) | 是 | 完成数量 |
| product_uom_qty | Decimal(16,4) | 是 | 预留数量 |
| state | Enum | 是 | 状态：draft/confirmed/assigned/done/cancel |
| company_id | Integer(FK) | 是 | 所属公司ID |
| create_time | DateTime | 是 | 创建时间 |
| write_time | DateTime | 是 | 最后更新时间 |

#### 约束规则
- qty_done >= 0
- product_uom_qty >= 0
- 同一批次/序列号在同一次移动中只能有一条记录

---

### 1.7 StockQuant（库存数量）

库存数量按产品+库位+批次+序列号维度存储。

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Integer | 是 | 主键ID |
| product_id | Integer(FK) | 是 | 产品ID |
| location_id | Integer(FK) | 是 | 库位ID |
| lot_id | Integer(FK) | 否 | 批次ID |
| package_id | Integer(FK) | 否 | 包裹ID |
| owner_id | Integer(FK) | 否 | 货主ID |
| quantity | Decimal(16,4) | 是 | 当前数量 |
| reserved_quantity | Decimal(16,4) | 是 | 预留数量 |
| available_quantity | Decimal(16,4) | 是 | 可用数量（计算字段） |
| in_date | DateTime | 否 | 入库日期 |
| company_id | Integer(FK) | 是 | 所属公司ID |
| create_time | DateTime | 是 | 创建时间 |
| write_time | DateTime | 是 | 最后更新时间 |

#### 唯一约束
- (product_id, location_id, lot_id, package_id, owner_id) 唯一

#### 计算字段
```
available_quantity = quantity - reserved_quantity
```

#### 约束规则
- quantity >= 0
- reserved_quantity >= 0
- reserved_quantity <= quantity

---

### 1.8 InventoryTransaction（库存交易）

记录所有库存变化，提供完整的审计追踪。

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Integer | 是 | 主键ID |
| reference | String(100) | 是 | 参考单号 |
| origin | String(100) | 否 | 来源单据 |
| product_id | Integer(FK) | 是 | 产品ID |
| product_uom_id | Integer(FK) | 是 | 计量单位ID |
| location_id | Integer(FK) | 是 | 源库位ID |
| location_dest_id | Integer(FK) | 是 | 目标库位ID |
| lot_id | Integer(FK) | 否 | 批次ID |
| package_id | Integer(FK) | 否 | 包裹ID |
| owner_id | Integer(FK) | 否 | 货主ID |
| quantity | Decimal(16,4) | 是 | 交易数量（正数为入库，负数为出库） |
| inventory_value | Decimal(18,4) | 是 | 库存价值 |
| company_id | Integer(FK) | 是 | 所属公司ID |
| picking_id | Integer(FK) | 否 | 调拨单ID |
| move_id | Integer(FK) | 否 | 移动明细ID |
| move_line_id | Integer(FK) | 否 | 移动明细行ID |
| transaction_type | Enum | 是 | 交易类型：incoming/outgoing/internal_adjustment/inventory_adjustment/production/scrap |
| state | Enum | 是 | 状态：draft/done/cancel |
| transaction_date | DateTime | 是 | 交易日期 |
| create_uid | Integer(FK) | 是 | 创建人ID |
| create_time | DateTime | 是 | 创建时间 |
| write_time | DateTime | 是 | 最后更新时间 |

#### 交易类型说明
| 类型 | 说明 |
|------|------|
| incoming | 入库（收货） |
| outgoing | 出库（发货） |
| internal_adjustment | 内部调拨 |
| inventory_adjustment | 盘点调整 |
| production | 生产入库/出库 |
| scrap | 报废 |

---

## 2. 关键机制设计

### 2.1 库存预留机制

#### 触发时机
调拨单状态从 `draft` → `confirmed` 时自动触发预留

#### 预留流程
```
1. 遍历调拨单的所有StockMove
2. 对每条Move调用预留逻辑：
   a. 查询StockQuant（按FIFO原则）
      - WHERE product_id = ? AND location_id = ?
      - AND quantity > reserved_quantity
      - ORDER BY in_date ASC
   b. 分配可用数量到MoveLine
      - 创建或更新MoveLine.product_uom_qty
      - 更新StockQuant.reserved_quantity
   c. 更新Move状态
      - 全部预留成功：state = 'assigned'
      - 部分预留成功：state = 'confirmed', 更新reserved_availability
      - 无库存可预留：state = 'confirmed'
```

#### 预留策略
```python
# 按调拨类型配置
reservation_method:
  - 'manual': 手动预留，不自动执行
  - 'auto_at_confirm': 确认时自动预留
  - 'by_product': 按产品配置的预留策略
```

#### 取消预留流程
调拨单取消时：
```
1. 遍历所有MoveLine
2. 释放预留数量：
   - StockQuant.reserved_quantity -= MoveLine.product_uom_qty
   - MoveLine.product_uom_qty = 0
3. 更新Move和Picking状态为'cancel'
```

---

### 2.2 自动库存更新机制

#### 触发时机
调拨单状态变更到 `done` 时

#### 更新流程
```
1. 验证调拨单：
   - 检查所有Move的quantity_done > 0
   - 检查所有MoveLine的qty_done > 0

2. 处理源库位（出库）：
   FOR each MoveLine:
     a. 查询或创建StockQuant（源库位）
     b. 验证数量充足：
        - quantity >= qty_done
     c. 扣减库存：
        - StockQuant.quantity -= qty_done
        - StockQuant.reserved_quantity -= product_uom_qty
     d. 创建交易记录（InventoryTransaction）
        - quantity = -qty_done（负数表示出库）

3. 处理目标库位（入库）：
   FOR each MoveLine:
     a. 查询或创建StockQuant（目标库位）
     b. 增加库存：
        - StockQuant.quantity += qty_done
        - 如有批次信息，设置lot_id
        - 设置in_date = 当前时间
     c. 创建交易记录（InventoryTransaction）
        - quantity = qty_done（正数表示入库）

4. 更新状态：
   - Move.state = 'done'
   - Picking.state = 'done'
   - Picking.date_done = 当前时间
```

#### 数量验证规则
```python
# 源库位出库验证
def validate_outgoing(move_line):
    quant = get_quant(
        product_id=move_line.product_id,
        location_id=move_line.location_id,
        lot_id=move_line.lot_id,
        package_id=move_line.package_id
    )
    if quant.quantity - quant.reserved_quantity < move_line.qty_done:
        raise InsufficientStockError("可用库存不足")
```

---

### 2.3 交易记录生成机制

#### 触发时机
任何导致 StockQuant.quantity 变化的操作

#### 生成规则
```
每次库存变化生成2条交易记录：
1. 出库交易：从源库位出库
   - location_id: 源库位
   - location_dest_id: 目标库位
   - quantity: 负数（-qty）
   - transaction_type: 根据操作类型确定

2. 入库交易：到目标库位入库
   - location_id: 源库位
   - location_dest_id: 目标库位
   - quantity: 正数（+qty）
   - transaction_type: 根据操作类型确定
```

#### 交易类型映射
| 操作类型 | transaction_type |
|---------|-----------------|
| 收货单完成 | incoming |
| 发货单完成 | outgoing |
| 内部调拨完成 | internal_adjustment |
| 盘点调整 | inventory_adjustment |
| 生产入库 | production |
| 报废 | scrap |

#### 审计追踪
```sql
-- 查询某产品的完整交易历史
SELECT *
FROM inventory_transaction
WHERE product_id = ?
ORDER BY transaction_date DESC;

-- 查询某库位的库存变化
SELECT *
FROM inventory_transaction
WHERE location_id = ? OR location_dest_id = ?
ORDER BY transaction_date DESC;
```

---

### 2.4 序列码生成规则

#### 生成机制
```
格式：{prefix}{separator}{current_value}{padding}

示例配置：
- prefix: "WH/IN/"
- separator: "/"
- padding: 5位数字
- initial: 1

生成结果：
WH/IN/00001, WH/IN/00002, WH/IN/00003, ...
```

#### 序列号表设计
| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Integer | 主键ID |
| name | String(100) | 序列名称 |
| code | String(50) | 序列编码 |
| prefix | String(50) | 前缀 |
| suffix | String(50) | 后缀 |
| separator | String(10) | 分隔符 |
| padding | Integer | 补零位数 |
| next_value | Integer | 下一个值 |
| implementation | Enum | 实现方式：standard/no_gap |

#### 按调拨类型生成
```python
def generate_picking_name(picking_type):
    sequence = picking_type.sequence_id
    date = datetime.now()

    # 替换日期变量
    prefix = sequence.prefix
    prefix = prefix.replace('%(year)s', str(date.year))
    prefix = prefix.replace('%(month)s', str(date.month).zfill(2))
    prefix = prefix.replace('%(day)s', str(date.day).zfill(2))

    # 生成编号
    value = str(sequence.next_value).zfill(sequence.padding)
    name = f"{prefix}{sequence.separator}{value}"

    # 更新序列号
    sequence.next_value += 1

    return name
```

#### 默认序列号配置
| 调拨类型 | 前缀示例 | 说明 |
|---------|---------|------|
| incoming | WH/IN/%(year)s/ | 收货单 |
| outgoing | WH/OUT/%(year)s/ | 发货单 |
| internal | WH/INT/%(year)s/ | 内部调拨 |
| dropship | WH/DS/%(year)s/ | 直发单 |

---

## 3. 状态流转设计

### 3.1 Picking（调拨单）状态流转

```
┌─────────┐
│  draft  │ 新建
└────┬────┘
     │ action_confirm()
     ▼
┌───────────┐
│ confirmed │ 已确认（待分配）
└─────┬─────┘
      │ action_assign()
      ▼
┌──────────┐
│ assigned │ 已分配（库存已预留）
└────┬─────┘
     │ button_validate()
     ├──────────┐
     ▼          ▼
┌──────┐  ┌─────────┐
│ done │  │ cancel  │
└──────┘  └─────────┘
```

#### 状态转换详细说明

| 当前状态 | 动作 | 目标状态 | 前置条件 | 后置操作 |
|---------|------|---------|---------|---------|
| draft | action_confirm | confirmed | 存在至少一条Move | 触发预留逻辑 |
| confirmed | action_assign | assigned | 有足够库存 | 预留库存，更新Move状态 |
| confirmed | action_assign | confirmed | 库存不足 | 部分预留，保持confirmed |
| assigned | button_validate | done | 所有Move已验证 | 更新库存，生成交易记录 |
| draft | action_cancel | cancel | 无 | 清理数据 |
| confirmed | action_cancel | cancel | 无预留数据 | 释放预留 |
| assigned | action_cancel | cancel | 有预留数据 | 释放预留，清理数据 |

#### 特殊流程
```python
# 强制完成（忽略未预留的库存）
def force_validate(picking):
    for move in picking.move_ids:
        if move.reserved_availability < move.product_uom_qty:
            # 创建额外的MoveLine补齐数量
            create_move_line(move, move.product_uom_qty - move.reserved_availability)
    picking.button_validate()
```

---

### 3.2 Move（移动明细）状态流转

```
┌─────────┐
│  draft  │
└────┬────┘
     │ 父Picking确认
     ▼
┌───────────┐
│ confirmed │
└─────┬─────┘
      │ 预留成功
      ▼
┌──────────┐
│ assigned │
└────┬─────┘
     │ 验证
     ├──────────┐
     ▼          ▼
┌──────┐  ┌─────────┐
│ done │  │ cancel  │
└──────┘  └─────────┘
```

#### 状态计算逻辑
```python
def compute_move_state(move):
    if move.picking_id.state == 'draft':
        return 'draft'

    if move.picking_id.state == 'cancel':
        return 'cancel'

    if move.picking_id.state == 'done':
        return 'done'

    # confirmed或assigned状态
    if move.reserved_availability == move.product_uom_qty:
        return 'assigned'
    elif move.reserved_availability > 0:
        return 'confirmed'  # 部分预留
    else:
        return 'confirmed'  # 未预留
```

---

### 3.3 MoveLine（移动明细行）状态流转

```
┌─────────┐
│  draft  │ 创建时
└────┬────┘
     │ 预留操作
     ▼
┌───────────┐
│ confirmed │ 有预留数量
└─────┬─────┘
      │ 分配成功
      ▼
┌──────────┐
│ assigned │ 库存已预留
└────┬─────┘
     │ 验证完成
     ▼
┌──────┐
│ done │
└──────┘
```

#### 状态说明
| 状态 | 说明 | product_uom_qty | qty_done |
|------|------|----------------|----------|
| draft | 新创建 | 0 | 0 |
| confirmed | 已预留 | >0 | 0 |
| assigned | 已分配 | >0 | 0 |
| done | 已完成 | >0 | =product_uom_qty |

---

## 4. API接口设计

### 4.1 基础数据管理

#### 4.1.1 仓库管理

##### 创建仓库
```
POST /api/v1/warehouses
```

**请求体：**
```json
{
  "name": "主仓库",
  "code": "WH01",
  "company_id": 1,
  "partner_id": 10,
  "address": "北京市朝阳区..."
}
```

**响应：**
```json
{
  "id": 1,
  "name": "主仓库",
  "code": "WH01",
  "lot_stock_id": 101,
  "input_stock_id": 102,
  "output_stock_id": 103,
  "create_time": "2024-01-01T10:00:00Z"
}
```

##### 查询仓库列表
```
GET /api/v1/warehouses?page=1&page_size=20&active=true
```

**响应：**
```json
{
  "total": 5,
  "page": 1,
  "page_size": 20,
  "data": [
    {
      "id": 1,
      "name": "主仓库",
      "code": "WH01",
      "active": true,
      ...
    }
  ]
}
```

##### 更新仓库
```
PUT /api/v1/warehouses/{id}
```

##### 删除仓库
```
DELETE /api/v1/warehouses/{id}
```

---

#### 4.1.2 库位管理

##### 创建库位
```
POST /api/v1/locations
```

**请求体：**
```json
{
  "name": "A区货架1",
  "location_id": 10,
  "usage": "internal",
  "code": "A01",
  "company_id": 1
}
```

**响应：**
```json
{
  "id": 100,
  "name": "A区货架1",
  "complete_name": "主仓库/A区/A区货架1",
  "parent_path": "1/10/100/",
  ...
}
```

##### 查询库位树形结构
```
GET /api/v1/locations/tree?warehouse_id=1
```

**响应：**
```json
{
  "id": 1,
  "name": "主仓库",
  "complete_name": "主仓库",
  "children": [
    {
      "id": 10,
      "name": "A区",
      "children": [...]
    }
  ]
}
```

##### 查询库位库存
```
GET /api/v1/locations/{id}/quants
```

---

#### 4.1.3 调拨类型管理

##### 创建调拨类型
```
POST /api/v1/picking-types
```

**请求体：**
```json
{
  "name": "收货单",
  "code": "incoming",
  "warehouse_id": 1,
  "sequence_code": "WH/IN/",
  "default_location_src_id": 50,
  "default_location_dest_id": 102,
  "reservation_method": "auto_at_confirm"
}
```

##### 查询调拨类型列表
```
GET /api/v1/picking-types?warehouse_id=1
```

---

### 4.2 调拨单操作

#### 4.2.1 创建调拨单
```
POST /api/v1/pickings
```

**请求体：**
```json
{
  "picking_type_id": 1,
  "partner_id": 100,
  "location_id": 50,
  "location_dest_id": 101,
  "scheduled_date": "2024-01-10",
  "origin": "PO20240001",
  "move_lines": [
    {
      "product_id": 10,
      "product_uom": 1,
      "product_uom_qty": 100,
      "name": "产品A"
    },
    {
      "product_id": 20,
      "product_uom": 1,
      "product_uom_qty": 50,
      "name": "产品B"
    }
  ]
}
```

**响应：**
```json
{
  "id": 1001,
  "name": "WH/IN/2024/00001",
  "state": "draft",
  "move_ids": [
    {
      "id": 5001,
      "product_id": 10,
      "product_uom_qty": 100,
      "state": "draft"
    },
    {
      "id": 5002,
      "product_id": 20,
      "product_uom_qty": 50,
      "state": "draft"
    }
  ],
  ...
}
```

---

#### 4.2.2 确认调拨单
```
POST /api/v1/pickings/{id}/confirm
```

**功能：**
- 状态：draft → confirmed
- 触发库存预留
- 自动生成调拨单号（如未生成）

**响应：**
```json
{
  "id": 1001,
  "state": "confirmed",
  "move_ids": [
    {
      "id": 5001,
      "state": "assigned",
      "reserved_availability": 100
    },
    {
      "id": 5002,
      "state": "confirmed",
      "reserved_availability": 30
    }
  ]
}
```

**异常情况：**
```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "产品B库存不足",
    "details": {
      "product_id": 20,
      "required": 50,
      "available": 30
    }
  }
}
```

---

#### 4.2.3 分配库存（预留）
```
POST /api/v1/pickings/{id}/assign
```

**功能：**
- 手动触发库存预留
- 返回预留结果

**响应：**
```json
{
  "success": true,
  "assigned_moves": 2,
  "partial_moves": 0,
  "unassigned_moves": 1,
  "details": [
    {
      "move_id": 5001,
      "product_id": 10,
      "required": 100,
      "reserved": 100,
      "state": "assigned"
    },
    {
      "move_id": 5002,
      "product_id": 20,
      "required": 50,
      "reserved": 50,
      "state": "assigned"
    },
    {
      "move_id": 5003,
      "product_id": 30,
      "required": 20,
      "reserved": 0,
      "state": "confirmed",
      "reason": "库存不足"
    }
  ]
}
```

---

#### 4.2.4 完成调拨单
```
POST /api/v1/pickings/{id}/validate
```

**请求体：**
```json
{
  "move_lines": [
    {
      "move_id": 5001,
      "qty_done": 100,
      "lot_id": null
    },
    {
      "move_id": 5002,
      "qty_done": 45,
      "lot_id": 200
    }
  ]
}
```

**功能：**
- 状态：assigned → done
- 更新StockQuant
- 生成InventoryTransaction
- 记录完成时间

**响应：**
```json
{
  "id": 1001,
  "state": "done",
  "date_done": "2024-01-10T15:30:00Z",
  "transactions_created": 4,
  "quant_updated": 2
}
```

---

#### 4.2.5 取消调拨单
```
POST /api/v1/pickings/{id}/cancel
```

**功能：**
- 状态：draft/confirmed/assigned → cancel
- 释放预留库存
- 清理相关数据

**响应：**
```json
{
  "id": 1001,
  "state": "cancel",
  "reservation_released": true,
  "released_quantities": [
    {
      "product_id": 10,
      "quantity": 100,
      "location_id": 101
    }
  ]
}
```

---

#### 4.2.6 查询调拨单详情
```
GET /api/v1/pickings/{id}
```

**响应：**
```json
{
  "id": 1001,
  "name": "WH/IN/2024/00001",
  "picking_type_id": 1,
  "picking_type_name": "收货单",
  "state": "assigned",
  "partner_id": 100,
  "partner_name": "供应商A",
  "location_id": 50,
  "location_name": "供应商库位",
  "location_dest_id": 101,
  "location_dest_name": "主仓库/库存",
  "scheduled_date": "2024-01-10",
  "origin": "PO20240001",
  "move_ids": [
    {
      "id": 5001,
      "product_id": 10,
      "product_name": "产品A",
      "product_uom": "件",
      "product_uom_qty": 100,
      "reserved_availability": 100,
      "quantity_done": 0,
      "state": "assigned",
      "move_line_ids": [
        {
          "id": 6001,
          "product_id": 10,
          "product_uom_qty": 100,
          "qty_done": 0,
          "lot_id": null,
          "state": "assigned"
        }
      ]
    }
  ],
  "create_time": "2024-01-05T10:00:00Z",
  "write_time": "2024-01-05T10:30:00Z"
}
```

---

#### 4.2.7 查询调拨单列表
```
GET /api/v1/pickings?page=1&page_size=20&state=assigned&picking_type_id=1
```

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| page | Integer | 页码 |
| page_size | Integer | 每页数量 |
| state | String | 状态过滤 |
| picking_type_id | Integer | 调拨类型过滤 |
| partner_id | Integer | 合作伙伴过滤 |
| product_id | Integer | 产品过滤（移动明细中包含该产品） |
| scheduled_date_from | Date | 计划日期起始 |
| scheduled_date_to | Date | 计划日期结束 |
| origin | String | 来源单据 |

---

### 4.3 库存查询

#### 4.3.1 按产品查询库存
```
GET /api/v1/quants?product_id=10
```

**响应：**
```json
{
  "total": 3,
  "data": [
    {
      "id": 1,
      "product_id": 10,
      "product_name": "产品A",
      "location_id": 101,
      "location_name": "主仓库/库存",
      "lot_id": null,
      "quantity": 500,
      "reserved_quantity": 100,
      "available_quantity": 400,
      "in_date": "2024-01-01T10:00:00Z"
    },
    {
      "id": 2,
      "product_id": 10,
      "product_name": "产品A",
      "location_id": 102,
      "location_name": "主仓库/入库",
      "lot_id": 200,
      "lot_name": "LOT20240001",
      "quantity": 200,
      "reserved_quantity": 0,
      "available_quantity": 200,
      "in_date": "2024-01-05T14:00:00Z"
    }
  ]
}
```

---

#### 4.3.2 按库位查询库存
```
GET /api/v1/quants?location_id=101
```

**响应：**
```json
{
  "total": 50,
  "data": [
    {
      "id": 1,
      "product_id": 10,
      "product_name": "产品A",
      "location_id": 101,
      "location_name": "主仓库/库存",
      "quantity": 500,
      "reserved_quantity": 100,
      "available_quantity": 400
    },
    ...
  ]
}
```

---

#### 4.3.3 按批次查询库存
```
GET /api/v1/quants?lot_id=200
```

---

#### 4.3.4 库存汇总查询
```
GET /api/v1/quants/summary?product_id=10&group_by=location
```

**响应：**
```json
{
  "product_id": 10,
  "total_quantity": 700,
  "total_reserved": 100,
  "total_available": 600,
  "by_location": [
    {
      "location_id": 101,
      "location_name": "主仓库/库存",
      "quantity": 500,
      "reserved": 100,
      "available": 400
    },
    {
      "location_id": 102,
      "location_name": "主仓库/入库",
      "quantity": 200,
      "reserved": 0,
      "available": 200
    }
  ]
}
```

---

### 4.4 库存交易查询

#### 4.4.1 交易记录列表
```
GET /api/v1/inventory-transactions?page=1&page_size=50&product_id=10
```

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| product_id | Integer | 产品ID |
| location_id | Integer | 库位ID |
| transaction_type | String | 交易类型 |
| transaction_date_from | DateTime | 交易日期起始 |
| transaction_date_to | DateTime | 交易日期结束 |
| reference | String | 参考单号 |
| origin | String | 来源单据 |

---

#### 4.4.2 交易详情
```
GET /api/v1/inventory-transactions/{id}
```

---

#### 4.4.3 库存移动历史
```
GET /api/v1/inventory-transactions/history?product_id=10&location_id=101
```

**响应：**
```json
{
  "product_id": 10,
  "location_id": 101,
  "opening_balance": 300,
  "closing_balance": 500,
  "transactions": [
    {
      "id": 1001,
      "transaction_date": "2024-01-01T10:00:00Z",
      "transaction_type": "incoming",
      "reference": "WH/IN/2024/00001",
      "quantity": 200,
      "balance": 500
    },
    {
      "id": 1002,
      "transaction_date": "2024-01-02T14:00:00Z",
      "transaction_type": "outgoing",
      "reference": "WH/OUT/2024/00001",
      "quantity": -100,
      "balance": 300
    }
  ]
}
```

---

### 4.5 库存盘点

#### 4.5.1 创建盘点单
```
POST /api/v1/inventory-adjustments
```

**请求体：**
```json
{
  "name": "年度盘点-2024",
  "location_id": 101,
  "product_ids": [10, 20, 30],
  "inventory_date": "2024-12-31"
}
```

---

#### 4.5.2 执行盘点
```
POST /api/v1/inventory-adjustments/{id}/start
```

**功能：**
- 锁定盘点范围
- 生成盘点明细

---

#### 4.5.3 录入盘点结果
```
POST /api/v1/inventory-adjustments/{id}/lines
```

**请求体：**
```json
{
  "lines": [
    {
      "product_id": 10,
      "location_id": 101,
      "lot_id": null,
      "theoretical_qty": 500,
      "actual_qty": 498
    },
    {
      "product_id": 20,
      "location_id": 101,
      "lot_id": 200,
      "theoretical_qty": 200,
      "actual_qty": 200
    }
  ]
}
```

---

#### 4.5.4 确认盘点
```
POST /api/v1/inventory-adjustments/{id}/validate
```

**功能：**
- 计算差异
- 生成调整调拨单
- 更新库存
- 生成交易记录

---

## 5. 模型关系图

### 5.1 核心模型关系

```
┌─────────────┐
│ StockWarehouse│
└──────┬───────┘
       │
       │ 1:N
       ▼
┌──────────────┐         ┌──────────────┐
│StockPickingType├────────┤StockLocation │
└──────┬─────────┘         └───────┬──────┘
       │                           │
       │ 1:N                       │ N:N
       ▼                           │
┌──────────────┐                   │
│ StockPicking │◄──────────────────┘
└──────┬───────┘
       │
       │ 1:N
       ▼
┌──────────────┐         ┌──────────────┐
│  StockMove   ├─────────►│   Product    │
└──────┬───────┘         └──────────────┘
       │
       │ 1:N
       ▼
┌──────────────┐         ┌──────────────┐
│ StockMoveLine├─────────►│   Lot        │
└──────┬───────┘         └──────────────┘
       │
       │ 触发
       ▼
┌──────────────────┐     ┌──────────────┐
│InventoryTransaction├────►│ StockQuant   │
└──────────────────┘     └──────────────┘
```

### 5.2 详细关系说明

#### StockWarehouse 关系
```
StockWarehouse
  ├─ lot_stock_id ───► StockLocation (存货库位)
  ├─ input_stock_id ─► StockLocation (入库库位)
  ├─ output_stock_id ─► StockLocation (出库库位)
  ├─ qc_stock_id ────► StockLocation (质检库位)
  └─ view_location_id ─► StockLocation (视图库位)
```

#### StockPicking 关系
```
StockPicking
  ├─ picking_type_id ──► StockPickingType
  ├─ location_id ───────► StockLocation (源库位)
  ├─ location_dest_id ──► StockLocation (目标库位)
  ├─ partner_id ────────► Partner
  ├─ move_ids ──────────► StockMove[]
  │                        ├─ product_id ──► Product
  │                        ├─ location_id ──► StockLocation
  │                        ├─ location_dest_id ──► StockLocation
  │                        └─ move_line_ids ──► StockMoveLine[]
  │                                             ├─ lot_id ──► Lot
  │                                             └─ package_id ──► Package
  └─ company_id ────────► Company
```

#### StockQuant 关系
```
StockQuant
  ├─ product_id ────► Product
  ├─ location_id ────► StockLocation
  ├─ lot_id ─────────► Lot
  ├─ package_id ─────► Package
  └─ owner_id ───────► Partner
```

#### InventoryTransaction 关系
```
InventoryTransaction
  ├─ product_id ────────► Product
  ├─ location_id ────────► StockLocation (源库位)
  ├─ location_dest_id ──► StockLocation (目标库位)
  ├─ lot_id ────────────► Lot
  ├─ package_id ────────► Package
  ├─ picking_id ────────► StockPicking
  ├─ move_id ───────────► StockMove
  └─ move_line_id ──────► StockMoveLine
```

---

## 6. 数据库索引设计

### 6.1 StockLocation 索引
```sql
CREATE INDEX idx_location_parent ON stock_location(location_id);
CREATE INDEX idx_location_parent_path ON stock_location(parent_path);
CREATE INDEX idx_location_usage ON stock_location(usage);
CREATE INDEX idx_location_company ON stock_location(company_id);
```

### 6.2 StockPicking 索引
```sql
CREATE INDEX idx_picking_type ON stock_picking(picking_type_id);
CREATE INDEX idx_picking_state ON stock_picking(state);
CREATE INDEX idx_picking_location ON stock_picking(location_id);
CREATE INDEX idx_picking_location_dest ON stock_picking(location_dest_id);
CREATE INDEX idx_picking_partner ON stock_picking(partner_id);
CREATE INDEX idx_picking_scheduled_date ON stock_picking(scheduled_date);
CREATE INDEX idx_picking_origin ON stock_picking(origin);
```

### 6.3 StockMove 索引
```sql
CREATE INDEX idx_move_picking ON stock_move(picking_id);
CREATE INDEX idx_move_product ON stock_move(product_id);
CREATE INDEX idx_move_state ON stock_move(state);
CREATE INDEX idx_move_location ON stock_move(location_id);
CREATE INDEX idx_move_location_dest ON stock_move(location_dest_id);
```

### 6.4 StockMoveLine 索引
```sql
CREATE INDEX idx_moveline_move ON stock_move_line(move_id);
CREATE INDEX idx_moveline_picking ON stock_move_line(picking_id);
CREATE INDEX idx_moveline_product ON stock_move_line(product_id);
CREATE INDEX idx_moveline_location ON stock_move_line(location_id);
CREATE INDEX idx_moveline_lot ON stock_move_line(lot_id);
CREATE INDEX idx_moveline_result_package ON stock_move_line(result_package_id);
```

### 6.5 StockQuant 索引
```sql
CREATE UNIQUE INDEX idx_quant_unique ON stock_quant(product_id, location_id, lot_id, package_id, owner_id);
CREATE INDEX idx_quant_product ON stock_quant(product_id);
CREATE INDEX idx_quant_location ON stock_quant(location_id);
CREATE INDEX idx_quant_lot ON stock_quant(lot_id);
CREATE INDEX idx_quant_quantity ON stock_quant(quantity);
```

### 6.6 InventoryTransaction 索引
```sql
CREATE INDEX idx_trans_product ON inventory_transaction(product_id);
CREATE INDEX idx_trans_location ON inventory_transaction(location_id);
CREATE INDEX idx_trans_location_dest ON inventory_transaction(location_dest_id);
CREATE INDEX idx_trans_date ON inventory_transaction(transaction_date);
CREATE INDEX idx_trans_type ON inventory_transaction(transaction_type);
CREATE INDEX idx_trans_picking ON inventory_transaction(picking_id);
CREATE INDEX idx_trans_reference ON inventory_transaction(reference);
```

---

## 7. 业务规则与约束

### 7.1 数量约束
1. StockQuant.quantity >= 0
2. StockQuant.reserved_quantity >= 0
3. StockQuant.reserved_quantity <= StockQuant.quantity
4. StockMove.product_uom_qty >= 0
5. StockMove.quantity_done <= StockMove.product_uom_qty
6. StockMoveLine.qty_done >= 0
7. StockMoveLine.product_uom_qty >= 0

### 7.2 状态约束
1. Picking.state = 'done' 时，所有 Move.state 必须为 'done'
2. Move.state = 'done' 时，所有 MoveLine.state 必须为 'done'
3. Picking.state = 'assigned' 时，所有 Move 必须已预留
4. 删除 Picking 时，级联删除所有 Move 和 MoveLine

### 7.3 业务约束
1. usage='view' 的库位不能存放实际库存
2. 报废库位每个仓库只能有一个
3. 已完成的调拨单不能修改
4. 已预留的库存不能被其他调拨单预留
5. 取消调拨单必须释放预留库存

---

## 8. 扩展功能

### 8.1 包裹管理
- Package：包裹管理
- 一包裹可包含多个产品
- 支持整包移动和追踪

### 8.2 批次管理
- Lot：批次管理
- 支持批次追溯
- 支持批次过期管理
- 支持批次属性（生产日期、过期日期等）

### 8.3 序列号管理
- 序列号级别追踪
- 每个序列号唯一
- 支持序列号全生命周期追踪

### 8.4 多公司支持
- 所有模型关联 company_id
- 数据隔离
- 跨公司调拨

### 8.5 多仓库支持
- 跨仓库调拨
- 仓库间补货规则
- 仓库路由配置

---

## 9. 性能优化建议

### 9.1 查询优化
1. 使用物化路径（parent_path）快速查询库位子树
2. StockQuant 表按产品ID分区
3. InventoryTransaction 表按日期分区

### 9.2 缓存策略
1. 缓存仓库配置信息
2. 缓存库位树形结构
3. 缓存产品信息

### 9.3 批量操作
1. 批量预留库存
2. 批量更新库存
3. 批量创建交易记录

---

## 10. API响应码定义

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 参数错误 |
| 404 | 资源不存在 |
| 409 | 业务冲突（如库存不足） |
| 500 | 服务器错误 |

### 业务错误码
| 错误码 | 说明 |
|--------|------|
| INSUFFICIENT_STOCK | 库存不足 |
| LOCATION_NOT_FOUND | 库位不存在 |
| INVALID_STATE_TRANSITION | 无效状态转换 |
| PICKING_ALREADY_DONE | 调拨单已完成 |
| MOVE_LINE_NOT_RESERVED | 明细行未预留 |
| QUANTITY_EXCEEDS_AVAILABLE | 数量超过可用数量 |

---

## 11. 版本信息

- **文档版本**: v1.0
- **创建日期**: 2024-01-01
- **最后更新**: 2024-01-01
- **作者**: 系统架构师
- **适用版本**: FastAPI + SQLAlchemy

---

## 附录A：状态流转完整流程图

```
┌──────────────────────────────────────────────────────────────┐
│                     调拨单生命周期                              │
└──────────────────────────────────────────────────────────────┘

   创建调拨单
       │
       ▼
   [DRAFT] ────────────┐
       │                │
       │ 确认           │ 取消
       ▼                ▼
  [CONFIRMED] ──────► [CANCEL]
       │
       │ 库存预留
       │
       ├───────┬───────┐
       │       │       │
       ▼       ▼       │
   [全部预留  [部分预留  │
    成功]     成功]     │
       │       │       │
       │       │       │
       ▼       ▼       │
  [ASSIGNED] [CONFIRMED]│
       │       │       │
       │ 验证  │ 强制验证│
       ├───────┴───────┘
       │
       ▼
     [DONE]
```

---

## 附录B：数据库表设计概要

### 核心表清单
| 表名 | 说明 | 主要字段 |
|------|------|---------|
| stock_location | 库位表 | id, name, location_id, usage, parent_path |
| stock_warehouse | 仓库表 | id, name, code, lot_stock_id, input_stock_id |
| stock_picking_type | 调拨类型表 | id, name, code, sequence_id, warehouse_id |
| stock_picking | 调拨单表 | id, name, picking_type_id, state, location_id |
| stock_move | 移动明细表 | id, picking_id, product_id, product_uom_qty |
| stock_move_line | 移动明细行表 | id, move_id, qty_done, lot_id, package_id |
| stock_quant | 库存数量表 | id, product_id, location_id, lot_id, quantity |
| inventory_transaction | 库存交易表 | id, product_id, location_id, quantity, transaction_type |

### 辅助表清单
| 表名 | 说明 |
|------|------|
| ir_sequence | 序列号表 |
| product_product | 产品表 |
| product_uom | 计量单位表 |
| stock_lot | 批次表 |
| stock_package | 包裹表 |
| res_partner | 合作伙伴表 |
| res_company | 公司表 |

---

**文档结束**