# 跨境电商智能客服 - 从0到1实施指南

---

## 📌 阶段一：MVP 验证（1-2个月）

### 目标
只做亚马逊平台，3个核心功能，验证需求

### 第1周：搭建基础框架
1. ✅ 项目已有：FastAPI 后端 + Vue3 前端
2. ✅ 技能框架已有
3. 📝 完成：`amazon_order_query.py` - 订单查询技能
4. 📝 完成：`amazon_fee_query.py` - 费用查询技能
5. 📝 创建：工作流配置（见 `smart_customer_service_workflow.json`）

### 第2-3周：集成真实 API
```python
# 在 amazon_order_query.py 中替换 _mock_query_from_api
def _real_query_from_api(...)
    # 使用 amazon sp-api 或第三方 SDK
    # 推荐第三方库：
    # - python-amazon-sp-api
    # - amz-sp-api
```

### 第4周：找客户验证
- 🎯 深圳找3家做亚马逊的卖家（去龙华/坂田电商园）
- 🎯 免费试用1个月，收集反馈

---

## 📌 阶段二：产品化（2-4个月）

### 支持平台（优先级）
| 平台 | API | 优先级 |
|------|-----|--------|
| 亚马逊 | SP-API | P0 |
| 速卖通 | OpenAPI | P1 |
| Shopify | GraphQL API | P1 |
| TikTok Shop | OpenAPI | P1 |
| eBay | Trading API | P2 |
| Wish | Merchant API | P2 |
| 独立站/WooCommerce | REST API | P2 |

### 功能扩展
- 物流查询
- 退款处理
- 产品信息查询
- 库存查询
- 评论分析

---

## 📌 具体 Skill 开发规范

### 平台适配器模式
```
base/plugins/agent/skills/
├── base.py                  # 基类
├── registry.py              # 注册器
├── amazon/                  # 亚马逊平台
│   ├── order_query.py
│   ├── fee_query.py
│   ├── tracking.py
│   └── refund.py
├── aliexpress/              # 速卖通
│   ├── order_query.py
│   └── ...
└── shopify/                 # Shopify
    └── ...
```

### 每个平台 Skill 的接口统一
```python
class PlatformOrderQuerySkill(BaseSkill):
    @staticmethod
    def execute(params: dict) -> dict:
        """
        params 必须包含:
            - platform: 平台标识
            - seller_id: 卖家ID/店铺ID
            - credentials: API密钥等配置
            
        返回格式统一:
            {
                "success": True/False,
                "result": [...],
                "message": "..."
            }
        """
```

---

## 📌 商业化路径（深圳特色）

### 获客渠道
1. **深圳跨境电商协会** - 精准客户
2. **坂田/龙华/华南城电商园** - 地推
3. **亿恩网/雨果网** - 行业媒体
4. **抖音/视频号** - 内容获客

### 定价方案
- 免费版：1个平台，100次/月
- 基础版：¥299/月 - 3个平台，无限次
- 专业版：¥999/月 - 全平台 + 数据分析
- 企业版：定制

### 融资路径
- 种子轮：深圳天使投资人，50-100万
- Pre-A：深创投/达晨，500-1000万

---

## 📌 下一步行动清单

### 本周要做
- [ ] 完善 `amazon_order_query.py` 真实 API 集成
- [ ] 把 skill 注册到 registry
- [ ] 测试完整流程（用 Mock 数据）
- [ ] 找1家深圳亚马逊卖家做访谈

### 本月要做
- [ ] 完成亚马逊全功能 MVP
- [ ] 3家客户试用
- [ ] 注册公司，准备资质
- [ ] 写商业计划书

---

## 📌 深圳可用资源

### 技术资源
- **深圳Python社区** - 找人交流
- **开源中国深圳** - 技术活动

### 创业资源
- **前海深港青年梦工场** - 场地+政策
- **南山智园** - 孵化器
- **深圳天使荟** - 投资人对接

### 产业资源
- **深圳跨境电商协会** - 客户资源
- **坂田跨境电商产业园** - 产业集聚

---

## 📌 技术栈补充

### 亚马逊 SP-API Python SDK
```bash
pip install python-amazon-sp-api
# 或
pip install amz-sp-api
```

### 配置管理
把各平台 API 密钥存到数据库，通过 Seller ID 关联

### RAG 知识库
上传店铺常见问题、物流说明，让客服回答更专业

---

## 🎯 快速开始

1. 启动项目后端
2. 前端访问智能体管理
3. 创建智能体，导入工作流配置
4. 测试对话
5. 替换 Mock 数据为真实 API

