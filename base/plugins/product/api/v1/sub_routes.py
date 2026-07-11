"""
产品子模块路由 - 分类、属性、变体等固定路径
"""
from fastapi import APIRouter, Query, status
from typing import Optional

try:
    from base.common.response import SuccessResponse, ErrorResponse
    RESPONSE_AVAILABLE = True
except ImportError:
    RESPONSE_AVAILABLE = False

sub_routes_router = APIRouter()


# ==================== 分类接口 ====================

try:
    from base.plugins.product.services.product_service import CategoryService
    from base.plugins.product.schemas.product_schema import CategoryCreate, CategoryUpdate
    CATEGORY_AVAILABLE = True
except ImportError:
    CategoryService = None
    CATEGORY_AVAILABLE = False


@sub_routes_router.get("/categories", summary="获取产品分类列表")
async def get_category_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=200, description="每页数量"),
    name: Optional[str] = Query(None, description="分类名称关键词"),
    parent_id: Optional[int] = Query(None, description="父分类ID"),
    is_active: Optional[bool] = Query(None, description="是否启用")
):
    try:
        items, total = await CategoryService.get_category_list(
            page=page, page_size=page_size,
            name=name, parent_id=parent_id, is_active=is_active
        )
        return SuccessResponse(data={"items": items, "total": total, "page": page, "page_size": page_size}, msg="获取分类列表成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.get("/categories/options", summary="获取产品分类选项（下拉选择用）")
async def get_category_options():
    try:
        options = await CategoryService.get_category_options()
        return SuccessResponse(data=options, msg="获取分类选项成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.get("/categories/{category_id}", summary="获取产品分类详情")
async def get_category(category_id: int):
    try:
        category = await CategoryService.get_category_by_id(category_id)
        if not category:
            return ErrorResponse(msg="分类不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data=category, msg="获取分类详情成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.post("/categories", summary="创建产品分类")
async def create_category(data: CategoryCreate):
    try:
        category = await CategoryService.create_category(data.dict())
        return SuccessResponse(data=category, msg="分类创建成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.put("/categories/{category_id}", summary="更新产品分类")
async def update_category(category_id: int, data: CategoryUpdate):
    try:
        category = await CategoryService.update_category(category_id, data.dict(exclude_unset=True))
        if not category:
            return ErrorResponse(msg="分类不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data=category, msg="分类更新成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.delete("/categories/{category_id}", summary="删除产品分类")
async def delete_category(category_id: int):
    try:
        success = await CategoryService.delete_category(category_id)
        if not success:
            return ErrorResponse(msg="分类不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data={"message": "分类删除成功"}, msg="分类删除成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


# ==================== 属性接口 ====================

try:
    from base.plugins.product.services.variant_service import (
        AttributeService,
        AttributeValueService
    )
    from base.plugins.product.schemas.product_schema import (
        AttributeCreate, AttributeUpdate,
        AttributeValueCreate, AttributeValueUpdate
    )
    ATTRIBUTE_AVAILABLE = True
except ImportError:
    ATTRIBUTE_AVAILABLE = False


@sub_routes_router.get("/attributes", summary="获取属性列表")
async def get_attribute_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    try:
        items, total = await AttributeService.get_attribute_list(
            page=page, page_size=page_size, name=name, category=category, is_active=is_active
        )
        return SuccessResponse(data={"items": items, "total": total, "page": page, "page_size": page_size}, msg="获取属性列表成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.get("/attributes/options", summary="获取属性选项")
async def get_attribute_options(category: Optional[str] = Query(None)):
    try:
        options = await AttributeService.get_attribute_options(category)
        return SuccessResponse(data=options, msg="获取属性选项成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.get("/attributes/{attr_id}", summary="获取属性详情")
async def get_attribute(attr_id: int):
    try:
        attr = await AttributeService.get_attribute_by_id(attr_id)
        if not attr:
            return ErrorResponse(msg="属性不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data=attr, msg="获取属性详情成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.post("/attributes", summary="创建属性")
async def create_attribute(data: AttributeCreate):
    try:
        attr = await AttributeService.create_attribute(data.dict())
        return SuccessResponse(data=attr, msg="属性创建成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.put("/attributes/{attr_id}", summary="更新属性")
async def update_attribute(attr_id: int, data: AttributeUpdate):
    try:
        attr = await AttributeService.update_attribute(attr_id, data.dict(exclude_unset=True))
        if not attr:
            return ErrorResponse(msg="属性不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data=attr, msg="属性更新成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.delete("/attributes/{attr_id}", summary="删除属性")
async def delete_attribute(attr_id: int):
    try:
        success = await AttributeService.delete_attribute(attr_id)
        if not success:
            return ErrorResponse(msg="属性不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data={"message": "属性删除成功"}, msg="属性删除成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.get("/attributes/{attr_id}/values", summary="获取属性值列表")
async def get_attribute_values(attr_id: int):
    try:
        values = await AttributeValueService.get_attribute_values(attr_id)
        return SuccessResponse(data=values, msg="获取属性值列表成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.post("/attributes/values", summary="创建属性值")
async def create_attribute_value(data: AttributeValueCreate):
    try:
        value = await AttributeValueService.create_attribute_value(data.dict())
        return SuccessResponse(data=value, msg="属性值创建成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.put("/attributes/values/{value_id}", summary="更新属性值")
async def update_attribute_value(value_id: int, data: AttributeValueUpdate):
    try:
        value = await AttributeValueService.update_attribute_value(value_id, data.dict(exclude_unset=True))
        if not value:
            return ErrorResponse(msg="属性值不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data=value, msg="属性值更新成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.delete("/attributes/values/{value_id}", summary="删除属性值")
async def delete_attribute_value(value_id: int):
    try:
        success = await AttributeValueService.delete_attribute_value(value_id)
        if not success:
            return ErrorResponse(msg="属性值不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data={"message": "属性值删除成功"}, msg="属性值删除成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


# ==================== 物料变体接口 ====================

try:
    from base.plugins.product.services.variant_service import MaterialVariantService
    from base.plugins.product.schemas.product_schema import (
        MaterialVariantCreate, MaterialVariantUpdate
    )
    MATERIAL_VARIANT_AVAILABLE = True
except ImportError:
    MATERIAL_VARIANT_AVAILABLE = False


@sub_routes_router.get("/material-variants", summary="获取物料变体列表")
async def get_material_variant_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    material_id: Optional[int] = Query(None),
    variant_code: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    try:
        items, total = await MaterialVariantService.get_material_variant_list(
            page=page, page_size=page_size, material_id=material_id, variant_code=variant_code, is_active=is_active
        )
        return SuccessResponse(data={"items": items, "total": total, "page": page, "page_size": page_size}, msg="获取物料变体列表成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.get("/material-variants/{variant_id}", summary="获取物料变体详情")
async def get_material_variant(variant_id: int):
    try:
        variant = await MaterialVariantService.get_material_variant_by_id(variant_id)
        if not variant:
            return ErrorResponse(msg="物料变体不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data=variant, msg="获取物料变体详情成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.post("/material-variants", summary="创建物料变体")
async def create_material_variant(data: MaterialVariantCreate):
    try:
        variant = await MaterialVariantService.create_material_variant(data.dict())
        return SuccessResponse(data=variant, msg="物料变体创建成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.put("/material-variants/{variant_id}", summary="更新物料变体")
async def update_material_variant(variant_id: int, data: MaterialVariantUpdate):
    try:
        variant = await MaterialVariantService.update_material_variant(variant_id, data.dict(exclude_unset=True))
        if not variant:
            return ErrorResponse(msg="物料变体不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data=variant, msg="物料变体更新成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.delete("/material-variants/{variant_id}", summary="删除物料变体")
async def delete_material_variant(variant_id: int):
    try:
        success = await MaterialVariantService.delete_material_variant(variant_id)
        if not success:
            return ErrorResponse(msg="物料变体不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data={"message": "物料变体删除成功"}, msg="物料变体删除成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


# ==================== 产品变体接口 ====================

try:
    from base.plugins.product.services.variant_service import ProductVariantService
    from base.plugins.product.schemas.product_schema import (
        ProductVariantCreate, ProductVariantUpdate
    )
    PRODUCT_VARIANT_AVAILABLE = True
except ImportError:
    PRODUCT_VARIANT_AVAILABLE = False


@sub_routes_router.get("/variants", summary="获取产品变体列表")
async def get_product_variant_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    product_id: Optional[int] = Query(None),
    sku: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    try:
        items, total = await ProductVariantService.get_product_variant_list(
            page=page, page_size=page_size, product_id=product_id, sku=sku, is_active=is_active
        )
        return SuccessResponse(data={"items": items, "total": total, "page": page, "page_size": page_size}, msg="获取产品变体列表成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.get("/variants/{variant_id}", summary="获取产品变体详情")
async def get_product_variant(variant_id: int):
    try:
        variant = await ProductVariantService.get_product_variant_by_id(variant_id)
        if not variant:
            return ErrorResponse(msg="产品变体不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data=variant, msg="获取产品变体详情成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.post("/variants", summary="创建产品变体")
async def create_product_variant(data: ProductVariantCreate):
    try:
        variant = await ProductVariantService.create_product_variant(data.dict())
        return SuccessResponse(data=variant, msg="产品变体创建成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.put("/variants/{variant_id}", summary="更新产品变体")
async def update_product_variant(variant_id: int, data: ProductVariantUpdate):
    try:
        variant = await ProductVariantService.update_product_variant(variant_id, data.dict(exclude_unset=True))
        if not variant:
            return ErrorResponse(msg="产品变体不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data=variant, msg="产品变体更新成功")
    except ValueError as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@sub_routes_router.delete("/variants/{variant_id}", summary="删除产品变体")
async def delete_product_variant(variant_id: int):
    try:
        success = await ProductVariantService.delete_product_variant(variant_id)
        if not success:
            return ErrorResponse(msg="产品变体不存在", status_code=status.HTTP_404_NOT_FOUND)
        return SuccessResponse(data={"message": "产品变体删除成功"}, msg="产品变体删除成功")
    except Exception as e:
        return ErrorResponse(msg=str(e), status_code=status.HTTP_400_BAD_REQUEST)