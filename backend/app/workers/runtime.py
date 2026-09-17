from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import traceback

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Assessment
from app.schemas.common import AssessmentStatus
from app.workflows.assessment_graph import AssessmentWorkflow


class AssessmentRuntime:
    def __init__(
        self,
        *,
        workflow: AssessmentWorkflow,
        session_factory: async_sessionmaker,
    ) -> None:
        self.workflow = workflow
        self.session_factory = session_factory
        self.tasks: dict[str, asyncio.Task[None]] = {}

    def start(self, assessment_id: str) -> None:
        task = asyncio.create_task(self._run_with_guard(assessment_id))
        self.tasks[assessment_id] = task
        task.add_done_callback(lambda _: self.tasks.pop(assessment_id, None))

    async def _run_with_guard(self, assessment_id: str) -> None:
        try:
            await self.workflow.run(assessment_id)
        except Exception as exc:
            async with self.session_factory() as session:
                assessment = await session.get(Assessment, assessment_id)
                if assessment is not None:
                    assessment.status = AssessmentStatus.FAILED.value
                    assessment.progress_message = "评估失败"
                    assessment.error_message = str(exc)
                    assessment.progress_percent = 100
                    assessment.completed_at = datetime.now(UTC).replace(tzinfo=None)
                    assessment.updated_at = datetime.now(UTC).replace(tzinfo=None)
                    await session.commit()
            traceback.print_exc()
