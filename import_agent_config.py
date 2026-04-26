#!/usr/bin/env python3
"""
智能体配置导入脚本
用于将配置导入到指定智能体
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def list_config_files():
    """列出所有可用的配置文件"""
    docs_dir = project_root / "docs"
    config_files = []
    
    if docs_dir.exists():
        for file in docs_dir.glob("*.json"):
            if "任务" in file.name or "agent" in file.name.lower() or "ReAct" in file.name:
                config_files.append(file)
    
    return config_files


async def import_agent_config():
    """导入智能体配置"""
    try:
        from base.plugins.agent.models.agent import Agent
        from base.common.database import init_db
        from tortoise import Tortoise

        # 初始化数据库
        print("正在初始化数据库...")
        await init_db()

        # 询问智能体ID
        agent_id = input("请输入智能体ID (例如: 9): ").strip()
        if not agent_id:
            print("错误: 智能体ID不能为空")
            return

        try:
            agent_id = int(agent_id)
        except ValueError:
            print("错误: 智能体ID必须是数字")
            return

        # 获取智能体
        print(f"正在获取智能体 ID: {agent_id}...")
        agent = await Agent.get_or_none(id=agent_id)
        if not agent:
            print(f"错误: 找不到ID为 {agent_id} 的智能体")
            return

        print(f"找到智能体: {agent.name} (ID: {agent.id})")
        print(f"当前 graph_definition: {'已配置' if agent.graph_definition else 'None'}")

        # 列出可用配置文件
        config_files = list_config_files()
        if not config_files:
            print("错误: 在 docs 目录下找不到可用的配置文件")
            return

        print("\n可用的配置文件:")
        for i, file in enumerate(config_files, 1):
            print(f"  {i}. {file.name}")

        # 选择配置文件
        choice = input("\n请选择配置文件 (输入数字): ").strip()
        try:
            choice_idx = int(choice) - 1
            if choice_idx < 0 or choice_idx >= len(config_files):
                print("错误: 无效选择")
                return
            config_path = config_files[choice_idx]
        except ValueError:
            print("错误: 请输入数字")
            return

        # 读取配置文件
  print(f"\n正在读取配置文件: {config_path.name}...")
  with open(config_path, "r", encoding="utf-8") as f:
    graph_data = json.load(f)

  # 确保格式正确 - 提取 nodes 和 edges
  if "说明" in graph_data and "nodes" in graph_data:
    # 已经是正确格式
    pass
  elif "nodes" not in graph_data:
    # 尝试找是否有内嵌的结构
    print("警告: 配置文件格式可能不正确，尝试提取...")

  # 为缺失 position 的节点添加默认位置
  print("检查节点位置信息...")
  if graph_data.get("nodes"):
    for i, node in enumerate(graph_data["nodes"]):
      if not node.get("position"):
        # 自动分配位置
        default_position = {
          "x": 100 + (i % 2) * 300,  # 两列布局
          "y": 100 + (i // 2) * 150
        }
        node["position"] = default_position
        print(f"  - 为节点 '{node.get('id')}' 添加默认位置: {default_position}")
    print(f"所有节点位置检查完成！")

        print(f"配置文件读取成功:")
        print(f"  - 节点数: {len(graph_data.get('nodes', []))}")
        print(f"  - 边数: {len(graph_data.get('edges', []))}")

        # 确认导入
        confirm = input("\n确认导入配置? (y/n): ").strip().lower()
        if confirm != "y":
            print("操作已取消")
            return

        # 保存配置
        print("正在保存配置...")
        agent.graph_definition = graph_data
        await agent.save()

        # 验证保存结果
        updated_agent = await Agent.get(id=agent.id)
        if updated_agent.graph_definition:
            print(f"\n✅ 配置导入成功！")
            print(f"   节点数: {len(updated_agent.graph_definition.get('nodes', []))}")
            print(f"   边数: {len(updated_agent.graph_definition.get('edges', []))}")
        else:
            print("\n❌ 配置导入失败: graph_definition 仍然是 None")

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭数据库连接
        try:
            await Tortoise.close_connections()
        except:
            pass


async def list_agents():
    """列出所有智能体"""
    try:
        from base.plugins.agent.models.agent import Agent
        from base.common.database import init_db
        from tortoise import Tortoise

        await init_db()

        print("所有智能体:")
        print("-" * 80)
        agents = await Agent.all()
        if not agents:
            print("没有找到智能体")
            return

        for agent in agents:
            has_graph = "✅" if agent.graph_definition else "❌"
            graph_info = ""
            if agent.graph_definition:
                nodes = len(agent.graph_definition.get("nodes", []))
                edges = len(agent.graph_definition.get("edges", []))
                graph_info = f" (节点:{nodes}, 边:{edges})"
            print(f"ID: {agent.id:2d} | {has_graph} | {agent.name[:20]:20} | {agent.description or '无描述'}{graph_info}")
        print("-" * 80)

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await Tortoise.close_connections()
        except:
            pass


def print_menu():
    """打印菜单"""
    print("\n" + "=" * 50)
    print("智能体配置管理工具")
    print("=" * 50)
    print("1. 列出所有智能体")
    print("2. 导入配置到指定智能体")
    print("0. 退出")
    print("=" * 50)


if __name__ == "__main__":
    while True:
        print_menu()
        choice = input("\n请选择操作 (0-2): ").strip()

        if choice == "0":
            print("再见！")
            break
        elif choice == "1":
            asyncio.run(list_agents())
        elif choice == "2":
            asyncio.run(import_agent_config())
        else:
            print("无效选择，请重新输入")

        input("\n按 Enter 继续...")
