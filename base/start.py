import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from tortoise import Tortoise
from base.common import database
from base.common.setting import settings
from base.common.database import init_data
from base.common.middleware import register_middlewares
from base.common.exceptions import register_exceptions
from base.common.router import register_routers
from base.common.json_encoder import DateTimeEncoder
from base.plugins import plugin_manager
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动逻辑
    print("Application starting up...")
    try:
        await init_data()

        # 初始化插件系统
        plugin_manager.set_app(app)
        await plugin_manager.load_enabled_plugins()
        await plugin_manager.startup()
        print("插件系统初始化完成")

        # 启动订单过期检查定时任务
        task1 = asyncio.create_task(cancel_expired_orders_task())
        print("订单过期检查定时任务已启动")

        # 启动会员数据更新定时任务
        task2 = asyncio.create_task(update_membership_data_task())
        print("会员数据更新定时任务已启动（每10分钟）")

        yield

        # 关闭插件系统
        await plugin_manager.shutdown()
        await Tortoise.close_connections()
    finally:
        # 确保所有资源正确关闭
        print("Application shutting down...")


async def cancel_expired_orders_task():
    """
    定时任务：每5分钟检查并取消过期订单
    """
    while True:
        try:
            await asyncio.sleep(300)  # 5分钟 = 300秒

            from base.plugins.order.services.order_service import OrderService
            cancelled_count = await OrderService.cancel_expired_orders()

            if cancelled_count > 0:
                print(f"[定时任务] 已取消 {cancelled_count} 个过期订单")
        except Exception as e:
            print(f"[定时任务] 订单过期检查失败: {e}")
            import traceback
            traceback.print_exc()


