import asyncio
import sys
import os
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base.common.setting import TORTOISE_ORM
from tortoise import Tortoise
from base.plugins.product.models.product import Product, ProductVariant


async def test_variant_create():
    await Tortoise.init(config=TORTOISE_ORM)
    
    try:
        product = await Product.get_or_none(name="听音T100充电盒")
        if not product:
            print("未找到产品")
            return
        
        print(f"找到产品: {product.name} (id={product.id})")
        print(f"产品created_at类型: {type(product.created_at)}")
        print(f"产品created_at值: {product.created_at}")
        
        data = {
            "product_id": product.id,
            "sku": "TEST-VAR-001",
            "price": Decimal("299.00"),
            "stock": 100,
            "attributes": []
        }
        
        print("\n开始创建变体...")
        print(f"数据: {data}")
        
        try:
            variant = await ProductVariant.create(**data)
            print(f"变体创建成功: {variant.id}")
        except Exception as e:
            print(f"创建失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(test_variant_create())
