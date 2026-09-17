"""Schema 统一导出入口。

路由层从这里导入请求和响应模型，减少对具体 Schema 文件路径的依赖。
"""

from app.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthSessionResponse,
    AuthUserResponse,
)
from app.schemas.assessment import (
    AssessmentMeta,
    AssessmentCompletedResponse,
    AssessmentCreateForm,
    AssessmentCreateResponse,
    AssessmentProgressResponse,
    HighlightItem,
    KnowledgeSource,
    KnowledgeStatus,
    NotebookSummary,
    ProfileSnapshot,
    Report,
    ReportDimension,
    SuggestionItem,
)
from app.schemas.common import AssessmentStatus, TaskType
from app.schemas.history import HistoryItem, HistoryResponse
from app.schemas.notebook import NotebookItemResponse, NotebookResponse, NotebookReviewResponse
from app.schemas.profile import ProfileResponse

__all__ = [
    "AuthLoginRequest",
    "AuthRegisterRequest",
    "AuthSessionResponse",
    "AuthUserResponse",
    "AssessmentCompletedResponse",
    "AssessmentCreateForm",
    "AssessmentCreateResponse",
    "AssessmentMeta",
    "AssessmentProgressResponse",
    "AssessmentStatus",
    "HighlightItem",
    "KnowledgeSource",
    "KnowledgeStatus",
    "HistoryItem",
    "HistoryResponse",
    "NotebookItemResponse",
    "NotebookResponse",
    "NotebookReviewResponse",
    "NotebookSummary",
    "ProfileResponse",
    "ProfileSnapshot",
    "Report",
    "ReportDimension",
    "SuggestionItem",
    "TaskType",
]
