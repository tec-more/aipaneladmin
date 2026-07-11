import asyncio
import sys
sys.path.insert(0, '.')

async def insert_categories():
    from tortoise import Tortoise, connections
    from base.common.setting import TORTOISE_ORM
    
    config = TORTOISE_ORM.copy()
    config['apps']['models']['models'].append('base.plugins.product.models.product')
    
    await Tortoise.init(config=config)
    
    conn = connections.get('postgres')
    
    categories = [
        ('蓝牙耳机', 'BLUETOOTH', 1, '各类蓝牙耳机产品'),
        ('配件', 'ACCESSORY', 2, '耳机配件及周边产品'),
        ('电子设备', 'ELECTRONICS', 3, '消费电子设备'),
        ('数码产品', 'DIGITAL', 4, '数码产品'),
        ('充值套餐', 'RECHARGE', 5, '会员充值套餐'),
        ('会员套餐', 'MEMBERSHIP', 6, '会员专属套餐'),
    ]
    
    for name, code, sort, desc in categories:
        exists = await conn.execute_query(
            'SELECT COUNT(*) FROM product_category WHERE name = $1',
            [name]
        )
        if exists == 0:
            await conn.execute_query(
                'INSERT INTO product_category (name, code, sort, description) VALUES ($1, $2, $3, $4)',
                [name, code, sort, desc]
            )
            print('创建:', name)
        else:
            print('已存在:', name)
    
    await Tortoise.close_connections()

asyncio.run(insert_categories())