import os
import json
import logging
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
from base.common.logging_config import register_exceptions_with_logging
from base.plugins import plugin_manager
import asyncio

# 配置日志 - 使用 Loguru 进行完整的日志配置
from base.common.log import setup_logging
setup_logging()

# 禁用websockets.client的调试日志
logging.getLogger('websockets.client').setLevel(logging.WARNING)


def register_audit_handlers():
    """注册审计事件处理器（在应用创建时调用，确保每个进程都注册）"""
    try:
        import base.plugins.audit.services.orm_event_service
        from base.plugins.audit.services.orm_event_service import register_orm_audit_handlers
        from base.plugins.audit.handlers.data_change_handler import DataChangeHandler
        from base.plugins.audit.handlers.login_event_handler import LoginEventHandler
        from base.common.events.event_bus import event_bus
        from base.common.setting import settings

        print(f"[审计] 事件总线实例ID: {id(event_bus)}")
        print(f"[审计] AUDIT_ENABLED: {getattr(settings, 'AUDIT_ENABLED', False)}")
        print(f"[审计] AUDIT_LOG_LOGIN: {getattr(settings, 'AUDIT_LOG_LOGIN', False)}")
        print(f"[审计] AUDIT_LOG_DATA_CHANGES: {getattr(settings, 'AUDIT_LOG_DATA_CHANGES', False)}")

        register_orm_audit_handlers()
        
        data_change_handler = DataChangeHandler()
        event_bus.subscribe("model.created", data_change_handler.handle)
        event_bus.subscribe("model.updated", data_change_handler.handle)
        event_bus.subscribe("model.deleted", data_change_handler.handle)
        print(f"[审计] 数据变更处理器已订阅, is_enabled: {data_change_handler.is_enabled()}")
        handlers_list = event_bus._handlers.get('model.created', []) if hasattr(event_bus, '_handlers') else event_bus.get_handlers('model.created')
        print(f"[审计] model.created 订阅者数量: {len(handlers_list)}")

        login_event_handler = LoginEventHandler()
        event_bus.subscribe("user.login", login_event_handler.handle)
        event_bus.subscribe("user.logout", login_event_handler.handle)
        print(f"[审计] 登录事件处理器已订阅, is_enabled: {login_event_handler.is_enabled()}")
        login_handlers = event_bus._handlers.get('user.login', []) if hasattr(event_bus, '_handlers') else event_bus.get_handlers('user.login')
        print(f"[审计] user.login 订阅者数量: {len(login_handlers)}")

        print("[审计] 事件处理器注册完成")
    except Exception as e:
        print(f"[审计] 注册事件处理器失败: {e}")
        import traceback
        traceback.print_exc()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动逻辑
    print("Application starting up...")

    # 存储后台任务引用，便于清理
    background_tasks = []

    try:
        await init_data()

        # 初始化EventBusAdapter（RabbitMQ事件总线）
        try:
            from base.common.events.event_bus import event_bus
            if hasattr(event_bus, 'initialize'):
                await event_bus.initialize()
                print("EventBusAdapter初始化完成")
        except Exception as e:
            print(f"EventBusAdapter初始化失败(将使用内存模式): {e}")

        # 启动ConsumerWorker
        try:
            from base.common.events.event_bus import event_bus
            from base.common.events.consumer_worker import ConsumerWorker
            if hasattr(event_bus, 'is_rabbitmq_available') and event_bus.is_rabbitmq_available():
                consumer_worker = ConsumerWorker(event_bus)
                await consumer_worker.start()
                app.state.consumer_worker = consumer_worker
                event_bus._consumer_worker = consumer_worker
                print("ConsumerWorker已启动")
            else:
                app.state.consumer_worker = None
                print("ConsumerWorker未启动(RabbitMQ不可用)")
        except Exception as e:
            print(f"ConsumerWorker启动失败: {e}")
            app.state.consumer_worker = None

        # 审计事件处理器已在 init_app 中注册

        # 初始化插件系统
        plugin_manager.set_app(app)
        await plugin_manager.load_enabled_plugins()
        await plugin_manager.startup()
        print("插件系统初始化完成")

        # 启动订单过期检查定时任务
        task1 = asyncio.create_task(cancel_expired_orders_task())
        background_tasks.append(task1)
        print("订单过期检查定时任务已启动")

        # 启动会员数据更新定时任务
        task2 = asyncio.create_task(update_membership_data_task())
        background_tasks.append(task2)
        print("会员数据更新定时任务已启动（每10分钟）")

        # 启动 Prometheus 推送工作器
        if getattr(settings, 'PROMETHEUS_PUSH_ENABLED', False):
            try:
                from base.common.prometheus import start_push_worker
                task3 = asyncio.create_task(start_push_worker())
                background_tasks.append(task3)
                print("Prometheus 推送工作器已启动")
            except ImportError as e:
                print(f"无法启动 Prometheus 推送工作器: {e}")
        else:
            print("Prometheus 推送工作器已禁用（PROMETHEUS_PUSH_ENABLED=false）")

        yield

    finally:
        # 清理逻辑
        print("Application shutting down...")

        # 1. 取消所有后台任务
        print("正在取消后台任务...")
        for task in background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

        # 1.5 停止ConsumerWorker和EventBusAdapter
        try:
            if hasattr(app.state, 'consumer_worker') and app.state.consumer_worker:
                await asyncio.wait_for(app.state.consumer_worker.stop(), timeout=5.0)
                print("ConsumerWorker已停止")
        except Exception as e:
            print(f"停止ConsumerWorker时出错: {e}")
        try:
            from base.common.events.event_bus import event_bus
            if hasattr(event_bus, 'shutdown'):
                await event_bus.shutdown()
                print("EventBusAdapter已关闭")
        except Exception as e:
            print(f"关闭EventBusAdapter时出错: {e}")

        # 2. 关闭插件系统
        print("正在关闭插件系统...")
        try:
            await plugin_manager.shutdown()
        except Exception as e:
            print(f"关闭插件系统时出错: {e}")

        # 3. 关闭数据库连接
        print("正在关闭数据库连接...")
        try:
            await Tortoise.close_connections()
        except Exception as e:
            print(f"关闭数据库连接时出错: {e}")

        # 4. 清理WebSocket连接
        print("正在清理WebSocket连接...")
        try:
            # 获取所有活动连接并关闭
            if hasattr(app, 'state') and hasattr(app.state, 'websockets'):
                for ws in app.state.websockets.copy():
                    try:
                        await ws.close(code=1001, reason="Server shutdown")
                    except Exception:
                        pass
        except Exception as e:
            print(f"清理WebSocket连接时出错: {e}")

        print("所有资源已清理完成，端口9998已释放")


