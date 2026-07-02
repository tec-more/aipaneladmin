from fastapi import FastAPI
from base.common.log import log

pass


async def on_enable(app: FastAPI) -> bool:
    log.info("财务管理插件正在启用...")
    return True


async def on_disable() -> bool:
    log.info("财务管理插件正在禁用...")
    return True


async def on_startup() -> None:
    log.info("财务管理插件启动")
    try:
        from base.plugins.finance.services.account_service import AccountService
        await AccountService.initialize_default_accounts()
        log.info("默认会计科目初始化完成")
    except Exception as e:
        log.warning(f"默认会计科目初始化失败: {e}")


async def on_shutdown() -> None:
    log.info("财务管理插件关闭")


__version__ = "1.0.0"
__plugin_name__ = "finance"

__all__ = ["on_enable", "on_disable", "on_startup", "on_shutdown", "finance_router"]