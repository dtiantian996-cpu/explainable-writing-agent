"""历史记录页面相关 Schema。"""

from app.schemas.common import APIModel, AssessmentStatus, TaskType


class HistoryItem(APIModel):
    """历史列表中的一条评估记录。"""

    assessmentId: str
    topic: str
    taskType: TaskType
    overallScore: float
    status: AssessmentStatus
    createdAt: str


class HistoryResponse(APIModel):
    """历史记录接口响应。"""

    items: list[HistoryItem]
