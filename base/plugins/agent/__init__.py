"""
Agent Development Base Plugin
"""

from .api.v1 import dialog_flow

async def on_enable(app):
    """Enable plugin"""
    return True

async def on_disable():
    """Disable plugin"""
    return True

async def on_startup():
    """Startup hook"""
    pass

async def on_shutdown():
    """Shutdown hook"""
    pass