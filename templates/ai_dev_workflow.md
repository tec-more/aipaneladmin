# AI驱动开发工作流模板

## 📋 使用说明

将本模板复制到你的需求文档中，填写相关内容，然后发送给AI进行自动化开发。

---

## 1️⃣ 需求描述模板

```markdown
### 功能需求
[一句话描述这个功能做什么]

### 业务背景
[为什么需要这个功能？解决什么问题？]

### 用户场景
[谁会使用这个功能？在什么场景下使用？]

### 参考文档
[提供API文档、接口文档、第三方SDK文档等链接或内容]

### 期望结果
[最终要达成什么效果？]
```

**示例：**

```markdown
### 功能需求
实现微信支付Native扫码支付功能

### 业务背景
PC端用户需要购买会员套餐，需要使用微信扫码支付

### 用户场景
1. 用户在PC端选择购买会员
2. 系统生成支付二维码
3. 用户使用微信扫码支付
4. 支付完成后自动跳转到订单详情页

### 参考文档
- 微信支付Native下单API：https://pay.weixin.qq.com/wiki/doc/apiv3/apis/chapter3_4_1.shtml
- 微信支付订单查询API：https://pay.weixin.qq.com/wiki/doc/apiv3/apis/chapter3_4_2.shtml

### 期望结果
用户能够成功扫码支付，支付后能正确更新订单状态
```

---

## 2️⃣ API接口分析模板

```markdown
### 接口名称
[接口功能名称]

### 请求方式
[GET / POST / PUT / DELETE]

### 请求路径
[API路径]

### 请求参数
| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| param1 | string | 是 | 参数说明 | xxx |
| param2 | int | 否 | 参数说明 | 123 |

### 响应参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| field1 | string | 字段说明 |
| field2 | int | 字段说明 |

### 错误码
| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| ERR001 | 错误说明 | 处理方法 |

### 验证规则
- [ ] 必填字段检查
- [ ] 数据格式验证
- [ ] 业务逻辑验证
- [ ] 权限验证
```

---

## 3️⃣ 代码结构分析模板

AI会根据以下结构分析参考代码：

```markdown
### 现有类似实现
[指出项目中是否有类似的实现可以参考]

### 依赖模块
- 模块1: [用途]
- 模块2: [用途]

### 数据模型
- Model: [涉及的数据库表]
- Schema: [请求/响应Schema]

### 服务层
- Service: [业务逻辑服务]
- 依赖的外部服务: [第三方API等]
```

---

## 4️⃣ AI任务分解模板

AI会自动将需求分解为以下任务：

```markdown
## 任务列表

### Phase 1: 分析阶段 ✅
- [ ] 分析参考文档，提取关键信息
- [ ] 识别输入参数和输出格式
- [ ] 确定验证规则和错误处理
- [ ] 设计数据结构和API接口

### Phase 2: 设计阶段 📐
- [ ] 设计Schema（请求/响应模型）
- [ ] 设计Service层业务逻辑
- [ ] 设计API路由和端点
- [ ] 设计错误处理机制

### Phase 3: 实现阶段 💻
- [ ] 实现Schema定义
- [ ] 实现Service层
- [ ] 实现API路由
- [ ] 实现错误处理

### Phase 4: 测试阶段 🧪
- [ ] 单元测试
- [ ] 集成测试
- [ ] 手动测试验证

### Phase 5: 文档阶段 📚
- [ ] 更新API文档
- [ ] 添加使用示例
- [ ] 更新README
```

---

## 5️⃣ 代码生成指令模板

### 给AI的完整提示词模板

```markdown
## 开发任务

你是一个专业的全栈开发工程师，请根据以下信息完成开发任务。

### 📄 参考文档
{{粘贴参考文档内容或链接}}

### 🎯 需求描述
{{粘贴需求描述模板内容}}

### 🏗️ 项目技术栈
- 框架: FastAPI
- ORM: Tortoise-ORM
- 数据库: MySQL
- 认证: JWT

### 📁 项目结构
```
base/plugins/
├── {{plugin_name}}/
│   ├── manifest.json          # 插件配置
│   ├── models/                # 数据模型
│   ├── schemas/               # Schema定义
│   ├── services/              # 业务逻辑
│   └── api/v1/                # API路由
```

### ✅ 请按以下步骤完成：

#### Step 1: 信息提取
请从参考文档中提取：
1. 请求参数列表（名称、类型、必填、说明）
2. 响应数据结构
3. 错误码和异常处理
4. 签名/验证逻辑
5. 回调通知机制

#### Step 2: 设计输出
输出以下设计内容：
```python
# 1. Schema定义
from pydantic import BaseModel

