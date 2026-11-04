# AIPanelAdmin

基于 FastAPI + Tortoise ORM 的插件化业务后台，并在此之上承载一套面向 C 端的**用户侧智能体工作流平台**（搭画布 → 试跑 → 发布 → 配额使用）。

- 后端：FastAPI、Tortoise ORM、PostgreSQL（兼容 openGauss）、Redis、Qdrant
- 前端：三套独立工程（管理后台 `web/`、用户侧站点 `web-user/`、共享校验器 `web-shared/`）
- 主线需求与架构基线见 [《用户侧智能体设计流PRD.md》](docs/用户侧智能体设计流PRD.md) 与 [docs/arch](docs/arch)

## 1. 项目定位与双主线

| 主线 | 内容 | 主要落点 |
|---|---|---|
| A. 插件化业务后台 | 用户 / RBAC / 部门 / 菜单 / 操作日志等基础能力，以及 MES、MRP2、采购、库存、销售、质量、财务等 22 个可启停插件 | `base/core/`、`base/plugins/`、`web/` |
| B. 用户侧智能体平台 | 工作流画布编辑与校验、节点试跑（SSE trace）、发布/版本/回滚、配额计量、身份关联、资源授权 | `base/common/authz`、`base/common/quota`、`base/common/events`、`base/plugins/agent`、`base/plugins/customer`、`base/plugins/llm`、`web-user/`、`web-shared/` |

后台菜单由插件清单驱动，插件可安装/启用/禁用；用户侧站点使用独立的登录态存储（`u_token` / `u_customer`），避免与后台会话冲突。

## 2. 技术栈（以锁定版本为准）

版本号来自 [requirements.txt](requirements.txt)：FastAPI `0.141.1`、Tortoise ORM `0.23.0`、Pydantic `2.11.7`、Uvicorn `0.34.2`；数据库驱动为 asyncpg，缓存/并发槽为 Redis，向量检索为 Qdrant，认证为 JWT（python-jose），密码为 Passlib + Bcrypt。

前端为 Vue 3 + Vite + Pinia + Element Plus，画布使用 VueFlow。

## 3. 后端结构

```
base/
├── app_wrapper.py          # 统一挂载 /api 前缀、安装引导与 SPA 静态资源
├── start.py                # 启动生命周期：数据库、插件、事件处理器、定时任务
├── common/
│   ├── config.py / setting.py / database.py   # 配置与 Tortoise 初始化
│   ├── router.py / middleware.py              # 路由与中间件自动发现
│   ├── response.py / security.py              # 统一响应、JWT/密码
│   ├── plugin_manager.py                      # 插件发现、启停、路由/模型/菜单注册
│   ├── authz/                                 # 归属鉴权 + ResourceGrant 资源授权
│   ├── quota/                                 # 配额预占/结算（Redis 原子操作，故障降级）
│   └── events/                                # 事件总线与审计等公共事件
├── core/                   # users / dept / install / extension
└── plugins/                # 22 个约定式插件，每个含 manifest.json
```

### 自动注册机制

- **核心路由**：启动时扫描 `base.core`，凡模块内定义 `router` 即自动注册（[base/common/router.py](base/common/router.py)）。
- **插件路由/模型/菜单**：读取 `base/plugins/<name>/manifest.json`，由 `plugin_manager` 按启用状态注册路由；所有已发现插件的模型在启动时统一注册，避免运行时热加载模型失败（[base/common/setting.py](base/common/setting.py)、[base/common/plugin_manager.py](base/common/plugin_manager.py)）。
- **中间件**：自动扫描 `base.common`、`base.core`、`base.plugins`（[base/common/middleware.py](base/common/middleware.py)）。
- **对外路径**：`app_wrapper` 统一加 `/api` 前缀，因此插件 `route_prefix` 写 `/v1/xxx`，实际访问为 `/api/v1/xxx`；例如资源授权 API 为 `/api/v1/agent/admin/grants`。

### 数据库迁移

