import asyncio
import sys
sys.path.insert(0, '.')

async def create_tables():
    from tortoise import Tortoise, connections
    from base.common.setting import TORTOISE_ORM
    
    config = TORTOISE_ORM.copy()
    config['apps']['models']['models'].extend([
        'base.plugins.product.models.attribute',
        'base.plugins.product.models.product',
        'base.plugins.mes.models.base_data',
    ])
    
    await Tortoise.init(config=config)
    
    conn = connections.get('postgres')
    
    tables = [
        """
        CREATE TABLE IF NOT EXISTS product_attribute (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            code VARCHAR(50) NOT NULL UNIQUE,
            category VARCHAR(50) DEFAULT 'both',
            sort INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_attribute_value (
            id SERIAL PRIMARY KEY,
            attribute_id INTEGER REFERENCES product_attribute(id) ON DELETE CASCADE,
            value VARCHAR(100) NOT NULL,
            sort INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS product_variant (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES product(id) ON DELETE CASCADE,
            sku VARCHAR(100) NOT NULL UNIQUE,
            attributes JSONB,
            price DECIMAL(10,2) NOT NULL,
            original_price DECIMAL(10,2),
            stock INTEGER DEFAULT 0,
            material_variant_id INTEGER,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS mes_material_variant (
            id SERIAL PRIMARY KEY,
            material_id INTEGER REFERENCES mes_material(id) ON DELETE CASCADE,
            variant_code VARCHAR(100) NOT NULL UNIQUE,
            attributes JSONB,
            specification VARCHAR(255),
            unit VARCHAR(20),
            initial_stock INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]
    
    for sql in tables:
        try:
            await conn.execute_query(sql)
            print('表创建成功')
        except Exception as e:
            print('表可能已存在:', e)
    
    await Tortoise.close_connections()

asyncio.run(create_tables())