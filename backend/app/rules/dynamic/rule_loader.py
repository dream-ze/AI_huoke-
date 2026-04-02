"""动态规则加载器 - 从 YAML 文件和数据库加载平台合规规则"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from app.core.database import SessionLocal
from app.models.models import PlatformComplianceRule
from app.rules.dynamic.rule_cache import clear_cache as clear_rule_cache
from app.rules.dynamic.rule_cache import get_cached_rules, set_cached_rules
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# YAML 规则文件目录
RULES_DIR = Path(__file__).parent.parent / "local"


def _load_yaml_rules(platform: str) -> List[Dict[str, Any]]:
    """
    从 YAML 文件加载平台规则

    Args:
        platform: 平台名称 (xiaohongshu/douyin/zhihu)

    Returns:
        规则列表
    """
    yaml_path = RULES_DIR / f"{platform.lower()}.yaml"

    if not yaml_path.exists():
        logger.warning(f"YAML 规则文件不存在: {yaml_path}")
        return []

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "rules" not in data:
            logger.warning(f"YAML 文件格式无效或无规则: {yaml_path}")
            return []

        rules = data.get("rules", [])
        # 添加来源标记
        for rule in rules:
            rule["source"] = "yaml"

        logger.info(f"从 YAML 加载规则: platform={platform}, count={len(rules)}")
        return rules

    except yaml.YAMLError as e:
        logger.error(f"YAML 解析错误: {yaml_path}, error={e}")
        return []
    except Exception as e:
        logger.error(f"读取 YAML 文件失败: {yaml_path}, error={e}")
        return []


def _load_db_rules(db: Session, platform: str) -> List[Dict[str, Any]]:
    """
    从数据库加载平台规则

    Args:
        db: 数据库会话
        platform: 平台名称

    Returns:
        规则列表
    """
    try:
        rules = (
            db.query(PlatformComplianceRule)
            .filter(
                PlatformComplianceRule.platform == platform.lower(),
                PlatformComplianceRule.is_active == True,
            )
            .all()
        )

        result = [
            {
                "id": r.id,
                "keyword_or_pattern": r.keyword_or_pattern,
                "risk_level": r.risk_level,
                "suggestion": r.suggestion,
                "rule_category": r.rule_category,
                "description": r.description,
                "source": "database",
            }
            for r in rules
        ]

        logger.info(f"从数据库加载规则: platform={platform}, count={len(result)}")
        return result

    except Exception as e:
        logger.error(f"数据库查询失败: platform={platform}, error={e}")
        return []


def _merge_rules(yaml_rules: List[Dict[str, Any]], db_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    合并 YAML 和数据库规则，去重（DB 规则优先）

    Args:
        yaml_rules: YAML 规则列表
        db_rules: 数据库规则列表

    Returns:
        合并后的规则列表
    """
    # 以 keyword_or_pattern 为 key 建立字典
    merged: Dict[str, Dict[str, Any]] = {}

    # 先添加 YAML 规则
    for rule in yaml_rules:
        key = rule.get("keyword_or_pattern", "")
        if key:
            merged[key] = rule

    # DB 规则覆盖同名 YAML 规则
    for rule in db_rules:
        key = rule.get("keyword_or_pattern", "")
        if key:
            merged[key] = rule

    result = list(merged.values())
    logger.debug(f"合并规则: yaml={len(yaml_rules)}, db={len(db_rules)}, merged={len(result)}")
    return result


def load_rules(platform: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    加载平台规则（从 YAML 和数据库，带缓存）

    Args:
        platform: 平台名称，None 表示加载所有平台
        db: 数据库会话，None 时自动创建

    Returns:
        规则字典: {platform: [rule_list]}
    """
    # 确定要加载的平台列表
    platforms_to_load = []
    if platform:
        platforms_to_load = [platform.lower()]
    else:
        # 扫描 YAML 文件确定可用平台
        platforms_to_load = _get_available_platforms()

    result: Dict[str, List[Dict[str, Any]]] = {}
    should_close_db = False

    if db is None:
        db = SessionLocal()
        should_close_db = True

    try:
        for plat in platforms_to_load:
            # 检查缓存
            cached = get_cached_rules(plat)
            if cached is not None:
                result[plat] = cached
                continue

            # 加载 YAML 规则
            yaml_rules = _load_yaml_rules(plat)

            # 加载数据库规则
            db_rules = _load_db_rules(db, plat)

            # 合并规则
            merged_rules = _merge_rules(yaml_rules, db_rules)

            # 更新缓存
            set_cached_rules(plat, merged_rules)

            result[plat] = merged_rules

        return result

    finally:
        if should_close_db:
            db.close()


def load_all_rules(db: Optional[Session] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    加载所有平台规则

    Args:
        db: 数据库会话，None 时自动创建

    Returns:
        规则字典: {platform: [rule_list]}
    """
    return load_rules(platform=None, db=db)


def reload_rules(platform: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    强制刷新缓存并重新加载规则

    Args:
        platform: 平台名称，None 表示刷新所有平台
        db: 数据库会话，None 时自动创建

    Returns:
        重新加载的规则字典
    """
    # 清除缓存
    clear_rule_cache(platform)

    # 重新加载
    return load_rules(platform=platform, db=db)


def _get_available_platforms() -> List[str]:
    """
    获取可用平台列表（基于 YAML 文件）

    Returns:
        平台名称列表
    """
    platforms = []

    if not RULES_DIR.exists():
        logger.warning(f"规则目录不存在: {RULES_DIR}")
        return platforms

    for yaml_file in RULES_DIR.glob("*.yaml"):
        platform_name = yaml_file.stem
        if platform_name:  # 排除空文件名
            platforms.append(platform_name)

    logger.debug(f"可用平台: {platforms}")
    return platforms


def get_platforms() -> List[str]:
    """
    获取所有支持的平台列表

    Returns:
        平台名称列表
    """
    return _get_available_platforms()
