# 资源授权管理 · 后台 UI 技术方案（承接 §6.1）

> 溯源：[resource-grant-admin-prd.md](../RequirementsAnalysis/resource-grant-admin-prd.md)；核心承接 §6.1「判定侧新增 org 维度」结构性裁定。
> 本文是技术实现方案（数据模型 / 后端 / 前端 / 风险），与 PRD 的产品行为定义分离。
> 状态：已落地（状态于 2026-11-03 按实际开发/交付进度回写）。

---

## 1. 改动地图总览

| 层 | 改动 | 性质 |
|---|---|---|
| 数据模型 | `ResourceGrant.owner_type` 支持 `org` 取值 | **零迁移**（字段 `max_length=3` 恰好容纳 `"org"`） |
| 后端 · 判定 | `check_resource_access` 扩展组织维度解析 | **核心**（§6.1 唯一触及判定逻辑的改动） |
| 后端 · API | 补齐组织列表 / 按主体反查 / 批量授权 3 个缺口；`owner_type` 校验放行 `org` | 增量 |
| 前端 | 新增「资源授权」菜单 + 列表页 + 新建授权表单 + 撤销确认 | 新页面 |

---

## 2. 数据模型层：org 维度支持

`ResourceGrant.owner_type` 为 `CharField(max_length=3)`，`"org"` 恰为 3 字符，**无需 alter 字段、无需数据迁移**。

| 取值 | 含义 | `owner_id` 指向 |
|---|---|---|
| `cus` | 单个 customer | `customer.id` |
| `usr` | 后台用户 | `user.id` |
| `org`（新增） | customer 组织 | `customer_organization.id` |

组织授权记录与普通记录同表、同四元组唯一约束 `(owner_type, owner_id, resource_type, resource_id)`——同一组织对同一资源仅一条有效记录，天然幂等。

**兼容确认**：存量数据 `owner_type ∈ {cus, usr}`，新增 `org` 不影响存量；`resource_id` 为字符串，组织 ID 数值转字符串无冲突。

---

## 3. 后端改动

### 3.1 判定扩展（核心）—— `check_resource_access` 支持 org