迁移文件统一放在 [migrations](migrations)（当前 27 个 SQL），命名形如 `{plugin}_{action}_{table}[__{field}]_{unix_timestamp}.sql`，按时间戳升序执行；文件只在对应插件启用时执行。

```bash
python -m base.common.migration_tool gen <plugin> <action> <table> [field]
python -m base.common.migration_tool list
python -m base.common.migration_tool validate
```

## 4. 三套前端

| 工程 | 职责 | 开发 / 构建 |
|---|---|---|
| [web/](web) | 管理后台：系统管理、插件管理、业务模块、资源授权管理 | `npm install && npm run dev`（端口 3000，`/api` 代理到 9998）；`npm run build` 产物 `web/dist` 由后端在 `/panel` 提供 |
| [web-user/](web-user) | 用户侧站点：工作流列表/画布/试跑/发布、知识库、执行记录、配额看板、身份关联 | `npm run dev`（端口 3100，`/api` 代理到 9998）；生产由 `deploy/nginx/Dockerfile` 构建并托管在 8081 |
| [web-shared/](web-shared) | 前后端共享的图校验器与 v1→v2 转换器 | 源码直引，无独立构建；`web-user` 通过 `@validator` 别名引用 `schema-validator` |

资源授权管理后台位于 [web/src/views/grant/](web/src/views/grant/)，对应后端 `base/plugins/agent/api/v1/admin_grant_router.py`；`base/common/authz/service.py` 已支持 `customer` / `usr` / `org` 三类主体判定，并使用短 TTL 的 `authz:org_ids` 缓存。

## 5. 本地运行

### 环境要求

- Python 3.x 与本机虚拟环境（容器镜像基于 `python:3.12-slim`，见 [deploy/app/Dockerfile](deploy/app/Dockerfile)）
- PostgreSQL（或 openGauss）
- 可选：Redis（用户侧并发槽与配额）、Qdrant（知识库向量检索）

### 步骤

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

1. 编辑 [config.conf](config.conf)：`[app]`、`[db]`、`[storage]`、`[log]`，按需配置 `[redis]`。
2. 创建数据库（名称与 `config.conf` 的 `db_name` 一致）。
3. 启动：

```bash
python run.py
```

默认端口 `9998`（可用 `UVICORN_PORT` 覆盖）。首次访问会进入 `/install` 安装向导，完成数据库连接校验与管理员创建。

### 访问地址

- 后端接口文档：`http://127.0.0.1:9998/docs`
- 管理后台（需先构建 `web/dist`）：`http://127.0.0.1:9998/panel`
- 管理后台开发态：`http://127.0.0.1:3000`
- 用户侧开发态：`http://127.0.0.1:3100`

## 6. 部署入口

一键编排位于 [deploy/app/docker-compose.yml](deploy/app/docker-compose.yml)（app + redis + nginx）：

```bash
cd deploy/app
cp .env.example .env                                   # 填写 DB/Redis/密钥
cp config.docker.conf config.conf                      # 按实际环境调整
docker compose --env-file .env up -d --build
```

- 管理后台：`http://<host>:8080`（`/panel` 由后端 `app_wrapper` 提供，`/` 与 `/api` 转发 app）
- 用户侧站点：`http://<host>:8081`（nginx 直接托管 `web-user` 构建产物，`/api` 转发 app）
- 站点配置见 [deploy/nginx/conf.d](deploy/nginx/conf.d)

上线三条硬约束（详见 [docs/ops/go-live-checklist.md](docs/ops/go-live-checklist.md) 与 [docs/ops/grayscale-monitoring-checklist.md](docs/ops/grayscale-monitoring-checklist.md)）：

| 编号 | 约束 | 落实方式 |
|---|---|---|
| H-1 | 单 worker | compose 固定 `UVICORN_WORKERS=1`；`run.py` 启动自检，生产环境违规且 `STRICT_STARTUP=true` 时拒绝启动 |
| H-2 | 必须启用 Redis | compose 随编排启动 Redis 并设 `redis.enabled=true`；`run.py` 预检可达性 |
| H-3 | 网关超时 ≥30s | nginx 对 SSE 路径 `proxy_buffering off`、`proxy_read_timeout 3600s` |

