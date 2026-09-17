"""通用 Schema 基类和枚举定义。"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """项目内所有接口模型的统一基类。"""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class TaskType(StrEnum):
    """作文任务类型，与提交页的题型选择保持一致。"""

    TASK1_ACADEMIC = "task1_academic"
    TASK1_GENERAL = "task1_general"
    TASK2 = "task2"


class AssessmentStatus(StrEnum):
    """评估任务状态，用于后端工作流和前端轮询展示。"""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
