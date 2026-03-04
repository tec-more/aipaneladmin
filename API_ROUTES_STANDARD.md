# 前后端路由格式统一标准

## 总体原则

### API 路径格式
- **基础路径**: `/api/v1/{resource}`
- **完整路径**: `/api` (baseURL) + `/v1/{resource}` (路由前缀) + `/{action}` (具体操作)

### 命名规范
- 资源名称使用复数形式（如 `customers`, `products`, `orders`）
- 使用小写字母和连字符（kebab-case）
- 避免使用驼峰命名

## 统一路由格式

### 客户管理 (Customer)
| 前端调用 | 后端路由 | HTTP方法 | 说明 |
|---------|----------|----------|------|
| `/v1/customer/list` | `/list` | GET | 获取客户列表 |
| `/v1/customer/${id}` | `/{customer_id}` | GET | 获取客户详情 |
| `/v1/customer` | `` | POST | 创建客户 |
| `/v1/customer/${id}` | `/{customer_id}` | PUT | 更新客户 |
| `/v1/customer/${id}` | `/{customer_id}` | DELETE | 删除客户 |
| `/v1/customer/batch` | `/batch` | DELETE | 批量删除 |
| `/v1/customer/${id}/status` | `/{customer_id}/status` | PATCH | 切换状态 |
| `/v1/customer/${id}/points` | `/{customer_id}/points` | PATCH | 更新积分 |
| `/v1/customer/${id}/membership` | `/{customer_id}/membership` | PATCH | 更新会员 |
| `/v1/customer/membership-levels` | `/membership-levels` | GET | 会员等级列表 |
| `/v1/customer/usage` | `/usage` | GET | 使用记录 |

### 产品管理 (Product)
| 前端调用 | 后端路由 | HTTP方法 | 说明 |
|---------|----------|----------|------|
| `/v1/product/list` | `/list` | GET | 获取产品列表 |
| `/v1/product/${id}` | `/{product_id}` | GET | 获取产品详情 |
| `/v1/product` | `` | POST | 创建产品 |
| `/v1/product/${id}` | `/{product_id}` | PUT | 更新产品 |
| `/v1/product/${id}` | `/{product_id}` | DELETE | 删除产品 |
| `/v1/product/batch` | `/batch` | DELETE | 批量删除 |
| `/v1/product/${id}/toggle-status` | `/{product_id}/toggle-status` | PATCH | 切换状态 |
| `/v1/product/${id}/stock` | `/{product_id}/stock` | PATCH | 更新库存 |
| `/v1/product/categories/list` | `/categories/list` | GET | 分类列表 |

### 订单管理 (Order)
| 前端调用 | 后端路由 | HTTP方法 | 说明 |
|---------|----------|----------|------|
| `/v1/order/` | `/` | GET | 获取订单列表 |
| `/v1/order/list` | `/list` | GET | 获取订单列表(别名) |
| `/v1/order/${id}` | `/{order_id}` | GET | 获取订单详情 |
| `/v1/order/create` | `/create` | POST | 创建订单 |
| `/v1/order/${id}` | `/{order_id}` | PUT | 更新订单 |
| `/v1/order/${id}` | `/{order_id}` | DELETE | 删除订单 |
| `/v1/order/batch` | `/batch` | DELETE | 批量删除 |
| `/v1/order/${id}/status` | `/{order_id}/status` | PATCH | 更新订单状态 |
| `/v1/order/${id}/payment-status` | `/{order_id}/payment-status` | PATCH | 更新支付状态 |

### 用户管理 (User)
| 前端调用 | 后端路由 | HTTP方法 | 说明 |
|---------|----------|----------|------|
| `/v1/users/list` | `/list` | GET | 获取用户列表 |
| `/v1/users/${id}` | `/{user_id}` | GET | 获取用户详情 |
| `/v1/users` | `` | POST | 创建用户 |
| `/v1/users/${id}` | `/{user_id}` | PUT | 更新用户 |
| `/v1/users/${id}` | `/{user_id}` | DELETE | 删除用户 |
| `/v1/users/${id}/toggle-status` | `/{user_id}/toggle-status` | PATCH | 切换状态 |

