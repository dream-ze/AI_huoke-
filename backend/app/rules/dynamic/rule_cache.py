"""规则缓存模块 - 提供规则缓存的存取和管理功能"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 缓存TTL配置（秒）
_CACHE_TTL_SECONDS = 300  # 5分钟缓存

# 内存缓存结构
# _RULE_CACHE: {
#   "rules": {platform: {"data": [...], "expires_at": timestamp}},
#   "versions": {platform: {"data": int, "expires_at": timestamp}},
# }
_RULE_CACHE: Dict[str, Dict[str, Any]] = {
    "rules": {},
    "versions": {},
}


def get_rule_cache() -> Dict[str, Dict[str, Any]]:
    """获取完整缓存对象（用于调试）"""
    return _RULE_CACHE


def get_cached_rules(platform: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取缓存的平台规则

    Args:
        platform: 平台名称

    Returns:
        规则列表，如缓存过期或不存在返回None
    """
    cache_key = platform.lower()
    current_time = time.time()

    if cache_key in _RULE_CACHE["rules"]:
        cached = _RULE_CACHE["rules"][cache_key]
        if cached["expires_at"] > current_time:
            logger.debug(f"缓存命中: platform={cache_key}")
            return cached["data"]

    return None


def set_cached_rules(platform: str, rules: List[Dict[str, Any]]) -> None:
    """
    设置平台规则缓存

    Args:
        platform: 平台名称
        rules: 规则列表
    """
    cache_key = platform.lower()
    current_time = time.time()

    _RULE_CACHE["rules"][cache_key] = {
        "data": rules,
        "expires_at": current_time + _CACHE_TTL_SECONDS,
    }
    logger.debug(f"缓存已更新: platform={cache_key}, count={len(rules)}")


def get_cached_version(platform: str) -> Optional[int]:
    """
    获取缓存的版本号

    Args:
        platform: 平台名称

    Returns:
        版本号，如缓存过期或不存在返回None
    """
    cache_key = platform.lower()
    current_time = time.time()

    if cache_key in _RULE_CACHE["versions"]:
        cached = _RULE_CACHE["versions"][cache_key]
        if cached["expires_at"] > current_time:
            return cached["data"]

    return None


def set_cached_version(platform: str, version: int) -> None:
    """
    设置平台版本号缓存

    Args:
        platform: 平台名称
        version: 版本号
    """
    cache_key = platform.lower()
    current_time = time.time()

    _RULE_CACHE["versions"][cache_key] = {
        "data": version,
        "expires_at": current_time + _CACHE_TTL_SECONDS,
    }


def clear_cache(platform: Optional[str] = None) -> None:
    """
    清除缓存

    Args:
        platform: 指定平台则只清除该平台缓存，None清除全部
    """
    if platform:
        cache_key = platform.lower()
        if cache_key in _RULE_CACHE["rules"]:
            del _RULE_CACHE["rules"][cache_key]
        if cache_key in _RULE_CACHE["versions"]:
            del _RULE_CACHE["versions"][cache_key]
        logger.info(f"已清除缓存: platform={cache_key}")
    else:
        _RULE_CACHE["rules"].clear()
        _RULE_CACHE["versions"].clear()
        logger.info("已清除所有缓存")


def get_cache_stats() -> Dict[str, Any]:
    """
    获取缓存统计信息

    Returns:
        缓存统计信息
    """
    current_time = time.time()

    rules_stats = {}
    for platform, cached in _RULE_CACHE["rules"].items():
        rules_stats[platform] = {
            "count": len(cached["data"]),
            "expires_in": max(0, int(cached["expires_at"] - current_time)),
        }

    versions_stats = {}
    for platform, cached in _RULE_CACHE["versions"].items():
        versions_stats[platform] = {
            "version": cached["data"],
            "expires_in": max(0, int(cached["expires_at"] - current_time)),
        }

    return {
        "rules": rules_stats,
        "versions": versions_stats,
        "ttl_seconds": _CACHE_TTL_SECONDS,
    }