openGauss 环境的独立编排见 [deploy/openguass/docker-compose.yml](deploy/openguass/docker-compose.yml)。

## 7. 文档索引

| 类别 | 文档 |
|---|---|
| 主线 PRD | [docs/用户侧智能体设计流PRD.md](docs/用户侧智能体设计流PRD.md) |
| 架构基线 | [01-需求与约束](docs/arch/01-需求与约束.md) · [02-系统上下文与领域模型](docs/arch/02-系统上下文与领域模型.md) · [03-技术选型与存储方案](docs/arch/03-技术选型与存储方案.md) · [04-核心流程与接口契约](docs/arch/04-核心流程与接口契约.md) · [05-可靠性与安全可观测](docs/arch/05-可靠性与安全可观测.md) · [06-架构自检与开发基线](docs/arch/06-架构自检与开发基线.md) |
| 资源授权 | [PRD](docs/RequirementsAnalysis/resource-grant-admin-prd.md) · [后台 UI 技术方案](docs/arch/resource-grant-admin-tech.md) |
| 测试 | 主线节点测试指南 [Agent_Node_Test_Guide.md](docs/Tests/Agent_Node_Test_Guide.md)；主线脚本在 [tests/](tests)（`_t15_*.py`、`test_authz_m8.py`、`test_quota_m9.py`、`test_grant_admin.py`、`test_engine_m2.py`、`test_identity_m11.py` 等）；MES/化妆品业务历史测试已归档至 [tests/mes/](tests/mes) |
| 上线/运维 | [上线检查表](docs/ops/go-live-checklist.md) · [灰度监控清单](docs/ops/grayscale-monitoring-checklist.md) |

## 8. 当前交付状态

- 架构节点 01~06 均已确认，并作为 T1~T16 的开发基线；T15 端到端验收已闭环，上线检查表与灰度监控清单已就绪。
- 用户侧主线已具备：画布编辑与双端同构校验、节点试跑与 SSE trace、发布/版本快照/回滚、配额计量与看板、身份关联/恢复、执行记录。
- 资源授权管理后台已交付：后端 `list / by-subject / batch / subjects / resource-options` 等接口与 `org` 主体判定、前端授权列表/新建对话框/资源与主体选择器均已落地。
- 插件体系现有 22 个插件，数据库 SQL 迁移 27 个；openGauss 兼容与部署验证按架构节点 06 执行。

## 9. 开发指南

### 新增插件

在 `base/plugins/<name>/` 下提供 `manifest.json`（含 `name`、`display_name`、`route_prefix`、菜单/图标等），并按约定放置 `models/`、`api/v1/`、`services/`；路由变量名统一为 `router`。插件模型与路由由 `plugin_manager` 按安装/启用状态接管，无需手工注册。

### 新增核心模块 API

```python
from fastapi import APIRouter, Depends
from base.common.security import get_current_user_id
from base.common.response import SuccessResponse

router = APIRouter(prefix="/v1/your_module", tags=["模块名"])

@router.get("/test")
async def test_api(current_user_id: int = Depends(get_current_user_id)):
    return SuccessResponse(data={"message": "Hello"})
```

对外实际路径为 `/api/v1/your_module/test`。

### 统一响应与认证

成功响应格式（[base/common/response.py](base/common/response.py)）：

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {},
  "success": true,
  "status_code": 200
}
```

JWT 有效期 24 小时（[base/common/security.py](base/common/security.py)）。

## 10. 安全建议

1. 生产环境必须替换 [base/common/security.py](base/common/security.py) 中默认的 `SECRET_KEY`，建议通过环境变量注入。
2. 数据库、Redis、支付渠道密钥通过 `.env` / 挂载配置下发，不提交真实密钥。
3. 对外统一走 HTTPS，并按实际域名收敛 CORS。
4. 正式上线前逐项执行上线检查表与灰度监控清单。

## License

MIT License
