#!/usr/bin/env python3
"""
测试旅行工具是否能正常工作
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "base"))

# 测试工具执行
print("🧪 测试工具执行...")
print("="*50)

async def test_tools():
    # 测试 flight_query
    print("\n1️⃣ 测试航班查询工具...")
    from base.plugins.agent.tools.travel.flight_query import FlightQueryTool
    result = FlightQueryTool.execute({
        "from_city": "北京",
        "to_city": "上海",
        "date": "2024-05-15",
        "passengers": 2,
        "travel_class": "economy"
    })
    
    print("✓ 航班查询结果:", result)
    
    # 测试 hotel_query
    print("\n2️⃣ 测试酒店查询工具...")
    from base.plugins.agent.tools.travel.hotel_query import HotelQueryTool
    result = HotelQueryTool.execute({
        "city": "上海",
        "checkin": "2024-05-15",
        "checkout": "2024-05-18",
        "guests": 2,
        "price_range": [200, 2000],
        "rating": 4.0
    })
    
    print("✓ 酒店查询结果:", result)
    
    # 测试 weather_query
    print("\n3️⃣ 测试天气查询工具...")
    from base.plugins.agent.tools.travel.weather_query import WeatherQueryTool
    result = WeatherQueryTool.execute({
        "city": "上海",
        "days": 7
    })
    
    print("✓ 天气查询结果:", result)
    
    print("\n" + "="*50)
    print("✅ 所有工具测试通过!")

asyncio.run(test_tools())