async def cancel_expired_orders_task():
    """
    定时任务：每5分钟检查并取消过期订单
    """
    while True:
        try:
            await asyncio.sleep(300)  # 5分钟 = 300秒

            # # 检查数据库连接状态
            # try:
            #     from tortoise import Tortoise
            #     # 尝试获取默认连接，检查数据库是否连接
            #     await Tortoise.get_connection("postgres")
            # except Exception as conn_error:
            #     print(f"[定时任务] 数据库连接未初始化，跳过订单过期检查: {conn_error}")
            #     continue

            from base.plugins.sales.services.order_service import OrderService
            cancelled_count = await OrderService.cancel_expired_orders()

            if cancelled_count > 0:
                print(f"[定时任务] 已取消 {cancelled_count} 个过期订单")
        except asyncio.CancelledError:
            print("[定时任务] 订单过期检查任务已取消")
            break
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

            # 检查数据库连接状态
            # try:
            #     from tortoise import Tortoise
            #     # 尝试获取默认连接，检查数据库是否连接
            #     await Tortoise.get_connection("postgres")
            # except Exception as conn_error:
            #     print(f"[定时任务] 数据库连接未初始化，跳过会员数据更新: {conn_error}")
            #     continue

            from base.plugins.customer.models.customer_membership import CustomerMembership
            from base.plugins.llm.models.usage import LLMUsageRecord
            from datetime import datetime

            print("\n" + "="*70)
            print(f"[定时任务] 🔔 开始更新会员数据 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*70)

            # 获取所有激活的会员（预加载membership_level关联）
            memberships = await CustomerMembership.filter(is_active=True).select_related('membership_level')
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
                    usage_logs = await LLMUsageRecord.filter(customer_id=membership.customer_id)
                    
                    # 计算总时长（秒）
                    total_seconds = 0
                    for log in usage_logs:
                        # 对于音频相关记录，使用audio_duration
                        if log.audio_duration:
                            total_seconds += log.audio_duration
                        # 对于对话记录，使用start_time和end_time的差值
                        elif log.start_time and log.end_time:
                            duration = (log.end_time - log.start_time).total_seconds()
                            total_seconds += duration
                        # 如果都没有，使用tokens估算（作为备用方案）
                        elif log.tokens:
                            # 假设100 tokens ≈ 1秒（粗略估算）
                            total_seconds += log.tokens / 100
                    
                    used_hours = total_seconds / 3600.0

                    print(f"📋 【使用记录汇总】")
                    print(f"  记录数量: {len(usage_logs)} 条")
                    print(f"  总时长: {total_seconds} 秒")
                    print(f"  💵 实际已用时长: {used_hours:.2f} 小时")

                    if usage_logs:
                        print(f"  📝 最近3条记录:")
                        for log in usage_logs[:3]:
                            duration_str = ""
                            if log.audio_duration:
                                duration_str = f"{log.audio_duration}秒"
                            elif log.start_time and log.end_time:
                                duration = (log.end_time - log.start_time).total_seconds()
                                duration_str = f"{duration:.1f}秒"
                            else:
                                duration_str = f"{log.tokens} tokens"
                            print(f"    - {log.created_at.strftime('%Y-%m-%d %H:%M:%S')}: {log.record_type}, {duration_str}, ${float(log.cost):.4f}")
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

                    # 混合系统信息
                    membership_level = membership.membership_level.level_type if membership.membership_level else "unknown"
                    print(f"  ✅ [会员类别] {membership_level}")
                    print(f"  ✅ [VIP状态] {'是' if membership.is_vip else '否'}")
                    print(f"  ✅ [SVIP状态] {'是' if membership.is_svip else '否'}")
                    print(f"  ✅ [Fibonacci动态等级] Lv{membership.level}")

                    # Fibonacci等级验证
                    from base.plugins.customer.services.membership_service import fibonacci_service
                    expected_level = fibonacci_service.get_level_from_hours(total_hours)
                    if membership.level == expected_level:
                        print(f"  ✅ [等级正确] Lv{membership.level}")
                    else:
                        print(f"  ⚠️  [等级异常] 当前Lv{membership.level}, 应该Lv{expected_level}")
                    #     print(f"  ⚠️  [等级异常] 当前Lv{membership.level}, 应该Lv{expected_level}")

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

        except asyncio.CancelledError:
            print("[定时任务] 会员数据更新任务已取消")
            break
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

    # 注册监控功能
    setup_monitoring(app)

    # 注册中间件、路由和异常处理
    register_exceptions_with_logging(app)  # 使用带详细日志的异常处理器
    register_middlewares(app)
    
    # 注册审计事件处理器（在应用创建时调用，确保每个进程都注册）
    register_audit_handlers()

    # 使用自动路由注册机制
    register_routers(app)

    # 手动注册WebSocket路由（绕过plugin_manager的缓存问题）
    try:
        from base.plugins.llm.api.v1 import voice_websocket
        app.include_router(voice_websocket.voice_websocket_router, prefix="/v1/llm")
        print("[手动注册] WebSocket路由已注册: /v1/llm/voice/translation/streaming")
    except ImportError as e:
        print(f"[警告] 无法导入voice_websocket: {e}")

    # 手动注册 mail WebSocket 路由（消息实时推送）
    try:
        from base.plugins.mail.api.v1.ws_router import ws_router
        app.include_router(ws_router, prefix="/v1/mail")
        print("[手动注册] WebSocket路由已注册: /v1/mail/ws")
    except ImportError as e:
        print(f"[警告] 无法导入 mail ws_router: {e}")

    # 注册事件系统API路由
    try:
        from base.common.events.api import events_api_router
        app.include_router(events_api_router)
        print("[手动注册] 事件系统API路由已注册: /v1/events/")
    except ImportError as e:
        print(f"[警告] 无法导入事件系统API路由: {e}")
    
    return app


def setup_monitoring(app: FastAPI):
    """设置监控功能"""
    
    # 注册健康检查端点
    try:
        from base.common.health import router as health_router
        app.include_router(health_router, prefix="/health")
        print("[监控] 健康检查端点已注册: /health")
    except ImportError as e:
        print(f"[警告] 无法导入健康检查模块: {e}")
    
    # 注册Prometheus中间件和指标端点
    if getattr(settings, 'PROMETHEUS_ENABLED', False):
        try:
            from base.common.prometheus import PrometheusMiddleware, metrics_endpoint
            app.add_middleware(PrometheusMiddleware)
            app.add_api_route("/metrics", metrics_endpoint, methods=["GET"])
            print("[监控] Prometheus监控已启用: /metrics")
        except ImportError as e:
            print(f"[警告] 无法导入Prometheus模块: {e}")
    
    # 初始化Jaeger分布式追踪
    if getattr(settings, 'JAEGER_ENABLED', False):
        try:
            from base.common.tracing import setup_jaeger, instrument_app
            setup_jaeger()
            instrument_app(app)
            print(f"[监控] Jaeger追踪已启用: {settings.JAEGER_HOST}:{settings.JAEGER_PORT}")
        except ImportError as e:
            print(f"[警告] 无法导入Jaeger模块: {e}")
