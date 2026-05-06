from typing import Dict, List, Callable, Any
from collections import defaultdict
from loguru import logger

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
    
    def subscribe(self, event_name: str, handler: Callable):
        self._handlers[event_name].append(handler)
        logger.debug(f"订阅事件: {event_name}, 处理器: {handler.__name__}")
    
    def unsubscribe(self, event_name: str, handler: Callable):
        if event_name in self._handlers:
            try:
                self._handlers[event_name].remove(handler)
                logger.debug(f"取消订阅事件: {event_name}, 处理器: {handler.__name__}")
            except ValueError:
                pass
    
    async def publish(self, event_name: str, **kwargs):
        handlers = self._handlers.get(event_name, [])
        if not handlers:
            logger.debug(f"发布事件: {event_name}, 没有订阅者, 事件总线实例ID: {id(self)}")
            return
        
        logger.info(f"发布事件: {event_name}, 处理器数量: {len(handlers)}, 参数: {list(kwargs.keys())}, 事件总线实例ID: {id(self)}")
        
        for handler in handlers:
            try:
                logger.debug(f"执行处理器: {handler.__name__}")
                await handler(event_name=event_name, **kwargs)
                logger.debug(f"处理器 {handler.__name__} 执行成功")
            except Exception as e:
                logger.error(f"事件 {event_name} 处理失败: {e}", exc_info=True)

# 全局事件总线实例
event_bus = EventBus()
print(f"[EventBus] 创建全局事件总线实例: {id(event_bus)}")


