# AIPanelAdmin - FastAPI 后台管理系统

一个基于 FastAPI + Tortoise ORM + PostgreSQL 构建的现代化后台管理系统。

## 功能特性

### 已实现功能

#### 1. 用户认证系统
- JWT Token 认证
- 用户注册和登录
- 密码加密存储(Bcrypt)
- Token 刷新机制
- 用户信息管理

#### 2. 用户管理(CRUD)
- 用户列表(分页、搜索、筛选)
- 创建用户(管理员)
- 更新用户信息
- 删除用户(管理员)
- 用户状态切换(激活/禁用)
- 修改密码

#### 3. 角色权限管理(RBAC)
- 角色管理(增删改查)
- 权限管理(增删改查)
- 为角色分配权限
- 为用户分配角色
- 查询用户权限

#### 4. 部门管理
- 部门树形结构
- 部门增删改查
- 部门层级管理

#### 5. 菜单管理
- 菜单树形结构
- 菜单增删改查
- 菜单类型(目录/菜单/按钮)
- 基于用户权限的菜单显示

#### 6. 操作日志
- 自动记录用户操作
- 日志查询和筛选
- 日志清理功能

### 技术栈

- **Web框架**: FastAPI 0.111.0
- **ORM**: Tortoise ORM 0.23.0
- **数据库**: PostgreSQL
- **认证**: JWT (python-jose)
- **密码加密**: Passlib + Bcrypt
- **服务器**: Uvicorn
- **数据迁移**: Aerich

## 项目结构

```
aipaneladmin/
├── base/                          # 核心业务代码
│   ├── cli/                       # 命令行工具
│   ├── common/                    # 公共模块
│   │   ├── config.py              # 配置加载
│   │   ├── constant.py            # 常量定义
│   │   ├── database.py            # 数据库初始化
│   │   ├── exceptions.py          # 异常处理
│   │   ├── log.py                 # 日志配置
│   │   ├── middleware.py          # 中间件自动注册
│   │   ├── model.py               # 基础模型
│   │   ├── response.py            # 统一响应
│   │   ├── router.py              # 路由自动注册
│   │   ├── security.py            # 安全工具(JWT/密码加密)
│   │   └── setting.py             # 配置管理
│   ├── core/                      # 核心业务模块
│   │   ├── users/                 # 用户模块
│   │   │   ├── api/v1/            # API接口
│   │   │   │   ├── auth.py        # 认证接口
│   │   │   │   ├── users.py       # 用户管理接口
│   │   │   │   ├── rbac.py        # 角色权限接口
│   │   │   │   ├── menu.py        # 菜单管理接口
│   │   │   │   └── operation_log.py # 操作日志接口
│   │   │   ├── models/            # 数据模型
│   │   │   │   ├── users.py       # 用户模型
│   │   │   │   ├── rbac.py        # 角色权限模型
│   │   │   │   └── operation_log.py # 操作日志模型
│   │   │   ├── schemas/           # Pydantic模型
│   │   │   │   ├── users.py       # 用户Schemas
│   │   │   │   ├── rbac.py        # 角色权限Schemas
│   │   │   │   └── operation_log.py # 日志Schemas
│   │   │   └── services/          # 业务逻辑层
│   │   │       ├── user_service.py # 用户服务
│   │   │       ├── rbac_service.py # 角色权限服务
│   │   │       ├── menu_service.py # 菜单服务
│   │   │       └── operation_log_service.py # 日志服务
│   │   └── dept/                  # 部门模块
│   │       ├── api/v1/
│   │       │   └── department.py  # 部门接口
│   │       ├── models/
│   │       │   └── department.py  # 部门模型
│   │       ├── schemas/
│   │       │   └── department.py  # 部门Schemas
│   │       └── services/
│   │           └── department_service.py # 部门服务
│   ├── test/                      # 测试模块
│   │   ├── __init__.py            # 测试包初始化
│   │   ├── conftest.py            # pytest配置
│   │   ├── test_auth.py           # 认证测试
│   │   ├── test_utils.py          # 工具测试
│   │   ├── test_api.py            # API测试
│   │   └── README.md              # 测试文档
│   └── start.py                   # 应用启动文件
├── migrations/                    # 数据库迁移文件
├── logs/                          # 日志目录
├── config.conf                    # 配置文件
├── init_db.py                     # 数据库初始化快捷入口
├── run_tests.py                   # 测试运行快捷入口
├── requirements.txt               # 依赖文件
└── run.py                         # 应用启动入口
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- PostgreSQL 12+

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置数据库

编辑 `config.conf` 文件:

```ini
[app]
name = AIPanelAdmin
version = v0.1.0
description = AIPanelAdmin API Documentation
debug = true

[db]
db_host = 127.0.0.1
db_name = aipaneladmin
db_user = postgres
db_password = 123456
db_port = 5432

[log]
path = D:\Programs\fastapi\aipaneladmin\logs
```

### 4. 创建数据库

```sql
CREATE DATABASE aipaneladmin;
```

### 5. 运行项目

```bash
python run.py
```

服务将在 `http://0.0.0.0:9999` 启动

### 6. 访问API文档

- Swagger UI: http://localhost:9999/docs
- ReDoc: http://localhost:9999/redoc

### 7. 创建初始管理员账户

首次运行后,使用注册接口创建管理员账户:

