"""工作流基类"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.state_machine import WorkflowTaskStatus
from app.events.event_store import EventStore, EventType
from app.skills import SkillContext, SkillRegistry, SkillResult
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BaseWorkflow:
    """
    工作流基类 - 定义 Skill 节点链的编排与执行。

    子类需要定义:
    - name: 工作流名称
    - skill_chain: Skill 名称有序列表
    """

    name: str = ""
    description: str = ""
    skill_chain: List[str] = []

    def __init__(self, db: Session):
        self.db = db
        self.event_store = EventStore(db)

    async def start(
        self,
        user_id: int,
        input_data: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        启动工作流，依次执行 skill_chain 中的每个 Skill。

        Returns:
            包含 workflow_task_id、最终状态和输出数据的字典
        """
        trace_id = trace_id or str(uuid.uuid4())

        # 1. 创建工作流任务记录
        from app.models.models import SkillExecution, WorkflowTask

        task = WorkflowTask(
            workflow_type=self.name,
            status=WorkflowTaskStatus.RUNNING.value,
            trace_id=trace_id,
            input_data=input_data,
            owner_id=user_id,
            started_at=datetime.utcnow(),
        )
        self.db.add(task)
        self.db.flush()

        self.event_store.emit_workflow_event(
            workflow_task_id=task.id,
            event_type=EventType.WORKFLOW_STARTED,
            trace_id=trace_id,
            user_id=user_id,
            data={"workflow_type": self.name, "skill_chain": self.skill_chain},
        )

        # 2. 逐个执行 Skill
        accumulated_results = {}
        current_data = input_data

        for skill_name in self.skill_chain:
            task.current_skill = skill_name
            self.db.flush()

            try:
                skill = SkillRegistry.get(skill_name)
            except ValueError as e:
                logger.error(f"Skill not found: {skill_name}")
                task.status = WorkflowTaskStatus.FAILED.value
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
                self.db.commit()

                self.event_store.emit_workflow_event(
                    workflow_task_id=task.id,
                    event_type=EventType.WORKFLOW_FAILED,
                    trace_id=trace_id,
                    user_id=user_id,
                    data={"error": str(e), "failed_at_skill": skill_name},
                )
                return {
                    "workflow_task_id": task.id,
                    "status": WorkflowTaskStatus.FAILED.value,
                    "error": str(e),
                }

            # 创建 Skill 执行记录
            execution = SkillExecution(
                workflow_task_id=task.id,
                skill_name=skill_name,
                status="running",
                input_snapshot=current_data,
            )
            self.db.add(execution)
            self.db.flush()

            self.event_store.emit_skill_event(
                skill_execution_id=execution.id,
                event_type=EventType.SKILL_STARTED,
                trace_id=trace_id,
                skill_name=skill_name,
            )

            # 执行 Skill
            context = SkillContext(
                trace_id=trace_id,
                user_id=user_id,
                workflow_task_id=task.id,
                input_data=current_data,
                previous_results=accumulated_results,
            )

            result = await skill.run(context)

            # 更新执行记录
            execution.status = "success" if result.success else "failed"
            execution.duration_ms = result.duration_ms
            execution.output_snapshot = result.data
            if result.error:
                execution.error_detail = result.error
            self.db.flush()

            if result.success:
                self.event_store.emit_skill_event(
                    skill_execution_id=execution.id,
                    event_type=EventType.SKILL_COMPLETED,
                    trace_id=trace_id,
                    skill_name=skill_name,
                    data={"duration_ms": result.duration_ms},
                )
                accumulated_results[skill_name] = result.data
                current_data = result.data  # 下一个 Skill 的输入
            else:
                self.event_store.emit_skill_event(
                    skill_execution_id=execution.id,
                    event_type=EventType.SKILL_FAILED,
                    trace_id=trace_id,
                    skill_name=skill_name,
                    data={"error": result.error},
                )

                # Skill 失败，中断工作流
                if not result.should_continue:
                    task.status = WorkflowTaskStatus.FAILED.value
                    task.error_message = f"Skill '{skill_name}' failed: {result.error}"
                    task.completed_at = datetime.utcnow()
                    self.db.commit()

                    self.event_store.emit_workflow_event(
                        workflow_task_id=task.id,
                        event_type=EventType.WORKFLOW_FAILED,
                        trace_id=trace_id,
                        user_id=user_id,
                        data={"failed_at_skill": skill_name, "error": result.error},
                    )
                    return {
                        "workflow_task_id": task.id,
                        "status": WorkflowTaskStatus.FAILED.value,
                        "error": result.error,
                        "failed_at_skill": skill_name,
                    }

            # 动态路由
            if result.next_skill:
                logger.info(f"Dynamic routing to skill: {result.next_skill}")
                # 后续可支持动态跳转

        # 3. 工作流完成
        task.status = WorkflowTaskStatus.SUCCESS.value
        task.output_data = accumulated_results
        task.completed_at = datetime.utcnow()
        task.current_skill = None
        self.db.commit()

        self.event_store.emit_workflow_event(
            workflow_task_id=task.id,
            event_type=EventType.WORKFLOW_COMPLETED,
            trace_id=trace_id,
            user_id=user_id,
            data={"total_skills": len(self.skill_chain)},
        )

        return {
            "workflow_task_id": task.id,
            "status": WorkflowTaskStatus.SUCCESS.value,
            "results": accumulated_results,
        }
