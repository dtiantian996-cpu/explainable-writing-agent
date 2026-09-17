"""错题本页面相关 Schema。"""

from app.schemas.assessment import NotebookSummary
from app.schemas.common import APIModel


class NotebookItemResponse(APIModel):
    """错题本列表和详情区展示的一条错题。"""

    id: str
    assessmentId: str
    sourceEssayTitle: str
    taskType: str
    errorType: str
    sourceText: str
    explanation: str
    revision: str
    revisedSentence: str
    status: str
    createdAt: str


class NotebookResponse(APIModel):
    """错题本接口响应，包含摘要和条目列表。"""

    summary: NotebookSummary
    items: list[NotebookItemResponse]


class NotebookReviewResponse(APIModel):
    """标记错题已复习后的响应。"""

    id: str
    status: str
    reviewedAt: str
