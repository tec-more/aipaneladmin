"""
全链路审计模块
"""


async def on_enable(plugin_config: dict = None):
    """
    插件启用钩子
    """
    print("[Audit] 全链路审计模块已启用")


async def on_disable(plugin_config: dict = None):
    """
    插件禁用钩子
    """
    print("[Audit] 全链路审计模块已禁用")


async def on_startup(plugin_config: dict = None):
    """
    插件启动钩子
    """
    print("[Audit] 全链路审计模块已启动")


async def on_shutdown(plugin_config: dict = None):
    """
    插件关闭钩子
    """
    print("[Audit] 全链路审计模块已关闭")
