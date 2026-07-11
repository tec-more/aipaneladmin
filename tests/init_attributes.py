import asyncio
import sys
sys.path.insert(0, '.')

async def init_attributes():
    from tortoise import Tortoise, connections
    from base.common.setting import TORTOISE_ORM
    
    config = TORTOISE_ORM.copy()
    config['apps']['models']['models'].append('base.plugins.product.models.attribute')
    
    await Tortoise.init(config=config)
    
    conn = connections.get('postgres')
    
    attributes = [
        ('颜色', 'color', 'both', 1),
        ('尺码', 'size', 'both', 2),
        ('内存', 'memory', 'product', 3),
        ('容量', 'capacity', 'both', 4),
        ('材质', 'material', 'both', 5),
        ('规格', 'spec', 'material', 6),
    ]
    
    attr_values = {
        'color': ['红色', '蓝色', '黑色', '白色', '灰色', '绿色'],
        'size': ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
        'memory': ['4GB', '8GB', '16GB', '32GB', '64GB'],
        'capacity': ['16GB', '32GB', '64GB', '128GB', '256GB', '512GB'],
        'material': ['塑料', '金属', '硅胶', '皮革', '布料'],
        'spec': ['标准', '豪华', '旗舰', '入门'],
    }
    
    for name, code, category, sort in attributes:
        exists = await conn.execute_query(
            'SELECT COUNT(*) FROM product_attribute WHERE name = $1',
            [name]
        )
        if exists == 0:
            await conn.execute_query(
                'INSERT INTO product_attribute (name, code, category, sort) VALUES ($1, $2, $3, $4)',
                [name, code, category, sort]
            )
            print('插入属性:', name)
        else:
            print('已存在:', name)
    
    for code, values in attr_values.items():
        result = await conn.execute_query(
            'SELECT id FROM product_attribute WHERE code = $1',
            [code]
        )
        if result[0] > 0 and len(result[1]) > 0:
            attr_id = result[1][0][0]
            for idx, val in enumerate(values):
                await conn.execute_query(
                    'INSERT INTO product_attribute_value (attribute_id, value, sort) VALUES ($1, $2, $3)',
                    [attr_id, val, idx]
                )
                print('  插入属性值:', val)
    
    await Tortoise.close_connections()

asyncio.run(init_attributes())