"""Prompt版本管理器"""

import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PromptVersion:
    """Prompt版本定义"""

    def __init__(
        self, version: str, template: str, description: str = "", created_at: str = None, is_default: bool = False
    ):
        self.version = version
        self.template = template
        self.description = description
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.is_default = is_default


class PromptVersionManager:
    """Prompt版本管理器 - 支持版本切换和A/B测试"""

    def __init__(self):
        self._registry: Dict[str, Dict[str, PromptVersion]] = {}
        self._active_versions: Dict[str, str] = {}  # prompt_name -> active_version

    def register(self, name: str, version: str, template: str, description: str = "", is_default: bool = False):
        """注册prompt版本"""
        if name not in self._registry:
            self._registry[name] = {}

        pv = PromptVersion(version, template, description, is_default=is_default)
        self._registry[name][version] = pv

        if is_default or name not in self._active_versions:
            self._active_versions[name] = version

        logger.info(f"注册Prompt: {name} v{version}" + (" [默认]" if is_default else ""))

    def get_template(self, name: str, version: str = None) -> str:
        """获取prompt模板"""
        if name not in self._registry:
            raise ValueError(f"Prompt '{name}' 未注册")

        v = version or self._active_versions.get(name)
        if v not in self._registry[name]:
            raise ValueError(f"Prompt '{name}' 版本 '{v}' 不存在")

        return self._registry[name][v].template

    def set_active_version(self, name: str, version: str):
        """切换活跃版本（用于A/B测试）"""
        if name in self._registry and version in self._registry[name]:
            old = self._active_versions.get(name)
            self._active_versions[name] = version
            logger.info(f"Prompt版本切换: {name} v{old} -> v{version}")

    def list_versions(self, name: str) -> list:
        """列出所有版本"""
        if name not in self._registry:
            return []
        return [
            {
                "version": v.version,
                "description": v.description,
                "is_active": v.version == self._active_versions.get(name),
            }
            for v in self._registry[name].values()
        ]

    def get_active_version(self, name: str) -> Optional[str]:
        """获取当前活跃版本"""
        return self._active_versions.get(name)


# 全局实例
prompt_manager = PromptVersionManager()


def _load_prompt_from_file(file_path: str) -> str:
    """从文件加载prompt内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"无法加载prompt文件 {file_path}: {e}")
        return ""


def _register_file_prompts():
    """注册所有文件中的prompt版本"""
    import os

    prompts_dir = os.path.dirname(os.path.abspath(__file__))

    # 定义prompt文件映射
    prompt_files = {
        "xiaohongshu": "mvp_xiaohongshu_v1.txt",
        "douyin": "mvp_douyin_v1.txt",
        "general": "mvp_general_v1.txt",
        "compliance_rewrite": "mvp_compliance_rewrite_v1.txt",
        "hot_rewrite": "mvp_hot_rewrite_v1.txt",
        "material_analyze": "material_analyze_v1.txt",
        "compliance_review": "compliance_review_v1.txt",
        "followup_assistant": "followup_assistant_v1.txt",
        "rewrite_douyin": "rewrite_douyin_v1.txt",
        "rewrite_xhs": "rewrite_xhs_v1.txt",
    }

    for name, filename in prompt_files.items():
        file_path = os.path.join(prompts_dir, filename)
        if os.path.exists(file_path):
            template = _load_prompt_from_file(file_path)
            if template:
                prompt_manager.register(
                    name=name,
                    version="v1",
                    template=template,
                    description=f"从 {filename} 加载的初始版本",
                    is_default=True,
                )


# 启动时自动注册文件中的prompt
_register_file_prompts()
