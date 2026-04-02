"""规则版本管理模块 - 管理平台规则版本"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from app.core.database import SessionLocal
from app.models.models import PlatformComplianceRule
from app.rules.dynamic.rule_cache import clear_cache as clear_rule_cache
from app.rules.dynamic.rule_cache import get_cached_version, set_cached_version
from app.rules.dynamic.rule_loader import _get_available_platforms

logger = logging.getLogger(__name__)

# YAML 规则文件目录
RULES_DIR = Path(__file__).parent.parent / "local"

# 内存中的版本号存储（用于 increment_version）
_version_store: Dict[str, int] = {}


def _get_yaml_version(platform: str) -> int:
    """
    从 YAML 文件读取版本号

    Args:
        platform: 平台名称

    Returns:
        版本号，默认为 1
    """
    yaml_path = RULES_DIR / f"{platform.lower()}.yaml"

    if not yaml_path.exists():
        return 1

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        version = data.get("version", 1) if data else 1
        return int(version) if version else 1

    except Exception as e:
        logger.error(f"读取 YAML 版本失败: {yaml_path}, error={e}")
        return 1


def _get_db_version(platform: str) -> int:
    """
    从数据库获取版本号（基于规则数量或最大ID）

    由于数据库没有专门的版本表，我们使用规则的最大 ID 作为版本标识

    Args:
        platform: 平台名称

    Returns:
        版本号（规则最大ID），无规则返回 0
    """
    db = SessionLocal()
    try:
        # 使用规则的最大 ID 作为数据库版本标识
        max_id_result = (
            db.query(PlatformComplianceRule.id)
            .filter(
                PlatformComplianceRule.platform == platform.lower(),
                PlatformComplianceRule.is_active == True,
            )
            .order_by(PlatformComplianceRule.id.desc())
            .first()
        )

        if max_id_result:
            return max_id_result[0]
        return 0

    except Exception as e:
        logger.error(f"获取数据库版本失败: platform={platform}, error={e}")
        return 0
    finally:
        db.close()


def get_active_version(platform: Optional[str] = None) -> int:
    """
    获取活跃版本号

    读取 YAML 的 version 字段，与 DB 版本取较大值
    同时考虑内存中的递增版本

    Args:
        platform: 平台名称，None 时返回所有平台的最大版本

    Returns:
        版本号
    """
    if platform is None:
        # 返回所有平台的最大版本
        max_version = 1
        for plat in _get_available_platforms():
            ver = get_active_version(plat)
            if ver > max_version:
                max_version = ver
        return max_version

    platform = platform.lower()

    # 检查缓存
    cached = get_cached_version(platform)
    if cached is not None:
        return cached

    # 获取 YAML 版本
    yaml_version = _get_yaml_version(platform)

    # 获取数据库版本
    db_version = _get_db_version(platform)

    # 获取内存版本
    memory_version = _version_store.get(platform, 0)

    # 取最大值
    active_version = max(yaml_version, db_version, memory_version, 1)

    # 更新缓存
    set_cached_version(platform, active_version)

    logger.debug(
        f"版本计算: platform={platform}, yaml={yaml_version}, "
        f"db={db_version}, memory={memory_version}, active={active_version}"
    )

    return active_version


def increment_version(platform: str) -> int:
    """
    递增版本号

    在内存中递增指定平台的版本号
    这用于规则更新后通知相关组件刷新

    Args:
        platform: 平台名称

    Returns:
        递增后的版本号
    """
    platform = platform.lower()

    # 获取当前活跃版本
    current = get_active_version(platform)

    # 递增
    new_version = current + 1
    _version_store[platform] = new_version

    # 更新缓存
    set_cached_version(platform, new_version)

    logger.info(f"版本递增: platform={platform}, {current} -> {new_version}")

    return new_version


def get_version_info() -> Dict[str, Any]:
    """
    获取所有平台的版本信息

    Returns:
        版本信息字典: {platform: {yaml_version, db_version, active_version}}
    """
    result = {}

    for platform in _get_available_platforms():
        yaml_version = _get_yaml_version(platform)
        db_version = _get_db_version(platform)
        memory_version = _version_store.get(platform, 0)
        active_version = max(yaml_version, db_version, memory_version, 1)

        result[platform] = {
            "yaml_version": yaml_version,
            "db_version": db_version,
            "memory_version": memory_version,
            "active_version": active_version,
        }

    return result


def reset_version(platform: Optional[str] = None) -> None:
    """
    重置版本号

    Args:
        platform: 平台名称，None 表示重置所有平台
    """
    if platform:
        platform = platform.lower()
        if platform in _version_store:
            del _version_store[platform]
        clear_rule_cache(platform)
        logger.info(f"版本已重置: platform={platform}")
    else:
        _version_store.clear()
        clear_rule_cache()
        logger.info("所有版本已重置")