### 部门管理 (Department)
| 前端调用 | 后端路由 | HTTP方法 | 说明 |
|---------|----------|----------|------|
| `/v1/departments/list` | `/list` | GET | 获取部门列表 |
| `/v1/departments/tree` | `/tree` | GET | 获取部门树 |
| `/v1/departments/${id}` | `/{dept_id}` | GET | 获取部门详情 |
| `/v1/departments` | `` | POST | 创建部门 |
| `/v1/departments/${id}` | `/{dept_id}` | PUT | 更新部门 |
| `/v1/departments/${id}` | `/{dept_id}` | DELETE | 删除部门 |

### RBAC 权限管理
| 前端调用 | 后端路由 | HTTP方法 | 说明 |
|---------|----------|----------|------|
| `/v1/rbac/roles/list` | `/list` | GET | 获取角色列表 |
| `/v1/rbac/roles/${id}` | `/{role_id}` | GET | 获取角色详情 |
| `/v1/rbac/roles` | `` | POST | 创建角色 |
| `/v1/rbac/roles/${id}` | `/{role_id}` | PUT | 更新角色 |
| `/v1/rbac/roles/${id}` | `/{role_id}` | DELETE | 删除角色 |
| `/v1/rbac/permissions/list` | `/list` | GET | 获取权限列表 |
| `/v1/menus/tree` | `/tree` | GET | 获取菜单树 |

## HTTP 方法使用规范

| 方法 | 使用场景 | 示例 |
|------|----------|------|
| GET | 查询资源 | `GET /v1/product/list` |
| POST | 创建资源 | `POST /v1/product` |
| PUT | 完整更新资源 | `PUT /v1/product/${id}` |
| PATCH | 部分更新资源状态 | `PATCH /v1/product/${id}/stock` |
| DELETE | 删除资源 | `DELETE /v1/product/${id}` |

## 路由配置注意事项

### 后端路由配置
```python
# 插件 manifest.json
{
  "route_prefix": "/api/v1/{resource}",
  "routes": ["api/v1"]
}

# 路由文件
router = APIRouter(
    prefix="",  # 前缀为空，避免重复
    tags=["资源管理"]
)

# 具体路由
@router.get("/list", summary="获取列表")
async def get_list(): ...

@router.get("/{resource_id}", summary="获取详情")
async def get_detail(resource_id: int): ...
```

### 前端 API 调用
```javascript
// baseURL: '/api'
// 完整路径自动拼接为: /api/v1/{resource}/{action}

export const getList = (params) => {
  return request.get('/v1/{resource}/list', { params })
}

export const getDetail = (id) => {
  return request.get(`/v1/{resource}/${id}`)
}
```

## 特殊路由别名

为保持向后兼容，可以添加路由别名：

```python
# 主路由
@router.patch("/{customer_id}/toggle-status")
async def toggle_status(): ...

# 别名路由（兼容前端）
@router.patch("/{customer_id}/status")
async def toggle_status_alias():
    return await toggle_status()
```

## 分页参数规范

```javascript
// 前端调用
{
  page: 1,        // 页码，从1开始
  pageSize: 10,   // 每页数量
  // ... 其他筛选参数
}

// 后端响应
{
  code: 0,
  data: {
    total: 100,    // 总记录数
    page: 1,       // 当前页码
    pageSize: 10,  // 每页数量
    items: []      // 数据列表
  }
}
```

## 响应格式规范

### 成功响应
```json
{
  "code": 0,
  "msg": "操作成功",
  "data": { ... }
}
```

### 错误响应
```json
{
  "code": 400,
  "msg": "错误信息",
  "data": null
}
```
