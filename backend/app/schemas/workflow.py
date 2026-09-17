"""评估工作流内部使用的 Schema 和进度配置。"""

from app.schemas.assessment import HighlightItem, NotebookSummary, ProfileSnapshot, Report, SuggestionItem
from app.schemas.common import APIModel, TaskType


PROGRESS_MAP = {
    # 各工作流阶段对应的前端进度百分比。
    "queued": 5,
    "ocr_if_needed": 20,
    "normalize_input": 30,
    "agent_parallel_run": 65,
    "supervisor_merge": 80,
    "persist_results": 95,
    "completed": 100,
}


class TutorAgentOutput(APIModel):
    """Tutor Agent 的输出结构。"""

    suggestions: list[SuggestionItem]
    highlights: list[HighlightItem]
    learningPath: list[str]


class SupervisorOutput(APIModel):
    """主管融合节点输出的结构。"""

    meta: dict
    report: Report
    suggestions: list[SuggestionItem]
    highlights: list[HighlightItem]
    chartsData: dict
    profile: ProfileSnapshot
    notebookSummary: NotebookSummary


class WorkflowInput(APIModel):
    """启动评估工作流所需的输入信息。"""

    assessment_id: str
    topic: str
    task_type: TaskType
    essay_text: str | None
    image_paths: list[str]
