"""Skill 基类 - 所有技能节点继承此类"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillContext:
    """Skill 执行上下文"""

    trace_id: str
    user_id: int
    workflow_task_id: int
    input_data: Dict[str, Any]
    previous_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    """Skill 执行结果"""

    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    duration_ms: int = 0
    should_continue: bool = True
    next_skill: Optional[str] = None


class BaseSkill(ABC):
    """
    Skill 基类，所有技能节点继承此类。

    设计原则：
    1. 单一职责：每个 Skill 只做一件事
    2. 可组合：通过 workflow 串联多个 Skill
    3. 可重试：失败后支持自动重试
    4. 可追溯：记录输入输出和执行时间
    """

    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    max_retries: int = 3
    timeout_seconds: int = 60

    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行技能核心逻辑"""
        pass

    def validate_input(self, context: SkillContext) -> bool:
        """校验输入参数"""
        return True

    async def on_success(self, context: SkillContext, result: SkillResult):
        """成功回调"""
        logger.info(f"[{self.name}] Success in {result.duration_ms}ms")

    async def on_failure(self, context: SkillContext, error: Exception):
        """失败回调"""
        logger.error(f"[{self.name}] Failed: {error}")

    async def run(self, context: SkillContext) -> SkillResult:
        """带重试和计时的执行入口"""
        if not self.validate_input(context):
            return SkillResult(success=False, data={}, error="Input validation failed")

        start = datetime.utcnow()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                result = await self.execute(context)
                result.duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)

                if result.success:
                    await self.on_success(context, result)
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"[{self.name}] Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # 指数退避

        await self.on_failure(context, last_error)
        return SkillResult(
            success=False,
            data={},
            error=str(last_error),
            duration_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
        )
