"""
客户模块API
"""
from fastapi import APIRouter, Depends, status, Query
from typing import Optional

# 导入响应类
try:
    from base.common.response import SuccessResponse, ErrorResponse
except ImportError:
    # 定义临时响应类，以便在没有base模块的情况下也能工作
    class SuccessResponse:
        def __init__(self, data=None, msg="操作成功"):
            self.data = data
            self.msg = msg
            self.success = True

    class ErrorResponse:
        def __init__(self, msg="操作失败", status_code=400):
            self.msg = msg
            self.success = False
            self.status_code = status_code

# 导入安全相关模块
try:
    from base.common.security import get_current_user_id
except ImportError:
    # 定义临时依赖，以便在没有base模块的情况下也能工作
    from fastapi import HTTPException
    async def get_current_user_id():
        raise HTTPException(status_code=401, detail="未授权")

# 导入Pydantic模式和服务（稍后创建）
try:
    from base.plugins.customer.schemas.customer_schema import (
        CustomerResponse,
        CustomerCreate,
        CustomerUpdate,
        CustomerLogin,
        CustomerListQuery,
        CustomerListResponse,
    )
    from base.plugins.customer.services.customer_service import CustomerService
except ImportError:
    # 定义临时模式和服务，以便在没有实现的情况下也能工作
    from pydantic import BaseModel, EmailStr
    from typing import List, Dict, Any

    class CustomerBase(BaseModel):
        username: str
        email: EmailStr
        phone: Optional[str] = None

    class CustomerCreate(CustomerBase):
        password: str

    class CustomerUpdate(BaseModel):
        username: Optional[str] = None
        email: Optional[EmailStr] = None
        phone: Optional[str] = None
        password: Optional[str] = None

    class CustomerResponse(CustomerBase):
        id: int
        is_active: bool

        class Config:
            from_attributes = True

    class CustomerLogin(BaseModel):
        email: EmailStr
        password: str

    class CustomerListQuery(BaseModel):
        page: int = 1
        page_size: int = 10
        username: Optional[str] = None
        email: Optional[str] = None
        phone: Optional[str] = None

    class CustomerListResponse(BaseModel):
        total: int
        page: int
        page_size: int
        items: List[CustomerResponse]

    class CustomerService:
        @staticmethod
        async def register_customer(customer_data):
            pass

        @staticmethod
        async def login_customer(email, password):
            pass

        @staticmethod
        async def get_customer_info(customer_id):
            pass

        @staticmethod
        async def update_customer_info(customer_id, customer_data):
            pass

        @staticmethod
        async def get_customer_list(page, page_size, **filters):
            pass

        @staticmethod
        async def toggle_customer_status(customer_id):
            pass

        @staticmethod
        async def delete_customer(customer_id):
            pass

router = APIRouter(prefix="/api/v1/customer", tags=["客户管理"])