async def update_membership_data_task():
    """
    定时任务：每10分钟更新会员数据
    - 重新计算已用时长（从使用记录汇总）
    - 更新剩余时长
    - 检查并更新过期状态
    - 停用剩余时长为0的会员
    """
    while True:
        try:
            await asyncio.sleep(600)  # 10分钟 = 600秒

            from base.plugins.customer.models.customer_membership import CustomerMembership
            from base.plugins.customer.models.usage_log import UsageLog
            from datetime import datetime

            print("\n" + "="*70)
            print(f"[定时任务] 🔔 开始更新会员数据 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*70)

            # 获取所有激活的会员
            memberships = await CustomerMembership.filter(is_active=True)
            print(f"[信息] 找到 {len(memberships)} 个激活的会员\n")

            if not memberships:
                print("[信息] 没有激活的会员，跳过更新")
                continue

            updated_count = 0
            deactivated_count = 0
            skipped_count = 0
            error_count = 0

            for idx, membership in enumerate(memberships, 1):
                try:
                    print(f"{'─'*70}")
                    print(f"[{idx}/{len(memberships)}] 💎 客户 {membership.customer_id} - 会员数据更新")
                    print(f"{'─'*70}")

                    # ===== 关键指标展示 =====
                    print(f"📊 【当前会员数据】")
                    print(f"  💰 充值总时长: {membership.total_hours} 小时")
                    print(f"  ⏱️  已用时长: {float(membership.used_hours):.2f} 小时")
                    print(f"  ⏳ 剩余时长: {float(membership.remaining_hours):.2f} 小时")
                    print(f"  🏆 Fibonacci等级: Lv{membership.level}")
                    print(f"  📅 过期时间: {membership.expire_time}")
                    print(f"  ✅ 激活状态: {'是' if membership.is_active else '否'}")
                    print()

                    # 从使用记录计算实际已用时长
                    usage_logs = await UsageLog.filter(customer_id=membership.customer_id)
                    total_seconds = sum(log.duration_seconds for log in usage_logs)
                    used_hours = total_seconds / 3600.0

                    print(f"📋 【使用记录汇总】")
                    print(f"  记录数量: {len(usage_logs)} 条")
                    print(f"  总使用秒数: {total_seconds} 秒")
                    print(f"  💵 实际已用时长: {used_hours:.2f} 小时")

                    if usage_logs:
                        print(f"  📝 最近3条记录:")
                        for log in usage_logs[:3]:
                            hours = log.duration_seconds / 3600.0
                            print(f"    - {log.created_at.strftime('%Y-%m-%d %H:%M:%S')}: {log.duration_seconds}秒 ({hours:.2f}小时)")
                    print()

                    # 计算剩余时长
                    total_hours = membership.total_hours
                    old_remaining = float(membership.remaining_hours)
                    new_remaining = total_hours - used_hours
                    if new_remaining < 0:
                        new_remaining = 0

                    print(f"🧮 【时长计算】")
                    print(f"  📐 公式: 剩余时长 = 充值总时长 - 已用时长")
                    print(f"  📊 充值总时长: {total_hours} 小时")
                    print(f"  💵 已用时长: {used_hours:.2f} 小时")
                    print(f"  📈 新剩余时长: {new_remaining:.2f} 小时")
                    print(f"  📉 原剩余时长: {old_remaining:.2f} 小时")
                    print(f"  🔄 变化幅度: {new_remaining - old_remaining:+.2f} 小时")
                    print()

                    # 检查是否需要更新
                    if abs(new_remaining - old_remaining) > 0.01:
                        membership.used_hours = used_hours
                        membership.remaining_hours = new_remaining
                        await membership.save()
                        print(f"  ✅ [已更新] 会员数据已更新到数据库")
                        updated_count += 1
                    else:
                        print(f"  ⏭️  [跳过] 无需更新（差异 < 0.01小时）")
                        skipped_count += 1

                    # 检查是否需要停用（剩余时长为0）
                    if new_remaining <= 0:
                        membership.is_active = False
                        await membership.save()
                        print(f"  ⛔ [已停用] 剩余时长已用完，会员已停用")
                        deactivated_count += 1

                    # 检查是否过期
                    if membership.is_expired:
                        print(f"  ⚠️  [已过期] 会员已过期")
                    else:
                        print(f"  ✅ [有效期] 会员在有效期内")

                    # Fibonacci等级验证
                    from base.plugins.customer.services.membership_service import fibonacci_service
                    expected_level = fibonacci_service.get_level_from_hours(total_hours)
                    if membership.level == expected_level:
                        print(f"  ✅ [等级正确] Lv{membership.level}")
                    else:
                        print(f"  ⚠️  [等级异常] 当前Lv{membership.level}, 应该Lv{expected_level}")

                except Exception as e:
                    print(f"  ❌ [错误] 处理失败: {e}")
                    error_count += 1
                    import traceback
                    traceback.print_exc()

                print()  # 空行分隔

            # 输出统计信息
            print("="*70)
            print(f"[定时任务] ✅ 执行完成")
            print(f"  处理会员总数: {len(memberships)}")
            print(f"  更新会员数: {updated_count}")
            print(f"  跳过会员数: {skipped_count}")
            print(f"  停用会员数: {deactivated_count}")
            print(f"  错误数量: {error_count}")
            print("="*70 + "\n")

        except Exception as e:
            print(f"\n[定时任务] ❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()

def init_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        json_dumps=lambda data, **kwargs: json.dumps(data, **kwargs, cls=DateTimeEncoder, ensure_ascii=False)
    )

    # 设置服务器 URL（用于文档页面的 "Try it out" 功能）
    app.state.servers = [
        {"url": "http://127.0.0.1:9998/api", "description": "本地开发服务器"},
    ]

    # 立即保存并替换 openapi 方法（在路由注册之前）
    _original_openapi = app.openapi

    def custom_openapi():
        import sys
        # 总是重新生成 schema（包含所有已注册的路由）
        openapi_schema = _original_openapi()

        # 设置服务器 URL
        if hasattr(app.state, 'servers'):
            openapi_schema["servers"] = app.state.servers

        paths = openapi_schema.get('paths', {})
        customer_auth_count = len([p for p in paths.keys() if 'customer/auth' in p])
        print(f"[custom_openapi] Generated schema with {customer_auth_count} customer/auth paths, total {len(paths)} paths", file=sys.stderr, flush=True)
        return openapi_schema

    app.openapi = custom_openapi

    # 注册中间件、路由和异常处理
    register_exceptions(app)
    register_middlewares(app)

    # 使用自动路由注册机制
    register_routers(app)

    return app
