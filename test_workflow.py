#!/usr/bin/env python3
"""
测试 travel workflow 的执行
"""

import asyncio
import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "base"))

# 导入必要的模块
from base.plugins.agent.services.langgraph_executor import LangGraphExecutor

# 注册工具
print("正在注册工具...")
from base.plugins.agent.tools.registry import ToolRegistry

# 手动注册旅行工具
from base.plugins.agent.tools.travel.flight_query import FlightQueryTool
from base.plugins.agent.tools.travel.hotel_query import HotelQueryTool
from base.plugins.agent.tools.travel.weather_query import WeatherQueryTool

ToolRegistry.register("flight_query", FlightQueryTool)
ToolRegistry.register("hotel_query", HotelQueryTool)
ToolRegistry.register("weather_query", WeatherQueryTool)

print("✅ 工具注册完成")

# 加载 workflow
print("\n正在加载工作流...")
with open(os.path.join(os.path.dirname(__file__), "docs", "workflow6.json"), "r", encoding="utf-8") as f:
    workflow_data = json.load(f)

nodes = workflow_data.get("nodes", [])
edges = workflow_data.get("edges", [])

print(f"✅ 工作流加载成功: {len(nodes)} 个节点, {len(edges)} 条边")

# 创建测试用的 Agent 对象
class MockAgent:
    def __init__(self):
        self.id = 1
        self.name = "Test Agent"

mock_agent = MockAgent()

# 测试输入
test_input = {
    "text": "我想在5月15号去上海旅行，预算适中，2个人，住3天。"
}

print(f"\n🧪 测试输入: {test_input['text']}")

# 定义 SSE 回调
async def sse_yield_func(event):
    print(f"\n📡 事件: {event.get('type')} - {event.get('label', '')}")
    if 'content' in event:
        print(f"   内容: {str(event['content'])[:150]}...")

# 执行工作流
print("\n🚀 开始执行工作流...")
print("="*50)

result = asyncio.run(
    LangGraphExecutor.execute_langgraph(
        agent=mock_agent,
        nodes=nodes,
        edges=edges,
        input_data=test_input,
        customer_id=1,
        user_id=1,
        sse_yield_func=sse_yield_func
    )
)

print("\n" + "="*50)
print("✅ 工作流执行完成!")
print(f"\n📊 执行结果:")
print(json.dumps(result, ensure_ascii=False, indent=2))

print(f"\n📝 执行轨迹:")
trace = result.get("trace", [])
for step in trace:
    print(f"  • [{step['timestamp']}] {step['label']} ({step['node_type']})")
