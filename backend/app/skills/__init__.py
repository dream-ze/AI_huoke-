"""Skill 插件化注册中心"""

from typing import Dict, List, Type


class SkillRegistry:
    """Skill 注册中心，支持动态注册和获取"""

    _skills: Dict[str, Type["BaseSkill"]] = {}

    @classmethod
    def register(cls, skill_class: Type["BaseSkill"]):
        """装饰器：注册 Skill"""
        cls._skills[skill_class.name] = skill_class
        return skill_class

    @classmethod
    def get(cls, name: str) -> "BaseSkill":
        """获取 Skill 实例"""
        skill_class = cls._skills.get(name)
        if not skill_class:
            raise ValueError(f"Skill '{name}' not found")
        return skill_class()

    @classmethod
    def list_all(cls) -> List[Dict]:
        """列出所有已注册的 Skill"""
        return [{"name": s.name, "version": s.version, "description": s.description} for s in cls._skills.values()]


# 导入所有 Skill 模块以触发装饰器注册
from . import (
    classify_skill,
    clean_skill,
    collect_skill,
    compliance_skill,
    knowledge_skill,
    reply_skill,
    retrieve_skill,
    rewrite_skill,
)

# 导出
from .base_skill import BaseSkill, SkillContext, SkillResult
