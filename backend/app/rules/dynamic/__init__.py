"""动态规则引擎模块"""

from app.rules.dynamic.rule_cache import (
    clear_cache,
    get_cache_stats,
    get_cached_rules,
    get_rule_cache,
    set_cached_rules,
)
from app.rules.dynamic.rule_loader import get_platforms, load_all_rules, load_rules, reload_rules
from app.rules.dynamic.rule_versioning import get_active_version, get_version_info, increment_version, reset_version

__all__ = [
    # rule_cache
    "get_rule_cache",
    "get_cached_rules",
    "set_cached_rules",
    "clear_cache",
    "get_cache_stats",
    # rule_loader
    "load_rules",
    "load_all_rules",
    "reload_rules",
    "get_platforms",
    # rule_versioning
    "get_active_version",
    "increment_version",
    "get_version_info",
    "reset_version",
]
