"""
Redis缓存工具类
"""
from typing import Optional, Any, List
import json
from .setting import settings

# 可选导入Redis，避免没有安装时导入失败
try:
    import redis.asyncio as redis
except ImportError:
    redis = None
    print("Redis模块未安装，将禁用Redis缓存功能")


class RedisCache:
    """Redis缓存单例类"""
    _instance: Optional["RedisCache"] = None
    _client: Optional[Any] = None
    _enabled: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_instance(cls) -> "RedisCache":
        """获取缓存实例"""
        if cls._instance is None:
            cls._instance = cls()
        if settings.REDIS_ENABLED and cls._instance._client is None:
            await cls._instance.connect()
        return cls._instance

    @classmethod
    def is_enabled(cls) -> bool:
        """检查Redis是否启用且连接成功"""
        return cls._instance is not None and cls._instance._client is not None

    async def connect(self):
        """
        连接Redis
        """
        if not settings.REDIS_ENABLED or redis is None:
            print("Redis已禁用或模块未安装，使用数据库直接查询")
            return

        password = settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None
        try:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=password,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            # 测试连接
            await self._client.ping()
            self._enabled = True
            print("Redis连接成功")
        except Exception as e:
            print(f"Redis连接失败: {e}，将使用数据库直接查询")
            self._client = None
            self._enabled = False

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回None
        """
        if not self._client:
            return None
        try:
            data = await self._client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间(秒)，默认1小时

        Returns:
            是否成功
        """
        if not self._client:
            return False
        try:
            await self._client.set(key, json.dumps(value, ensure_ascii=False), ex=expire)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        if not self._client:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception:
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        根据模式删除缓存

        Args:
            pattern: 匹配模式，如 "user:*"

        Returns:
            删除的键数量
        """
        if not self._client:
            return 0
        try:
            keys = await self._client.keys(pattern)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception:
            return 0

    async def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        if not self._client:
            return False
        try:
            return await self._client.exists(key) > 0
        except Exception:
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间

        Args:
            key: 缓存键
            seconds: 过期秒数

        Returns:
            是否成功
        """
        if not self._client:
            return False
        try:
            return await self._client.expire(key, seconds)
        except Exception:
            return False

    async def get_list(self, key: str) -> List[Any]:
        """
        获取列表缓存

        Args:
            key: 缓存键

        Returns:
            列表值
        """
        if not self._client:
            return []
        try:
            data = await self._client.lrange(key, 0, -1)
            return [json.loads(item) for item in data] if data else []
        except Exception:
            return []

    async def push_list(self, key: str, *values: Any, expire: int = 3600) -> bool:
        """
        向列表添加值

        Args:
            key: 缓存键
            values: 要添加的值
            expire: 过期时间

        Returns:
            是否成功
        """
        if not self._client:
            return False
        try:
            serialized = [json.dumps(v, ensure_ascii=False) for v in values]
            await self._client.rpush(key, *serialized)
            await self._client.expire(key, expire)
            return True
        except Exception:
            return False

    async def get_hash(self, key: str, field: str = None) -> Optional[Any]:
        """
        获取哈希缓存

        Args:
            key: 缓存键
            field: 哈希字段，为None时获取所有

        Returns:
            哈希值
        """
        if not self._client:
            return None
        try:
            if field:
                data = await self._client.hget(key, field)
                return json.loads(data) if data else None
            else:
                data = await self._client.hgetall(key)
                return {k: json.loads(v) for k, v in data.items()} if data else None
        except Exception:
            return None

    async def set_hash(self, key: str, mapping: dict, expire: int = 3600) -> bool:
        """
        设置哈希缓存

        Args:
            key: 缓存键
            mapping: 哈希映射
            expire: 过期时间

        Returns:
            是否成功
        """
        if not self._client:
            return False
        try:
            serialized = {k: json.dumps(v, ensure_ascii=False) for k, v in mapping.items()}
            await self._client.hset(key, mapping=serialized)
            await self._client.expire(key, expire)
            return True
        except Exception:
            return False


# 便捷函数
async def get_cache() -> RedisCache:
    """获取缓存实例的便捷函数"""
    return await RedisCache.get_instance()