现状 [service.py](file:///d:/programs/fastapi/aipaneladmin/base/common/authz/service.py#L44)：`filter(owner_type, owner_id, resource_type, resource_id)` 仅查主体自身。

**改造**：当 `owner_type == "cus"` 时，除查 customer 自身授权外，追加查其**所属组织**的授权。

```python
# 伪代码（ResourceGrantService.check_resource_access 内）
async def check_resource_access(owner, resource_type, resource_id):
    owner_type, owner_id = _split_owner(owner)
    # 0. §6.3：主体有效性校验（cus→Customer.is_active；usr→User.is_active；org→org.status=="active"）
    if not await _subject_active(owner_type, owner_id):
        return False
    # 1. 主体自身授权（现有逻辑不变）
    if await _has_valid_grant(owner_type, owner_id, resource_type, resource_id):
        return True
    # 2. §6.1：customer 追加组织维度
    if owner_type == "cus":
        org_ids = await _customer_org_ids(owner_id)          # CustomerOrganizationMember 解析
        if org_ids and await _has_valid_grant("org", org_ids, resource_type, resource_id):
            return True
    return False
```

- `_customer_org_ids(customer_id)`：`CustomerOrganizationMember.filter(customer_id=..., status="active").values_list("org_id", flat=True)`（字段名以模型为准：FK 为 `org_id`/`customer_id`，状态字段为 `status`，**无 is_active 字段**）。
- `_has_valid_grant` 支持单 id 或 id 列表（`owner_id__in=org_ids`），复用 `_is_valid_grant` 过期校验。
- **主体有效性校验（§6.3）** 在判定层实现：已禁用/删除主体不放行，恢复后自动恢复。**资源有效性（§6.2）不在 check 热路径校验**——用户侧清单已过滤已删除资源（u_resource_router meta 缺失即跳过），运行时资源不存在业务自然失败；"资源已删除"标注由管理端列表 API enrich 实现。
- `usr` 主体不走组织维度（组织是 customer 域概念）。

**性能风险与对策**：每次 `check` 多一次组织关系查询。对策：
- `_customer_org_ids` 结果按 `customer_id` 短 TTL 缓存（Redis，键 `authz:org_ids:{customer_id}`；按 BUG-OPS-001 修复后的用法：先 `get_instance()` 再判 `is_enabled()`）；
- 组织成员变动时失效对应缓存键：`CustomerOrganizationService.add_member`（含 removed→active 复活）、`remove_member`、`create_organization` 三处挂钩（`update_member_role` 不改成员集合，无需失效）。

### 3.2 授权 API 增强（`admin_grant_router.py` 增量）

> 路径订正（节点1 核查）：该路由挂在 agent 插件下，实际前缀为 **`/v1/agent/admin/grants`**（agent 插件 route_prefix=`/v1/agent` + router prefix=`/admin/grants`）。

| 改动 | 说明 |
|---|---|
| `owner_type` 校验放行 `org` | 新增 `OWNER_TYPES = ("cus","usr","org")` 显式校验，非法值报错；`OwnerType` 枚举同步新增 `ORG = "org"`（constants.py，纯代码无迁移） |
| **新增** `GET /admin/grants/by-subject` | 按主体反查（`owner_type`+`owner_id`），支撑 FR-07 按主体筛选的列表数据源 |
| **新增** `GET /admin/grants/list` | 管理端授权记录列表（分页 + resource_type/owner_type/status/keyword 筛选 + 按授权时间倒序），enrich 主体显示名与"资源已删除"标注（§6.2）；FR-02/FR-07 数据源 |
| **新增** `POST /admin/grants/batch` | 单资源 + 多主体批量发放（PRD FR-03）。入参 `{resource_type, resource_id, subjects:[{owner_type,owner_id}], expires_at}`；**逐条独立**（§6.4）：循环调 `grant()`，收集每条成功/失败，返回 `{succeeded:[], failed:[{subject,reason}]}`，不整体回滚 |
| 审计 | 复用现有 ORM 自动捕获，无需额外处理 |

### 3.3 数据源 API（节点选择器）—— 聚合到 grants 域（节点1 裁定 Q1）

**裁定**：项目无全局 `/v1/admin` 挂载点，且 `/v1/customer/list` 认证依赖被注释存在安全债务；故数据源端点统一聚合在 admin/grants 域内，全部 `require_superuser`，直接查模型，不复用异构业务列表 API。

| 端点 | 说明 |
|---|---|
| **新增** `GET /admin/grants/subjects?type=cus\|org\|usr&keyword=&page=&page_size=` | 主体选择器统一数据源：cus→Customer（email/username 模糊，is_active=True）；org→CustomerOrganization（name 模糊，status="active"）；usr→User（username/email 模糊，is_active=True）。返回 `{items:[{id, label, extra}], total}` |
| **新增** `GET /admin/grants/resource-options?type=model\|kb\|tool\|agent\|node_type&keyword=` | 资源选择器统一数据源，复用 `u_resource_router._load_metadata` 的分类型查询模式（model→LLMModel status=active；kb→RAGKnowledgeBase；tool→Tool；agent→Agent status=active；node_type→静态编码 hitl/sub_agent/tool）。返回 `{items:[{id, label, extra}]}`，extra 带状态标注（FR-05） |

> 既有债务记录（本期不修）：`/v1/customer/list` 认证依赖被注释（"暂时注释，用于调试"），未认证可调，建议另开任务修复。

---

## 4. 前端改动（web 管理后台，Vue3 + Element Plus）

### 4.1 菜单与路由

- **菜单为后端驱动**：`/v1/menus/user-menus` → menuStore 动态生成路由（component 映射 `@/views/**`）。新增「资源授权」需在**菜单表注册一条记录**（path=/panel/grant，component=grant/Index，icon=Key，归属权限管理分组）。superuser 自动获得全部菜单；不授权给任何角色即天然仅 superuser 可见（FR-01）。
- **路由**：无需在 `web/src/router/index.js` 静态注册——菜单记录的 path/component 由 menuStore 动态生成路由（component=`grant/Index` → `@/views/grant/Index.vue`）。
- **权限守卫**：页面内校验 `userStore.isSuperuser`（[stores/user.js:13](file:///d:/programs/fastapi/aipaneladmin/web/src/stores/user.js#L13)），非 superuser 直接访问 URL 时展示无权限提示；菜单层面对非 superuser 天然不渲染。

### 4.2 页面组件

```
web/src/views/grant/
├── Index.vue                  # 授权列表页（FR-02/07）：筛选区 + 表格 + 撤销
├── GrantCreateDialog.vue      # 新建授权弹窗（FR-03）：资源选择 + 主体多选 + 过期时间
└── components/
    ├── ResourceSelect.vue     # 资源级联选择器（FR-05）：类型下拉 → 资源搜索单选
    └── SubjectSelect.vue      # 主体级联选择器（FR-06）：类型单选 → 主体搜索多选
```

`web/src/api/grant.js`：封装 `listGrants / createGrantBatch / revokeGrant / listOrganizations` 等。

### 4.3 关键交互落点

| PRD 落点 | 前端实现 |
|---|---|
| FR-03 幂等反馈 | 批量接口返回 succeeded/failed，前端 ElMessage 分色提示"新增 N / 刷新 M / 失败 K" |
| FR-04 撤销二次确认 | ElMessageBox.confirm 展示"将对【主体】回收【资源】权限"，确认后调 `DELETE /admin/grants` |
| FR-02 状态列 | `expires_at` 为空→"长期有效"；过期→红色"已过期"标签；资源已删除→灰色标注 |
| FR-06 组织语义 | 组织选项 tooltip 标注"全体成员获得授权，成员变动自动生效"（§6.1） |

---

## 5. 关键技术风险与对策

| 风险 | 对策 |
|---|---|
| org 判定增加查询开销 | 组织关系按 customer 短 TTL 缓存；成员变动主动失效 |
| 组织成员变动一致性 | 判定侧实时解析（§6.1 裁定），无需同步授权记录；缓存失效保证新鲜度 |
| 批量授权部分失败 | 服务端逐条独立 + 明细返回（§6.4）；失败项可安全重试（幂等） |
| owner_type=org 与存量混用 | 字段长度兼容，判定逻辑对 org/cus/usr 分支清晰，无隐式放行 |
| 资源列表 API 逐类型对齐 | 五类资源各有管理列表接口，前端资源选择器按类型映射；逐一确认路径与字段 |

---

## 6. 改动清单（文件级）

| 层 | 文件 | 动作 |
|---|---|---|
| 后端判定 | `base/common/authz/service.py` | 改 `check_resource_access`/`check_many` 增 org 分支 + §6.3 主体有效性校验 + org_ids 缓存 |
| 后端常量 | `base/common/authz/constants.py` | `OwnerType` 新增 `ORG = "org"`（纯代码，无迁移） |
| 后端 API | `base/plugins/agent/api/v1/admin_grant_router.py` | owner_type 校验；新增 list / by-subject / batch / subjects / resource-options |
| 后端服务 | `base/plugins/customer/services/organization_service.py` | add_member/remove_member/create_organization 三处缓存失效挂钩 |
| 前端 | `web/src/views/grant/*` + `web/src/api/grant.js` | 新增页面与封装 |
| 数据 | 菜单表插入「资源授权」记录 | 一次性数据（组件路径 grant/Index） |

---

## 7. 节点1 裁定记录

| # | 问题 | 裁定 |
|---|---|---|
| Q1 | 数据源 API 挂载 | 聚合到 `/v1/agent/admin/grants` 域（subjects / resource-options 两端点），不复用异构业务列表 API |
| Q2 | P1 范围 | 按资源/主体反查用 FR-07 列表筛选等价实现，不做独立 Tab；审计查看复用既有审计日志页面，本期不新建 |
| R3 | §6.2 落点 | 资源存在性不进 check 热路径；管理端列表 enrich"资源已删除"标注 |
| R2 | 既有债务 | `/v1/customer/list` 无鉴权问题本期记录不修，建议另开任务 |

> 全部开放项已裁定；状态于 2026-11-03 按实际开发/交付进度回写：后端判定/API 与前端页面均已交付（见第 6 节改动清单），技术方案已落地。
