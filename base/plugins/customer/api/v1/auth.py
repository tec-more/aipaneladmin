"""
客户认证API - 认证相关功能
职责：客户注册、登录（密码/验证码）、Token管理、密码管理、验证码

注意：客户管理功能（CRUD、列表等）已迁移到 customer.py
"""
from datetime import timedelta
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional

from base.common.security import (
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user_id,
)
from base.common.response import success_response, fail_response
from base.core.users.models.users import User
from base.core.users.services.email_service import EmailService

auth_router = APIRouter(prefix="/auth", tags=["客户认证"])


class SendCodeSchema(BaseModel):
    """发送验证码请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    type: str = Field(..., description="验证码类型: register, login, reset_password")


class VerifyCodeSchema(BaseModel):
    """验证码登录请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., description="验证码")


class CustomerRegisterSchema(BaseModel):
    """客户注册请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    code: str = Field(..., description="验证码")
    nickname: Optional[str] = Field(default=None, max_length=50, description="昵称")


class CustomerPasswordLoginSchema(BaseModel):
    """客户密码登录请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class CustomerUpdatePasswordSchema(BaseModel):
    """客户修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


async def get_or_create_customer_by_email(email: str, user: User = None) -> "Customer":
    """通过邮箱获取或创建客户记录"""
    from base.plugins.customer.models.customer import Customer

    if user:
        # 如果有User对象，通过system_user关联查找
        customer = await Customer.get_or_none(system_user_id=user.id)

        if not customer:
            # 如果没找到，尝试通过email查找
            customer = await Customer.get_or_none(email=email)

            if not customer:
                # 创建新的客户记录
                customer = await Customer.create(
                    system_user_id=user.id,
                    username=user.username,
                    email=user.email,
                    nickname=getattr(user, "nickname", None),
                    avatar=getattr(user, "avatar", None),
                    is_active=True
                )
            else:
                # 如果通过email找到了，更新关联
                customer.system_user_id = user.id
                await customer.save()

        return customer
    else:
        # 没有User对象，通过email查找
        customer = await Customer.get_or_none(email=email)
        return customer


@auth_router.post("/register", summary="客户注册")
async def customer_register(register_data: CustomerRegisterSchema):
    """
    客户注册（API调用，前端页面不显示注册按钮）

    需要提供邮箱、密码和验证码
    用于PC端程序调用

    Returns:
        客户信息和Token
    """
    from base.plugins.customer.models.customer import Customer
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # 验证验证码
    is_valid = EmailService.verify_code(register_data.email, register_data.code, "register")

    if not is_valid:
        return fail_response(msg="验证码错误或已过期")

    # 检查邮箱是否已被注册
    existing_customer = await Customer.get_or_none(email=register_data.email)
    if existing_customer:
        return fail_response(msg="该邮箱已被注册")

    # 同时检查系统User表
    from base.core.users.services.user_service import UserService
    if await UserService.check_email_exists(register_data.email):
        return fail_response(msg="该邮箱已被注册")

    # 生成用户名（基于邮箱）
    username = register_data.email.split("@")[0]

    # 检查用户名是否存在，如果存在则添加随机后缀
    username_exists = await Customer.get_or_none(username=username)
    if username_exists:
        import random
        import string
        suffix = ''.join(random.choices(string.digits, k=4))
        username = f"{username}_{suffix}"

    # 创建客户
    hashed_password = pwd_context.hash(register_data.password)

    customer = await Customer.create(
        username=username,
        email=register_data.email,
        password=hashed_password,
        nickname=register_data.nickname or username,
        is_active=True,
        is_verified=True  # 通过验证码验证后直接标记为已验证
    )

    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(customer.id), "email": customer.email},
        expires_delta=access_token_expires
    )

    # 更新最后登录时间
    from datetime import datetime
    customer.last_login = datetime.now()
    customer.login_count = 1
    await customer.save()

    # 转换客户信息
    customer_dict = await customer.to_dict()

    # 返回token和客户信息
    token_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "customer": customer_dict
    }

    return success_response(data=token_data, msg="注册成功")


@auth_router.post("/login", summary="客户密码登录")
async def customer_login_with_password(login_data: CustomerPasswordLoginSchema):
    """
    使用邮箱和密码登录

    Returns:
        Token和客户信息
    """
    from base.plugins.customer.models.customer import Customer
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # 查找客户
    customer = await Customer.get_or_none(email=login_data.email)

    if not customer:
        return fail_response(msg="邮箱或密码错误")

    if not customer.is_active:
        return fail_response(msg="账号已被禁用，请联系管理员")

    # 验证密码
    if not pwd_context.verify(login_data.password, customer.password):
        return fail_response(msg="邮箱或密码错误")

    # 创建访问令牌
    user_id = customer.system_user_id if customer.system_user_id else customer.id
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user_id), "typ": "cus", "email": customer.email},
        expires_delta=access_token_expires
    )

    # 更新最后登录时间
    from datetime import datetime
    customer.last_login = datetime.now()
    customer.login_count += 1
    await customer.save()

    # 转换客户信息
    customer_dict = await customer.to_dict()

    # 返回token和客户信息
    token_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "customer": customer_dict
    }

    return success_response(data=token_data, msg="登录成功")


@auth_router.post("/send-code", summary="发送客户验证码")
async def send_customer_code(code_data: SendCodeSchema):
    """
    发送验证码到客户邮箱

    支持的验证码类型:
    - register: 注册新客户
    - login: 客户验证码登录
    - reset_password: 重置密码
    """
    from base.plugins.customer.models.customer import Customer

    # 验证类型
    valid_types = ["register", "login", "reset_password"]
    if code_data.type not in valid_types:
        return fail_response(
            msg=f"无效的验证码类型，必须是: {', '.join(valid_types)}"
        )

    # 如果是注册类型，检查邮箱是否已被注册
    if code_data.type == "register":
        existing_customer = await Customer.get_or_none(email=code_data.email)
        if existing_customer:
            return fail_response(msg="该邮箱已被注册")

    # 如果是登录类型，检查邮箱是否存在
    if code_data.type == "login":
        # 检查Customer表中是否存在该邮箱
        existing_customer = await Customer.get_or_none(email=code_data.email)
        if not existing_customer:
            return fail_response(msg="该邮箱未注册")

    # 发送验证码
    success, message = await EmailService.send_code(code_data.email, code_data.type)

    if success:
        return success_response(msg=message)
    else:
        return fail_response(msg=message)


@auth_router.post("/login-code", summary="客户验证码登录")
async def customer_login_with_code(login_data: VerifyCodeSchema):
    """
    使用邮箱和验证码登录

    Returns:
        Token和客户信息
    """
    from base.plugins.customer.models.customer import Customer

    # 验证验证码
    is_valid = EmailService.verify_code(login_data.email, login_data.code, "login")

    if not is_valid:
        return fail_response(msg="验证码错误或已过期")

    # 查找客户
    customer = await Customer.get_or_none(email=login_data.email)

    # 如果Customer表中没有，尝试从User表查找并创建Customer记录
    if not customer:
        from base.core.users.services.user_service import UserService
        user = await UserService.get_by_email(login_data.email)

        if not user:
            return fail_response(msg="用户不存在")

        customer = await get_or_create_customer_by_email(login_data.email, user)
    else:
        # 如果Customer记录存在但没有关联User，尝试关联
        if not customer.system_user_id:
            from base.core.users.services.user_service import UserService
            user = await UserService.get_by_email(login_data.email)

            if user:
                customer.system_user_id = user.id
                await customer.save()

    if not customer.is_active:
        return fail_response(msg="账号已被禁用，请联系管理员")

    # 创建访问令牌 - 使用User ID如果有关联，否则使用Customer ID
    user_id = customer.system_user_id if customer.system_user_id else customer.id
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user_id), "email": customer.email},
        expires_delta=access_token_expires
    )

    # 更新最后登录时间
    from datetime import datetime
    customer.last_login = datetime.now()
    customer.login_count += 1
    await customer.save()

    # 转换客户信息
    customer_dict = await customer.to_dict()

    # 返回token和客户信息
    token_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "customer": customer_dict
    }

    return success_response(data=token_data, msg="登录成功")


@auth_router.post("/verify-code", summary="验证客户验证码")
async def verify_customer_code(verify_data: VerifyCodeSchema):
    """
    验证客户验证码（用于前端验证）

    Returns:
        验证结果
    """
    is_valid = EmailService.verify_code(verify_data.email, verify_data.code, "login")

    if is_valid:
        return success_response(msg="验证码正确")
    else:
        return fail_response(msg="验证码错误或已过期")


@auth_router.get("/check-email", summary="检查客户邮箱是否存在")
async def check_customer_email(email: str = Query(..., description="邮箱地址")):
    """
    检查客户邮箱是否已注册

    Returns:
        是否存在
    """
    from base.plugins.customer.models.customer import Customer

    customer = await Customer.get_or_none(email=email)

    # 同时检查User表
    from base.core.users.services.user_service import UserService
    user_exists = await UserService.check_email_exists(email)

    exists = customer is not None or user_exists

    return success_response(data={
        "exists": exists,
        "email": email
    })


@auth_router.get("/me", summary="获取当前客户信息")
async def get_current_customer(user_id: int = Depends(get_current_user_id)):
    """
    获取当前登录客户的信息

    这是唯一获取当前用户信息的端点（位于认证模块）
    客户管理模块中已删除重复的 /me 端点

    Returns:
        客户信息
    """
    from base.plugins.customer.models.customer import Customer

    # 先通过Customer ID查找
    customer = await Customer.get_or_none(id=user_id)

    # 如果没找到，通过system_user_id查找
    if not customer:
        customer = await Customer.get_or_none(system_user_id=user_id)

    if not customer:
        return fail_response(msg="客户不存在")

    customer_dict = await customer.to_dict()
    return success_response(data=customer_dict)


@auth_router.post("/change-password", summary="修改客户密码")
async def change_customer_password(
        password_data: CustomerUpdatePasswordSchema,
        user_id: int = Depends(get_current_user_id)
):
    """
    修改当前客户密码

    Returns:
        修改结果
    """
    from base.plugins.customer.models.customer import Customer
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # 先通过Customer ID查找
    customer = await Customer.get_or_none(id=user_id)

    # 如果没找到，通过system_user_id查找
    if not customer:
        customer = await Customer.get_or_none(system_user_id=user_id)

    if not customer:
        return fail_response(msg="客户不存在")

    # 验证旧密码
    if not pwd_context.verify(password_data.old_password, customer.password):
        return fail_response(msg="旧密码错误")

    # 更新密码
    customer.password = pwd_context.hash(password_data.new_password)
    await customer.save()

    return success_response(msg="密码修改成功")


@auth_router.post("/logout", summary="客户登出")
async def customer_logout():
    """
    客户登出(客户端需要删除本地token)

    Returns:
        登出成功消息
    """
    # JWT是无状态的,登出主要由前端处理(删除token)
    # 这里可以添加一些登出日志记录
    return success_response(msg="登出成功")


class ResetPasswordSchema(BaseModel):
    """重置密码请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., description="验证码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


@auth_router.post("/reset-password", summary="重置客户密码")
async def reset_customer_password(reset_data: ResetPasswordSchema):
    """
    通过验证码重置密码

    用于忘记密码时重置密码

    Returns:
        重置结果
    """
    from base.plugins.customer.models.customer import Customer
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # 验证验证码
    is_valid = EmailService.verify_code(reset_data.email, reset_data.code, "reset_password")

    if not is_valid:
        return fail_response(msg="验证码错误或已过期")

    # 查找客户
    customer = await Customer.get_or_none(email=reset_data.email)

    if not customer:
        return fail_response(msg="用户不存在")

    # 更新密码
    customer.password = pwd_context.hash(reset_data.new_password)
    await customer.save()

    return success_response(msg="密码重置成功，请使用新密码登录")
