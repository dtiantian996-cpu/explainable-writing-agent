"""作文评估相关 Pydantic Schema。

该文件定义多 Agent 结构化输出、评估结果响应、知识库来源、错题摘要和用户
画像快照等核心数据结构，是后端 AI 输出与前端结果页之间的主要契约。
"""

from enum import StrEnum
from typing import Any

from pydantic import AliasChoices, Field, model_validator

from app.schemas.common import APIModel, AssessmentStatus, TaskType


class ReportDimension(APIModel):
    """单个评分维度的结构，包含分数和评分理由。"""

    score: float
    reasonBullets: list[str] = Field(
        validation_alias=AliasChoices("reasonBullets", "feedback", "reasons", "bullets")
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_reason_bullets(cls, value: Any) -> Any:
        """兼容不同模型输出字段名，并统一整理为 reasonBullets。"""

        if not isinstance(value, dict):
            return value
        payload = dict(value)
        raw_bullets = payload.get("reasonBullets", payload.get("feedback", payload.get("reasons", payload.get("bullets", []))))
        if isinstance(raw_bullets, str):
            payload["reasonBullets"] = [raw_bullets]
        else:
            payload["reasonBullets"] = raw_bullets
        return payload


class Report(APIModel):
    """雅思写作四维评分报告。"""

    grammar_accuracy: ReportDimension
    task_response: ReportDimension
    coherence_cohesion: ReportDimension
    lexical_resource: ReportDimension


class LanguageAgentOutput(APIModel):
    """Language Agent 的结构化输出，只覆盖语法维度。"""

    grammar_accuracy: ReportDimension


class DiscourseAgentOutput(APIModel):
    """Discourse Agent 的结构化输出，覆盖任务回应和连贯衔接。"""

    task_response: ReportDimension
    coherence_cohesion: ReportDimension


class SuggestionItem(APIModel):
    """逐句可解释修改建议，用于原文高亮和错题本沉淀。"""

    errorType: str = Field(validation_alias=AliasChoices("errorType", "error_type", "type"))
    sourceText: str = Field(
        validation_alias=AliasChoices("sourceText", "source_text", "originalText", "original_text", "text")
    )
    explanation: str
    revision: str = Field(validation_alias=AliasChoices("revision", "suggestion", "advice"))
    revisedSentence: str = Field(
        validation_alias=AliasChoices("revisedSentence", "revised_sentence", "rewrite")
    )
    positionStart: int = Field(
        default=0,
        validation_alias=AliasChoices("positionStart", "position_start", "start", "startIndex"),
    )
    positionEnd: int = Field(
        default=0,
        validation_alias=AliasChoices("positionEnd", "position_end", "end", "endIndex"),
    )


class HighlightItem(APIModel):
    """作文亮点条目，用于结果页亮点分析。"""

    type: str = Field(validation_alias=AliasChoices("type", "highlightType", "highlight_type"))
    location: str = Field(validation_alias=AliasChoices("location", "sourceText", "source_text"))
    explanation: str
    encouragement: str


class KnowledgeStatus(StrEnum):
    """本次评估的 RAG 知识检索状态。"""

    DISABLED = "disabled"
    FALLBACK = "fallback"
    ENABLED = "enabled"


class KnowledgeSource(APIModel):
    """RAG 检索命中的一条参考资料。"""

    id: str
    title: str
    type: str
    score: float
    rerankScore: float | None = None
    ieltsTask: str | None = None
    excerpt: str
    selectionReason: str


class AssessmentMeta(APIModel):
    """一次评估的元信息，包括输入来源、字数和知识库使用情况。"""

    sourceMode: str
    wordCount: int
    generatedAt: str
    knowledgeStatus: KnowledgeStatus = KnowledgeStatus.DISABLED
    knowledgeTask: str | None = None
    knowledgeWarnings: list[str] = Field(default_factory=list)
    knowledgeSources: list[KnowledgeSource] = Field(default_factory=list)


class NotebookSummary(APIModel):
    """本次评估生成的错题本摘要。"""

    totalItems: int
    reviewedItems: int = 0
    pendingReviewCount: int = 0
    dominantErrorType: str


class ProfileDominantError(APIModel):
    """用户画像中的主导错误统计项。"""

    type: str
    count: int
    share: float


class ProfileSnapshot(APIModel):
    """一次评估完成时生成的用户画像快照。"""

    dominantErrors: list[ProfileDominantError]
    learningPath: list[str]
    nextTargetScore: float
    summaryNarrative: str


class AssessmentCreateResponse(APIModel):
    """创建评估任务后的立即响应。"""

    assessmentId: str
    status: AssessmentStatus
    etaSeconds: int = 120


class AssessmentProgressResponse(APIModel):
    """评估任务未完成时返回的进度响应。"""

    assessmentId: str
    status: AssessmentStatus
    progressMessage: str
    progressPercent: int
    errorMessage: str | None = None


class AssessmentCompletedResponse(APIModel):
    """评估任务完成后返回给结果页的完整响应。"""

    assessmentId: str
    status: AssessmentStatus = AssessmentStatus.COMPLETED
    essayText: str = ""
    meta: AssessmentMeta
    report: Report
    suggestions: list[SuggestionItem]
    highlights: list[HighlightItem]
    chartsData: dict[str, Any]
    profile: ProfileSnapshot
    notebookSummary: NotebookSummary


class AssessmentCreateForm(APIModel):
    """作文提交表单的结构定义。"""

    topic: str = Field(min_length=1, max_length=500)
    task_type: TaskType
    essay_text: str | None = None