```bash
POST /api/v1/auth/register
{
  "username": "admin",
  "password": "admin123",
  "email": "admin@example.com",
  "alias": "系统管理员"
}
```

然后手动将该用户设置为超级管理员(在数据库中设置 `is_superuser=true`)

## API 接口说明

### 认证相关
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `GET /api/v1/auth/me` - 获取当前用户信息
- `POST /api/v1/auth/change-password` - 修改密码
- `POST /api/v1/auth/logout` - 用户登出

### 用户管理
- `GET /api/v1/users/list` - 获取用户列表(分页)
- `GET /api/v1/users/{user_id}` - 获取用户详情
- `POST /api/v1/users` - 创建用户(管理员)
- `PUT /api/v1/users/{user_id}` - 更新用户
- `DELETE /api/v1/users/{user_id}` - 删除用户(管理员)
- `PATCH /api/v1/users/{user_id}/toggle-status` - 切换用户状态

### 角色权限管理
- `GET /api/v1/rbac/roles/list` - 获取角色列表
- `GET /api/v1/rbac/roles/{role_id}` - 获取角色详情
- `POST /api/v1/rbac/roles` - 创建角色
- `PUT /api/v1/rbac/roles/{role_id}` - 更新角色
- `DELETE /api/v1/rbac/roles/{role_id}` - 删除角色
- `POST /api/v1/rbac/roles/{role_id}/permissions` - 为角色分配权限
- `GET /api/v1/rbac/permissions/list` - 获取权限列表
- `GET /api/v1/rbac/permissions/all` - 获取所有权限
- `POST /api/v1/rbac/permissions` - 创建权限
- `PUT /api/v1/rbac/permissions/{permission_id}` - 更新权限
- `DELETE /api/v1/rbac/permissions/{permission_id}` - 删除权限
- `POST /api/v1/rbac/users/{user_id}/roles` - 为用户分配角色
- `GET /api/v1/rbac/users/{user_id}/roles` - 获取用户角色
- `GET /api/v1/rbac/users/{user_id}/permissions` - 获取用户权限

### 部门管理
- `GET /api/v1/departments/list` - 获取部门列表(分页)
- `GET /api/v1/departments/tree` - 获取部门树
- `GET /api/v1/departments/{dept_id}` - 获取部门详情
- `POST /api/v1/departments` - 创建部门
- `PUT /api/v1/departments/{dept_id}` - 更新部门
- `DELETE /api/v1/departments/{dept_id}` - 删除部门

### 菜单管理
- `GET /api/v1/menus/tree` - 获取菜单树
- `GET /api/v1/menus/user-menus` - 获取当前用户菜单
- `GET /api/v1/menus/{menu_id}` - 获取菜单详情
- `POST /api/v1/menus` - 创建菜单
- `PUT /api/v1/menus/{menu_id}` - 更新菜单
- `DELETE /api/v1/menus/{menu_id}` - 删除菜单

### 操作日志
- `GET /api/v1/logs/list` - 获取操作日志列表
- `DELETE /api/v1/logs/cleanup` - 清理旧日志

## 核心特性说明

### 1. 自动路由注册

项目实现了路由自动发现和注册机制,只需在指定目录创建路由文件并定义 `router` 变量,系统会自动注册。

参考: [base/common/router.py](base/common/router.py:111)

### 2. 自动中间件注册

支持中间件自动发现,在各模块的 `middleware` 目录下创建中间件文件即可自动注册。

参考: [base/common/middleware.py](base/common/middleware.py:205)

### 3. 自动模型加载

数据库模型会自动从 `core` 和 `plugins` 目录加载,无需手动配置。

参考: [base/common/setting.py](base/common/setting.py:9)

### 4. 统一响应格式

所有API响应遵循统一格式:

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {},
  "success": true,
  "status_code": 200
}
```

参考: [base/common/response.py](base/common/response.py)

### 5. JWT认证

使用JWT Token进行用户认证,Token有效期24小时。

参考: [base/common/security.py](base/common/security.py)

## 数据库迁移

项目使用 Aerich 进行数据库迁移管理。

```bash
# 初始化(首次使用)
aerich init -t base.common.setting.settings.TORTOISE_ORM

# 创建迁移
aerich migrate

# 应用迁移
aerich upgrade

# 回滚
aerich downgrade
```

## 开发指南

### 添加新模块

1. 在 `base/core/` 或 `base/plugins/` 下创建新模块目录
2. 按照以下结构组织代码:
   ```
   your_module/
   ├── api/v1/          # API接口
   ├── models/          # 数据模型
   ├── schemas/         # Pydantic模型
   └── services/        # 业务逻辑
   ```
3. 系统会自动注册路由和模型

### 添加API接口

```python
from fastapi import APIRouter, Depends
from base.common.security import get_current_user_id
from base.common.response import SuccessResponse

router = APIRouter(prefix="/api/v1/your_module", tags=["模块名"])

@router.get("/test")
async def test_api(current_user_id: int = Depends(get_current_user_id)):
    return SuccessResponse(data={"message": "Hello"})
```

## 安全建议

1. **修改JWT密钥**: 在 [base/common/security.py](base/common/security.py) 中修改 `SECRET_KEY`,建议使用环境变量
2. **修改数据库密码**: 生产环境使用强密码
3. **HTTPS**: 生产环境使用HTTPS
4. **CORS配置**: 根据实际需求配置允许的域名

## License

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request!
