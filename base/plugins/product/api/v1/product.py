"""
产品模块API
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

# 导入Pydantic模式和服务
try:
    from base.plugins.product.schemas.product_schema import (
        ProductResponse,
        ProductCreate,
        ProductUpdate,
        ProductListQuery,
        ProductListResponse,
        ProductStockUpdate,
        ProductSalesUpdate,
    )
    from base.plugins.product.services.product_service import ProductService
except ImportError:
    # 定义临时模式和服务，以便在没有实现的情况下也能工作
    from pydantic import BaseModel
    from typing import List, Dict, Any
    from decimal import Decimal

    class ProductBase(BaseModel):
        name: str
        price: Decimal
        stock: int = 0
        category: Optional[str] = None

    class ProductCreate(ProductBase):
        description: Optional[str] = None
        tags: Optional[List[str]] = None
        images: Optional[List[str]] = None
        is_active: bool = True
        is_hot: bool = False
        is_new: bool = False

    class ProductUpdate(BaseModel):
        name: Optional[str] = None
        description: Optional[str] = None
        price: Optional[Decimal] = None
        stock: Optional[int] = None
        category: Optional[str] = None
        tags: Optional[List[str]] = None
        images: Optional[List[str]] = None
        is_active: Optional[bool] = None
        is_hot: Optional[bool] = None
        is_new: Optional[bool] = None

    class ProductResponse(ProductBase):
        id: int
        description: Optional[str] = None
        tags: Optional[List[str]] = None
        images: Optional[List[str]] = None
        is_active: bool
        is_hot: bool
        is_new: bool
        view_count: int
        sales_count: int

        class Config:
            from_attributes = True

    class ProductListQuery(BaseModel):
        page: int = 1
        page_size: int = 10
        name: Optional[str] = None
        category: Optional[str] = None
        is_active: Optional[bool] = None
        is_hot: Optional[bool] = None
        is_new: Optional[bool] = None

    class ProductListResponse(BaseModel):
        total: int
        page: int
        page_size: int
        items: List[ProductResponse]

    class ProductStockUpdate(BaseModel):
        quantity: int

    class ProductSalesUpdate(BaseModel):
        quantity: int

    class ProductService:
        @staticmethod
        async def create_product(product_data):
            pass

        @staticmethod
        async def update_product(product_id, product_data):
            pass

        @staticmethod
        async def get_product_by_id(product_id):
            pass

        @staticmethod
        async def delete_product(product_id):
            pass

        @staticmethod
        async def toggle_product_status(product_id):
            pass

        @staticmethod
        async def update_stock(product_id, quantity):
            pass

        @staticmethod
        async def update_sales_count(product_id, quantity):
            pass

        @staticmethod
        async def increment_view_count(product_id):
            pass

        @staticmethod
        async def get_product_list(page, page_size, **filters):
            pass

        @staticmethod
        async def get_product_categories():
            pass

# 创建路由实例
product_router = APIRouter(
    prefix="",
    tags=["产品管理"]
)


# 为每个路由添加单数和复数两种路径
@product_router.post("/", summary="创建产品", status_code=status.HTTP_201_CREATED)
async def create_product(
        product_data: ProductCreate,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    创建新产品

    Args:
        product_data: 产品创建数据
        current_user_id: 当前用户ID

    Returns:
        创建成功的产品信息
    """
    try:
        product = await ProductService.create_product(product_data)
        # 使用to_dict方法确保datetime字段被正确转换
        if hasattr(product, 'to_dict'):
            product_dict = await product.to_dict()
        elif hasattr(product, 'dict'):
            product_dict = product.dict()
        else:
            product_dict = dict(product)
        return SuccessResponse(data=product_dict, msg="产品创建成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@product_router.get("/list", summary="获取产品列表(分页)")
async def get_product_list(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=1000, description="每页数量"),
        name: Optional[str] = Query(None, description="产品名称(模糊搜索)"),
        category: Optional[str] = Query(None, description="产品分类"),
        is_active: Optional[bool] = Query(None, description="是否上架"),
        is_hot: Optional[bool] = Query(None, description="是否热门"),
        is_new: Optional[bool] = Query(None, description="是否新品"),
        current_user_id: int = Depends(get_current_user_id)
):
    """
    获取产品列表(分页)

    Args:
        page: 页码
        page_size: 每页数量
        name: 产品名称(模糊搜索)
        category: 产品分类
        is_active: 是否上架
        is_hot: 是否热门
        is_new: 是否新品
        current_user_id: 当前用户ID

    Returns:
        产品列表
    """
    try:
        products, total = await ProductService.get_product_list(
            page=page,
            page_size=page_size,
            name=name,
            category=category,
            is_active=is_active,
            is_hot=is_hot,
            is_new=is_new
        )

        # 转换为字典列表
        product_list = []
        for product in products:
            if hasattr(product, 'to_dict'):
                product_dict = await product.to_dict()
            elif hasattr(product, 'dict'):
                product_dict = product.dict()
            else:
                product_dict = dict(product)
            product_list.append(product_dict)

        response_data = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": product_list
        }

        return SuccessResponse(data=response_data)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@product_router.get("/{product_id}", summary="获取产品详情")
