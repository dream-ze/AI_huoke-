import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional

import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# 缓存key前缀
CACHE_PREFIX = "zhk_cache:"


def get_redis_client() -> redis.Redis:
    """获取Redis客户端实例"""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _generate_cache_key(*args, **kwargs) -> str:
    """生成缓存key的MD5哈希值

    Args:
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        str: MD5哈希字符串
    """
    key_data = json.dumps({"args": str(args), "kwargs": str(kwargs)}, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key_data.encode()).hexdigest()


def cache(ttl: int = 3600, prefix: str = ""):
    """缓存装饰器

    为函数结果添加Redis缓存支持，自动处理缓存读写和异常情况。

    Args:
        ttl: 缓存过期时间（秒），默认1小时
        prefix: 缓存key前缀，默认使用函数名

    Returns:
        装饰器函数

    Usage:
        @cache(ttl=1800, prefix="user_info")
        def get_user_info(user_id: int):
            # 数据库查询...
            return user_data

        # 手动清除缓存
        get_user_info.invalidate(user_id=123)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            redis_client = get_redis_client()
            if not redis_client:
                # Redis不可用时直接执行原函数
                return func(*args, **kwargs)

            # 生成缓存key（跳过self/cls参数）
            func_args = args[1:] if args and hasattr(args[0], "__class__") else args
            cache_key_hash = _generate_cache_key(*func_args, **kwargs)
            key = f"{CACHE_PREFIX}{prefix or func.__name__}:{cache_key_hash}"

            # 尝试从缓存读取
            try:
                cached = redis_client.get(key)
                if cached:
                    logger.debug(f"缓存命中: {key}")
                    return json.loads(cached)
            except (json.JSONDecodeError, redis.RedisError) as e:
                logger.warning(f"缓存读取失败: {e}")
            except Exception as e:
                logger.warning(f"缓存读取异常: {e}")

            # 执行原函数
            result = func(*args, **kwargs)

            # 写入缓存
            try:
                if result is not None:
                    redis_client.setex(key, ttl, json.dumps(result, default=str, ensure_ascii=False))
                    logger.debug(f"缓存写入: {key}, TTL={ttl}s")
            except (TypeError, redis.RedisError) as e:
                logger.warning(f"缓存写入失败: {e}")
            except Exception as e:
                logger.warning(f"缓存写入异常: {e}")

            return result

        def invalidate(*args, **kwargs) -> bool:
            """清除指定参数对应的缓存

            Args:
                *args, **kwargs: 与原函数调用相同的参数

            Returns:
                bool: 是否成功删除
            """
            redis_client = get_redis_client()
            if not redis_client:
                return False

            try:
                func_args = args[1:] if args and hasattr(args[0], "__class__") else args
                cache_key_hash = _generate_cache_key(*func_args, **kwargs)
                key = f"{CACHE_PREFIX}{prefix or func.__name__}:{cache_key_hash}"
                deleted = redis_client.delete(key)
                if deleted:
                    logger.debug(f"缓存清除: {key}")
                return bool(deleted)
            except redis.RedisError as e:
                logger.warning(f"缓存清除失败: {e}")
                return False

        wrapper.invalidate = invalidate
        wrapper.cache_prefix = f"{CACHE_PREFIX}{prefix or func.__name__}:"
        return wrapper

    return decorator


def invalidate_pattern(pattern: str) -> int:
    """按模式批量清除缓存

    Args:
        pattern: 缓存key模式（不含前缀），支持通配符*

    Returns:
        int: 删除的缓存数量

    Usage:
        # 清除所有用户相关缓存
        invalidate_pattern("user_info:*")

        # 清除特定用户的所有缓存
        invalidate_pattern("*:user_123")
    """
    redis_client = get_redis_client()
    if not redis_client:
        return 0

    full_pattern = f"{CACHE_PREFIX}{pattern}*"
    try:
        keys = redis_client.keys(full_pattern)
        if keys:
            deleted = redis_client.delete(*keys)
            logger.info(f"批量清除缓存: {deleted}个key, pattern={full_pattern}")
            return deleted
        return 0
    except redis.RedisError as e:
        logger.warning(f"批量清除缓存失败: {e}")
        return 0


def get_cache_stats() -> dict:
    """获取缓存统计信息

    Returns:
        dict: 包含缓存key数量、内存使用等信息
    """
    redis_client = get_redis_client()
    if not redis_client:
        return {"available": False}

    try:
        info = redis_client.info("memory")
        keys = redis_client.keys(f"{CACHE_PREFIX}*")
        return {
            "available": True,
            "cache_keys": len(keys),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": redis_client.client_count(),
        }
    except redis.RedisError as e:
        logger.warning(f"获取缓存统计失败: {e}")
        return {"available": False, "error": str(e)}