@router.post("/register", summary="客户注册")
async def register_customer(customer_data: CustomerCreate):
    """
    客户注册接口

    Args:
        customer_data: 客户注册数据

    Returns:
        注册成功的客户信息
    """
    try:
        customer = await CustomerService.register_customer(customer_data)
        # 使用to_dict方法确保datetime字段被正确转换
        if hasattr(customer, 'to_dict'):
            customer_dict = await customer.to_dict()
        elif hasattr(customer, 'dict'):
            customer_dict = customer.dict()
        else:
            customer_dict = dict(customer)
        return SuccessResponse(data=customer_dict, msg="注册成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@router.post("/login", summary="客户登录")
async def login_customer(login_data: CustomerLogin):
    """
    客户登录接口

    Args:
        login_data: 客户登录数据

    Returns:
        登录成功的客户信息和token
    """
    try:
        result = await CustomerService.login_customer(login_data.email, login_data.password)
        return SuccessResponse(data=result, msg="登录成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_401_UNAUTHORIZED)


@router.get("/me", summary="获取当前客户信息")
async def get_current_customer_info(current_customer_id: int = Depends(get_current_user_id)):
    """
    获取当前登录客户的详细信息

    Returns:
        当前客户的详细信息
    """
    try:
        customer = await CustomerService.get_customer_info(current_customer_id)
        if not customer:
            return ErrorResponse(msg="用户不存在", status_code=status.HTTP_404_NOT_FOUND)
        customer_dict = customer.dict() if hasattr(customer, 'dict') else dict(customer)
        return SuccessResponse(data=customer_dict)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@router.put("/me", summary="更新当前客户信息")
async def update_current_customer_info(
        customer_data: CustomerUpdate,
        current_customer_id: int = Depends(get_current_user_id)
):
    """
    更新当前登录客户的信息

    Args:
        customer_data: 客户更新数据
        current_customer_id: 当前客户ID

    Returns:
        更新后的客户信息
    """
    try:
        updated_customer = await CustomerService.update_customer_info(current_customer_id, customer_data)
        if not updated_customer:
            return ErrorResponse(msg="用户不存在", status_code=status.HTTP_404_NOT_FOUND)
        customer_dict = updated_customer.dict() if hasattr(updated_customer, 'dict') else dict(updated_customer)
        return SuccessResponse(data=customer_dict, msg="更新成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@router.get("/list", summary="获取客户列表(分页)")
async def get_customer_list(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        username: Optional[str] = Query(None, description="用户名(模糊搜索)"),
        email: Optional[str] = Query(None, description="邮箱(模糊搜索)"),
        phone: Optional[str] = Query(None, description="手机号(模糊搜索)"),
        is_active: Optional[bool] = Query(None, description="是否激活"),
        current_user_id: int = Depends(get_current_user_id)
):
    """
    获取客户列表(分页)

    需要认证

    Args:
        page: 页码
        page_size: 每页数量
        username: 用户名(模糊搜索)
        email: 邮箱(模糊搜索)
        phone: 手机号(模糊搜索)
        is_active: 是否激活
        current_user_id: 当前客户ID

    Returns:
        客户列表
    """
    try:
        customers, total = await CustomerService.get_customer_list(
            page=page,
            page_size=page_size,
            username=username,
            email=email,
            phone=phone,
            is_active=is_active
        )

        # 转换为字典列表
        customer_list = []
        for customer in customers:
            if hasattr(customer, 'to_dict'):
                customer_dict = await customer.to_dict()
            elif hasattr(customer, 'dict'):
                customer_dict = customer.dict()
            else:
                customer_dict = dict(customer)
            customer_list.append(customer_dict)

        response_data = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": customer_list
        }

        return SuccessResponse(data=response_data)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@router.get("/{customer_id}", summary="获取客户详情")
async def get_customer_detail(
        customer_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    获取客户详情

    Args:
        customer_id: 客户ID
        current_user_id: 当前客户ID

    Returns:
        客户详细信息
    """
    try:
        customer = await CustomerService.get_customer_info(customer_id)
        if not customer:
            return ErrorResponse(msg="用户不存在", status_code=status.HTTP_404_NOT_FOUND)
        customer_dict = customer.dict() if hasattr(customer, 'dict') else dict(customer)
        return SuccessResponse(data=customer_dict)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@router.put("/{customer_id}", summary="更新客户信息")
async def update_customer(
        customer_id: int,
        customer_data: CustomerUpdate,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    更新客户信息(管理员功能)

    Args:
        customer_id: 客户ID
        customer_data: 更新数据
        current_user_id: 当前客户ID

    Returns:
        更新后的客户信息
    """
    try:
        updated_customer = await CustomerService.update_customer_info(customer_id, customer_data)
        if not updated_customer:
            return ErrorResponse(msg="用户不存在", status_code=status.HTTP_404_NOT_FOUND)
        customer_dict = updated_customer.dict() if hasattr(updated_customer, 'dict') else dict(updated_customer)
        return SuccessResponse(data=customer_dict, msg="更新成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@router.delete("/{customer_id}", summary="删除客户")
async def delete_customer(
        customer_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    删除客户(管理员功能)

    Args:
        customer_id: 客户ID
        current_user_id: 当前客户ID

    Returns:
        删除结果
    """
    try:
        success = await CustomerService.delete_customer(customer_id)
        if not success:
            return ErrorResponse(msg="用户不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(msg="删除成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@router.patch("/{customer_id}/toggle-status", summary="切换客户状态")
async def toggle_customer_status(
        customer_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    切换客户激活状态(管理员功能)

    Args:
        customer_id: 客户ID
        current_user_id: 当前客户ID

    Returns:
        更新后的客户信息
    """
    try:
        updated_customer = await CustomerService.toggle_customer_status(customer_id)
        if not updated_customer:
            return ErrorResponse(msg="用户不存在", status_code=status.HTTP_404_NOT_FOUND)
        customer_dict = updated_customer.dict() if hasattr(updated_customer, 'dict') else dict(updated_customer)
        status_text = "激活" if updated_customer.is_active else "禁用" if hasattr(updated_customer, 'is_active') else "未知"
        return SuccessResponse(data=customer_dict, msg=f"用户已{status_text}")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)