class RequestSchema(BaseModel):
    """请求Schema"""
    pass

class ResponseSchema(BaseModel):
    """响应Schema"""
    pass

# 2. Service接口
class XXXService:
    """业务逻辑服务"""
    pass

# 3. API路由设计
# 路由路径、方法、参数、响应
```

#### Step 3: 代码实现
基于设计输出完整的代码实现，包括：
- 完整的Schema定义
- Service层实现
- API路由实现
- 错误处理

#### Step 4: 测试用例
提供测试用的请求示例和预期响应

### ⚠️ 注意事项
1. 遵循项目现有的代码风格
2. 使用项目统一的响应格式（SuccessResponse）
3. 所有异常都用HTTPException包装
4. 添加详细的中文注释
5. 处理所有边界情况

### 🔍 参考现有代码
如果项目中有类似的实现，请参考以下文件：
- {{相关文件路径1}}
- {{相关文件路径2}}

开始执行任务，首先展示你的分析和设计，然后生成代码。
```

---

## 6️⃣ 实战示例

### 示例：实现微信Native支付

#### 输入给AI的完整内容：

```markdown
## 开发任务

### 📄 参考文档
**微信支付Native下单API**
- 接口地址：https://api.mch.weixin.qq.com/v3/pay/transactions/native
- 请求方式：POST
- 请求参数：
  - appid: String, 商户AppID
  - mchid: String, 商户号
  - description: String, 商品描述
  - out_trade_no: String, 商户订单号
  - amount.total: Integer, 订单金额（分）
  - notify_url: String, 通知URL
- 响应参数：
  - code_url: String, 二维码链接
  - prepay_id: String, 预支付交易会话标识

**支付结果查询API**
- 接口地址：https://api.mch.weixin.qq.com/v3/pay/transactions/out-trade-no/{out_trade_no}
- 响应状态：
  - SUCCESS: 支付成功
  - REFUND: 转入退款
  - NOTPAY: 未支付
  - CLOSED: 已关闭
  - REVOKED: 已撤销
  - USERPAYING: 用户支付中
  - PAYERROR: 支付失败

### 🎯 需求描述
实现微信支付Native扫码支付功能。PC端用户购买会员套餐时，系统生成支付二维码，用户扫码完成支付后，前端通过轮询查询支付状态，支付成功后自动跳转到订单详情页。

### 📁 需要实现的接口
1. POST /v1/pay/wechat/native/create - 创建扫码支付订单，返回二维码链接
2. GET /v1/pay/wechat/native/poll/{order_no} - 轮询查询支付状态
3. POST /v1/pay/wechat/native/close/{order_no} - 关闭未支付订单

### ✅ 请按AI任务分解模板执行开发任务
```

#### AI会自动输出：

**Step 1: 信息提取**
```markdown
## 提取的关键信息

### 输入参数
- order_no: 商户订单号（必填）
- total_fee: 支付金额，单位分（必填）
- body: 商品描述（必填）
- attach: 附加数据（可选）

### 输出数据
- code_url: 二维码链接
- prepay_id: 预支付ID
- order_id: 订单号

### 支付状态映射
SUCCESS → success
NOTPAY → pending
CLOSED → closed
PAYERROR → error
```

**Step 2: 代码实现**
```python
# AI生成的完整代码...
```

---

## 7️⃣ 质量检查清单

AI生成代码后，使用此清单验证：

