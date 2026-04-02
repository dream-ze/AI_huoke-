"""平台规则服务 - 提供平台合规规则的缓存查询"""

import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from app.models.models import AutoRewriteTemplate, PlatformComplianceRule
from app.rules.dynamic.rule_cache import clear_cache as clear_rule_cache
from app.rules.dynamic.rule_versioning import increment_version
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 缓存配置
_CACHE_TTL_SECONDS = 300  # 5分钟缓存

# 内存缓存
_platform_rules_cache: Dict[str, Dict[str, Any]] = {}  # {platform: {"data": [...], "expires_at": timestamp}}
_rewrite_templates_cache: Dict[str, Dict[str, Any]] = (
    {}
)  # {"all" or category: {"data": [...], "expires_at": timestamp}}

# YAML 规则文件目录
RULES_DIR = Path(__file__).parent.parent / "rules" / "local"


class PlatformRuleService:
    """平台规则服务 - 管理平台合规规则的缓存查询"""

    def __init__(self, db: Session):
        self.db = db

    def get_rules_by_platform(self, platform: str) -> List[Dict[str, Any]]:
        """
        按平台加载规则（带缓存）

        Args:
            platform: 平台名称 (xiaohongshu/douyin/zhihu/weixin)

        Returns:
            规则列表，每条规则包含：keyword_or_pattern, risk_level, suggestion, rule_category
        """
        global _platform_rules_cache

        current_time = time.time()
        cache_key = platform.lower()

        # 检查缓存是否有效
        if cache_key in _platform_rules_cache:
            cached = _platform_rules_cache[cache_key]
            if cached["expires_at"] > current_time:
                return cached["data"]

        # 从数据库加载
        try:
            rules = (
                self.db.query(PlatformComplianceRule)
                .filter(
                    PlatformComplianceRule.platform == cache_key,
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
                }
                for r in rules
            ]

            # 更新缓存
            _platform_rules_cache[cache_key] = {
                "data": result,
                "expires_at": current_time + _CACHE_TTL_SECONDS,
            }

            return result

        except Exception as e:
            logger.warning(f"加载平台规则失败 [platform={platform}]: {e}")
            return []

    def get_rewrite_templates(
        self, category: Optional[str] = None, platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取改写模板（带缓存）

        Args:
            category: 模板分类（承诺类/利率类/资质类），None表示全部
            platform: 适用平台，None表示全部

        Returns:
            模板列表，每条包含：trigger_pattern, safe_alternative, risk_level, platform_scope
        """
        global _rewrite_templates_cache

        current_time = time.time()
        cache_key = f"{category or 'all'}_{platform or 'all'}"

        # 检查缓存
        if cache_key in _rewrite_templates_cache:
            cached = _rewrite_templates_cache[cache_key]
            if cached["expires_at"] > current_time:
                return cached["data"]

        # 从数据库加载
        try:
            query = self.db.query(AutoRewriteTemplate).filter(AutoRewriteTemplate.is_active == True)

            if category:
                query = query.filter(AutoRewriteTemplate.category == category)

            templates = query.all()

            # 按平台过滤
            result = []
            for t in templates:
                # 如果指定了平台，检查平台范围
                if platform and t.platform_scope:
                    allowed_platforms = [p.strip().lower() for p in t.platform_scope.split(",")]
                    if platform.lower() not in allowed_platforms:
                        continue

                result.append(
                    {
                        "id": t.id,
                        "trigger_pattern": t.trigger_pattern,
                        "safe_alternative": t.safe_alternative,
                        "risk_level": t.risk_level,
                        "platform_scope": t.platform_scope,
                        "category": t.category,
                    }
                )

            # 更新缓存
            _rewrite_templates_cache[cache_key] = {
                "data": result,
                "expires_at": current_time + _CACHE_TTL_SECONDS,
            }

            return result

        except Exception as e:
            logger.warning(f"加载改写模板失败: {e}")
            return []

    def clear_cache(self, platform: Optional[str] = None) -> None:
        """
        清除缓存

        Args:
            platform: 指定平台则只清除该平台缓存，None清除全部
        """
        global _platform_rules_cache, _rewrite_templates_cache

        if platform:
            cache_key = platform.lower()
            if cache_key in _platform_rules_cache:
                del _platform_rules_cache[cache_key]
            # 清除相关的模板缓存
            keys_to_remove = [k for k in _rewrite_templates_cache if platform.lower() in k]
            for k in keys_to_remove:
                del _rewrite_templates_cache[k]
        else:
            _platform_rules_cache.clear()
            _rewrite_templates_cache.clear()

        logger.info(f"已清除缓存 [platform={platform or 'all'}]")

    # ========== CRUD 方法 ==========

    def add_platform_rule(
        self,
        platform: str,
        keyword_or_pattern: str,
        risk_level: str = "medium",
        rule_category: Optional[str] = None,
        suggestion: Optional[str] = None,
        description: Optional[str] = None,
    ) -> PlatformComplianceRule:
        """添加平台规则"""
        rule = PlatformComplianceRule(
            platform=platform.lower(),
            keyword_or_pattern=keyword_or_pattern,
            risk_level=risk_level,
            rule_category=rule_category,
            suggestion=suggestion,
            description=description,
        )
        self.db.add(rule)
        self.db.commit()
        self.clear_cache(platform)
        return rule

    def update_platform_rule(self, rule_id: int, **kwargs) -> Optional[PlatformComplianceRule]:
        """更新平台规则"""
        rule = self.db.get(PlatformComplianceRule, rule_id)
        if not rule:
            return None

        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        self.db.commit()
        self.clear_cache(rule.platform)
        return rule

    def delete_platform_rule(self, rule_id: int) -> bool:
        """删除平台规则"""
        rule = self.db.get(PlatformComplianceRule, rule_id)
        if not rule:
            return False

        platform = rule.platform
        self.db.delete(rule)
        self.db.commit()
        self.clear_cache(platform)
        return True

    def add_rewrite_template(
        self,
        trigger_pattern: str,
        safe_alternative: str,
        risk_level: str = "medium",
        category: Optional[str] = None,
        platform_scope: Optional[str] = None,
    ) -> AutoRewriteTemplate:
        """添加改写模板"""
        template = AutoRewriteTemplate(
            trigger_pattern=trigger_pattern,
            safe_alternative=safe_alternative,
            risk_level=risk_level,
            category=category,
            platform_scope=platform_scope,
        )
        self.db.add(template)
        self.db.commit()
        self.clear_cache()
        return template

    def list_platform_rules(
        self, platform: Optional[str] = None, is_active: Optional[bool] = None
    ) -> List[PlatformComplianceRule]:
        """列出平台规则"""
        query = self.db.query(PlatformComplianceRule)

        if platform:
            query = query.filter(PlatformComplianceRule.platform == platform.lower())
        if is_active is not None:
            query = query.filter(PlatformComplianceRule.is_active == is_active)

        return query.all()

    def list_rewrite_templates(
        self, category: Optional[str] = None, is_active: Optional[bool] = None
    ) -> List[AutoRewriteTemplate]:
        """列出改写模板"""
        query = self.db.query(AutoRewriteTemplate)

        if category:
            query = query.filter(AutoRewriteTemplate.category == category)
        if is_active is not None:
            query = query.filter(AutoRewriteTemplate.is_active == is_active)

        return query.all()

    # ========== 增强的 CRUD 方法（用于运营级管理）==========

    def create_rule(
        self,
        platform: str,
        keyword_or_pattern: str,
        risk_level: str,
        suggestion: str,
        rule_category: str,
        description: Optional[str] = None,
    ) -> PlatformComplianceRule:
        """
        创建平台规则

        Args:
            platform: 平台名称
            keyword_or_pattern: 关键词或正则表达式
            risk_level: 风险等级 (high/medium/low)
            suggestion: 修改建议
            rule_category: 规则分类
            description: 规则描述（可选）

        Returns:
            创建的规则对象
        """
        rule = PlatformComplianceRule(
            platform=platform.lower(),
            keyword_or_pattern=keyword_or_pattern,
            risk_level=risk_level,
            suggestion=suggestion,
            rule_category=rule_category,
            description=description,
            is_active=True,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        # 清除缓存并递增版本
        self._invalidate_platform_cache(platform)

        logger.info(f"创建规则成功: id={rule.id}, platform={platform}, keyword={keyword_or_pattern}")
        return rule

    def update_rule(
        self,
        rule_id: int,
        keyword_or_pattern: Optional[str] = None,
        risk_level: Optional[str] = None,
        suggestion: Optional[str] = None,
        rule_category: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[PlatformComplianceRule]:
        """
        更新平台规则

        Args:
            rule_id: 规则ID
            keyword_or_pattern: 关键词或正则表达式（可选）
            risk_level: 风险等级（可选）
            suggestion: 修改建议（可选）
            rule_category: 规则分类（可选）
            description: 规则描述（可选）
            is_active: 是否激活（可选）

        Returns:
            更新后的规则对象，如果不存在返回None
        """
        rule = self.db.get(PlatformComplianceRule, rule_id)
        if not rule:
            return None

        # 记录原平台用于缓存清除
        original_platform = rule.platform

        # 更新字段
        if keyword_or_pattern is not None:
            rule.keyword_or_pattern = keyword_or_pattern
        if risk_level is not None:
            rule.risk_level = risk_level
        if suggestion is not None:
            rule.suggestion = suggestion
        if rule_category is not None:
            rule.rule_category = rule_category
        if description is not None:
            rule.description = description
        if is_active is not None:
            rule.is_active = is_active

        self.db.commit()
        self.db.refresh(rule)

        # 清除缓存并递增版本
        self._invalidate_platform_cache(original_platform)

        logger.info(f"更新规则成功: id={rule_id}")
        return rule

    def delete_rule(self, rule_id: int) -> Optional[PlatformComplianceRule]:
        """
        软删除平台规则（设置 is_active=False）

        Args:
            rule_id: 规则ID

        Returns:
            删除的规则对象，如果不存在返回None
        """
        rule = self.db.get(PlatformComplianceRule, rule_id)
        if not rule:
            return None

        platform = rule.platform
        rule.is_active = False
        self.db.commit()
        self.db.refresh(rule)

        # 清除缓存并递增版本
        self._invalidate_platform_cache(platform)

        logger.info(f"软删除规则成功: id={rule_id}")
        return rule

    def get_rule_by_id(self, rule_id: int) -> Optional[PlatformComplianceRule]:
        """
        根据ID获取规则

        Args:
            rule_id: 规则ID

        Returns:
            规则对象，如果不存在返回None
        """
        return self.db.get(PlatformComplianceRule, rule_id)

    def list_rules(
        self,
        platform: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> Dict[str, Any]:
        """
        分页列出平台规则

        Args:
            platform: 平台名称筛选（可选）
            is_active: 是否激活筛选（可选）
            page: 页码，从1开始
            size: 每页数量

        Returns:
            包含items、total、page、size的字典
        """
        query = self.db.query(PlatformComplianceRule)

        if platform:
            query = query.filter(PlatformComplianceRule.platform == platform.lower())
        if is_active is not None:
            query = query.filter(PlatformComplianceRule.is_active == is_active)

        total = query.count()
        items = query.order_by(PlatformComplianceRule.id.desc()).offset((page - 1) * size).limit(size).all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
        }

    def import_from_yaml(self, platform: str) -> Dict[str, Any]:
        """
        从 YAML 文件批量导入规则到数据库

        Args:
            platform: 平台名称

        Returns:
            导入结果统计: {imported_count, skipped_count, total_count}
        """
        platform = platform.lower()
        yaml_path = RULES_DIR / f"{platform}.yaml"

        if not yaml_path.exists():
            logger.warning(f"YAML 规则文件不存在: {yaml_path}")
            return {
                "imported_count": 0,
                "skipped_count": 0,
                "total_count": 0,
                "message": f"YAML 文件不存在: {platform}.yaml",
            }

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "rules" not in data:
                return {
                    "imported_count": 0,
                    "skipped_count": 0,
                    "total_count": 0,
                    "message": f"YAML 文件格式无效: {platform}.yaml",
                }

            rules = data.get("rules", [])
            imported_count = 0
            skipped_count = 0

            # 获取已存在的规则关键词集合
            existing_keywords = {
                r.keyword_or_pattern
                for r in self.db.query(PlatformComplianceRule).filter(PlatformComplianceRule.platform == platform).all()
            }

            for rule_data in rules:
                keyword = rule_data.get("keyword_or_pattern", "")
                if not keyword or keyword in existing_keywords:
                    skipped_count += 1
                    continue

                # 创建新规则
                rule = PlatformComplianceRule(
                    platform=platform,
                    keyword_or_pattern=keyword,
                    risk_level=rule_data.get("risk_level", "medium"),
                    suggestion=rule_data.get("suggestion", ""),
                    rule_category=rule_data.get("rule_category", ""),
                    description=rule_data.get("description"),
                    is_active=True,
                )
                self.db.add(rule)
                imported_count += 1
                existing_keywords.add(keyword)  # 防止同一文件内重复

            self.db.commit()

            # 清除缓存并递增版本
            if imported_count > 0:
                self._invalidate_platform_cache(platform)

            logger.info(f"YAML 导入完成: platform={platform}, " f"imported={imported_count}, skipped={skipped_count}")

            return {
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "total_count": len(rules),
                "message": f"导入完成: {imported_count} 条新增, {skipped_count} 条跳过",
            }

        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误: {yaml_path}, error={e}")
            return {
                "imported_count": 0,
                "skipped_count": 0,
                "total_count": 0,
                "message": f"YAML 解析错误: {e}",
            }
        except Exception as e:
            logger.error(f"导入失败: {yaml_path}, error={e}")
            self.db.rollback()
            return {
                "imported_count": 0,
                "skipped_count": 0,
                "total_count": 0,
                "message": f"导入失败: {e}",
            }

    def reload_cache(self, platform: Optional[str] = None) -> List[str]:
        """
        手动刷新规则缓存

        Args:
            platform: 指定平台，None表示刷新所有平台

        Returns:
            刷新的平台列表
        """
        if platform:
            platforms = [platform.lower()]
        else:
            # 扫描所有平台
            platforms = []
            if RULES_DIR.exists():
                for yaml_file in RULES_DIR.glob("*.yaml"):
                    platform_name = yaml_file.stem
                    if platform_name:
                        platforms.append(platform_name)

        # 清除缓存
        for plat in platforms:
            self._invalidate_platform_cache(plat, increment_version_flag=False)

        # 重新加载缓存
        for plat in platforms:
            self.get_rules_by_platform(plat)

        logger.info(f"缓存已刷新: platforms={platforms}")
        return platforms

    def _invalidate_platform_cache(self, platform: str, increment_version_flag: bool = True) -> None:
        """
        使指定平台的缓存失效

        Args:
            platform: 平台名称
            increment_version_flag: 是否递增版本号
        """
        platform = platform.lower()

        # 清除服务内部缓存
        self.clear_cache(platform)

        # 清除动态规则缓存
        clear_rule_cache(platform)

        # 递增版本号
        if increment_version_flag:
            increment_version(platform)

        logger.debug(f"平台缓存已失效: platform={platform}")


# 便捷函数：检查文本是否匹配平台规则
def check_text_against_rules(text: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    检查文本是否匹配规则

    Args:
        text: 待检查文本
        rules: 规则列表（来自 get_rules_by_platform）

    Returns:
        匹配的风险点列表
    """
    matched = []
    text_lower = text.lower()

    for rule in rules:
        pattern = rule.get("keyword_or_pattern", "")
        if not pattern:
            continue

        # 尝试作为正则表达式匹配
        try:
            if re.search(pattern, text, re.IGNORECASE):
                matched.append(
                    {
                        "keyword": pattern,
                        "risk_level": rule.get("risk_level", "medium"),
                        "suggestion": rule.get("suggestion", ""),
                        "rule_category": rule.get("rule_category", ""),
                        "source": "platform_rule",
                    }
                )
                continue
        except re.error:
            pass  # 不是有效正则，尝试关键词匹配

        # 关键词匹配
        if pattern.lower() in text_lower:
            matched.append(
                {
                    "keyword": pattern,
                    "risk_level": rule.get("risk_level", "medium"),
                    "suggestion": rule.get("suggestion", ""),
                    "rule_category": rule.get("rule_category", ""),
                    "source": "platform_rule",
                }
            )

    return matched