async def get_product_detail(
        product_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    获取产品详情

    Args:
        product_id: 产品ID
        current_user_id: 当前用户ID

    Returns:
        产品详细信息
    """
    try:
        product = await ProductService.get_by_id(product_id)
        if not product:
            return ErrorResponse(msg="产品不存在", status_code=status.HTTP_404_NOT_FOUND)
        # 增加浏览次数
        await ProductService.increment_view_count(product_id)
        if hasattr(product, 'to_dict'):
            product_dict = await product.to_dict()
        elif hasattr(product, 'dict'):
            product_dict = product.dict()
        else:
            product_dict = dict(product)
        return SuccessResponse(data=product_dict)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@product_router.put("/{product_id}", summary="更新产品信息")
async def update_product(
        product_id: int,
        product_data: ProductUpdate,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    更新产品信息

    Args:
        product_id: 产品ID
        product_data: 更新数据
        current_user_id: 当前用户ID

    Returns:
        更新后的产品信息
    """
    try:
        updated_product = await ProductService.update_product(product_id, product_data)
        if not updated_product:
            return ErrorResponse(msg="产品不存在", status_code=status.HTTP_404_NOT_FOUND)
        if hasattr(updated_product, 'to_dict'):
            product_dict = await updated_product.to_dict()
        elif hasattr(updated_product, 'dict'):
            product_dict = updated_product.dict()
        else:
            product_dict = dict(updated_product)
        return SuccessResponse(data=product_dict, msg="产品更新成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@product_router.delete("/{product_id}", summary="删除产品")
async def delete_product(
        product_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    删除产品

    Args:
        product_id: 产品ID
        current_user_id: 当前用户ID

    Returns:
        删除结果
    """
    try:
        success = await ProductService.delete_product(product_id)
        if not success:
            return ErrorResponse(msg="产品不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(msg="产品删除成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@product_router.delete("/batch", summary="批量删除产品")
async def batch_delete_product(
        request_data: dict,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    批量删除产品

    Args:
        request_data: 包含ids数组的请求体
        current_user_id: 当前用户ID

    Returns:
        删除结果
    """
    try:
        ids = request_data.get("ids", [])
        if not ids:
            return ErrorResponse(msg="请选择要删除的产品", status_code=status.HTTP_400_BAD_REQUEST)

        success_count = 0
        for product_id in ids:
            success = await ProductService.delete_product(product_id)
            if success:
                success_count += 1

        return SuccessResponse(msg=f"成功删除{success_count}/{len(ids)}个产品")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@product_router.patch("/{product_id}/toggle-status", summary="切换产品上架状态")
async def toggle_product_status(
        product_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    切换产品上架状态

    Args:
        product_id: 产品ID
        current_user_id: 当前用户ID

    Returns:
        更新后的产品信息
    """
    try:
        updated_product = await ProductService.toggle_product_status(product_id)
        if not updated_product:
            return ErrorResponse(msg="产品不存在", status_code=status.HTTP_404_NOT_FOUND)
        if hasattr(updated_product, 'to_dict'):
            product_dict = await updated_product.to_dict()
        elif hasattr(updated_product, 'dict'):
            product_dict = updated_product.dict()
        else:
            product_dict = dict(updated_product)
        status_text = "上架" if updated_product.is_active else "下架"
        return SuccessResponse(data=product_dict, msg=f"产品已{status_text}")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@product_router.patch("/{product_id}/stock", summary="更新产品库存")
async def update_product_stock(
        product_id: int,
        stock_data: ProductStockUpdate,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    更新产品库存

    Args:
        product_id: 产品ID
        stock_data: 库存更新数据
        current_user_id: 当前用户ID

    Returns:
        更新后的产品信息
    """
    try:
        updated_product = await ProductService.update_stock(product_id, stock_data.quantity)
        if not updated_product:
            return ErrorResponse(msg="产品不存在", status_code=status.HTTP_404_NOT_FOUND)
        if hasattr(updated_product, 'to_dict'):
            product_dict = await updated_product.to_dict()
        elif hasattr(updated_product, 'dict'):
            product_dict = updated_product.dict()
        else:
            product_dict = dict(updated_product)
        return SuccessResponse(data=product_dict, msg="库存更新成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@product_router.patch("/{product_id}/sales", summary="更新产品销售数量")
async def update_product_sales(
        product_id: int,
        sales_data: ProductSalesUpdate,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    更新产品销售数量

    Args:
        product_id: 产品ID
        sales_data: 销售数量更新数据
        current_user_id: 当前用户ID

    Returns:
        更新后的产品信息
    """
    try:
        updated_product = await ProductService.update_sales_count(product_id, sales_data.quantity)
        if not updated_product:
            return ErrorResponse(msg="产品不存在", status_code=status.HTTP_404_NOT_FOUND)
        if hasattr(updated_product, 'to_dict'):
            product_dict = await updated_product.to_dict()
        elif hasattr(updated_product, 'dict'):
            product_dict = updated_product.dict()
        else:
            product_dict = dict(updated_product)
        return SuccessResponse(data=product_dict, msg="销售数量更新成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@product_router.patch("/{product_id}/view", summary="增加产品浏览次数")
async def increment_product_view(
        product_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """
    增加产品浏览次数

    Args:
        product_id: 产品ID
        current_user_id: 当前用户ID

    Returns:
        更新后的产品信息
    """
    try:
        updated_product = await ProductService.increment_view_count(product_id)
        if not updated_product:
            return ErrorResponse(msg="产品不存在", status_code=status.HTTP_404_NOT_FOUND)
        if hasattr(updated_product, 'to_dict'):
            product_dict = await updated_product.to_dict()
        elif hasattr(updated_product, 'dict'):
            product_dict = updated_product.dict()
        else:
            product_dict = dict(updated_product)
        return SuccessResponse(data=product_dict, msg="浏览次数更新成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@product_router.get("/categories/list", summary="获取所有产品分类")
async def get_product_categories(
        current_user_id: int = Depends(get_current_user_id)
):
    """
    获取所有产品分类

    Args:
        current_user_id: 当前用户ID

    Returns:
        产品分类列表
    """
    try:
        categories = await ProductService.get_product_categories()
        return SuccessResponse(data={"categories": categories}, msg="获取分类成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)