```markdown
### 代码质量检查
- [ ] 所有函数都有文档字符串
- [ ] 异常处理完整
- [ ] 输入参数验证
- [ ] 日志记录
- [ ] 类型注解完整
- [ ] 遵循项目代码风格

### 功能完整性检查
- [ ] 所有必填参数都处理
- [ ] 所有错误码都有对应处理
- [ ] 业务逻辑完整
- [ ] 边界情况处理

### 安全性检查
- [ ] 敏感信息不记录日志
- [ ] 签名验证
- [ ] 防止SQL注入
- [ ] 输入数据清理

### 测试检查
- [ ] 正常流程测试通过
- [ ] 异常流程测试通过
- [ ] 边界值测试通过
```

---

## 8️⃣ 通用代码模板

### Service层模板

```python
class XXXService:
    """XXX服务"""

    @staticmethod
    async def create(data: dict) -> dict:
        """
        创建XXX

        Args:
            data: 创建数据

        Returns:
            创建结果

        Raises:
            ValueError: 参数验证失败
            Exception: 创建失败
        """
        try:
            # 1. 参数验证
            if not data.get("required_field"):
                raise ValueError("缺少必填字段")

            # 2. 业务逻辑
            result = await Model.create(**data)

            # 3. 返回结果
            return {
                "id": result.id,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"创建XXX失败: {str(e)}")
            raise

    @staticmethod
    async def query(id: int) -> dict:
        """查询XXX"""
        result = await Model.get_or_none(id=id)
        if not result:
            raise ValueError("数据不存在")
        return result.to_dict()
```

### API路由模板

```python
@router.post("/xxx", response_model=XXXResponse, summary="创建XXX")
async def create_xxx(request: XXXRequest):
    """创建XXX

    - **param1**: 参数说明
    - **param2**: 参数说明
    """
    try:
        # 调用服务层
        result = await XXXService.create(request.model_dump())
        return SuccessResponse(data=result, msg="操作成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建XXX异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="操作失败")
```

---

## 9️⃣ 最佳实践

### 1. 提供清晰的需求
- ✅ 好示例："实现微信Native支付，用户扫码后完成支付"
- ❌ 坏示例："做一个支付功能"

### 2. 提供完整的参考文档
- ✅ 包含完整的API文档链接或内容
- ✅ 说明认证方式和签名规则
- ✅ 提供错误码列表

### 3. 指定项目上下文
- ✅ 说明使用的技术栈
- ✅ 提供项目结构
- ✅ 提供参考的现有代码

### 4. 明确输出要求
- ✅ 要求按步骤执行：分析→设计→实现→测试
- ✅ 要求添加详细注释
- ✅ 要求遵循代码规范

---

## 🔟 常见使用场景

### 场景1: 集成第三方API
```
参考文档 → 提取API信息 → 设计接口 → 实现调用 → 处理响应
```

### 场景2: 开发新功能模块
```
需求描述 → 设计数据模型 → 实现Service → 实现API → 编写测试
```

### 场景3: 优化现有功能
```
现有代码分析 → 找出问题 → 设计优化方案 → 实现改进 → 验证效果
```

---

## 📞 使用流程

1. **复制模板** → 复制相关章节的模板
2. **填写内容** → 根据实际需求填写
3. **提交给AI** → 将完整内容发送给AI
4. **审查结果** → 检查AI的分析和代码
5. **迭代优化** → 根据结果反馈调整

---

## 🎓 进阶技巧

### 技巧1: 分阶段提交
不要一次性提交所有内容，分阶段让AI处理：
- 第1次：只提交需求描述，让AI分析
- 第2次：提供参考文档，让AI提取信息
- 第3次：要求AI设计数据结构
- 第4次：要求AI生成代码

### 技巧2: 提供示例代码
给AI看项目中的类似实现作为参考：
```
"请参考 base/plugins/wechat_pay/api/v1/wechat_pay.py 的代码风格"
```

### 技巧3: 明确约束条件
明确告诉AI的限制和要求：
```
"不要使用asyncio，使用Tortoise-ORM的异步语法"
"所有API必须使用SuccessResponse包装响应"
```

### 技巧4: 代码审查模式
让AI自我检查：
```
"生成代码后，请使用提供的质量检查清单自我审查"
```

---

**模板版本**: v1.0
**最后更新**: 2026-03-27
**适用范围**: FastAPI项目开发、API集成、功能模块开发
