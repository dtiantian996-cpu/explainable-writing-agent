"""规范化与中文本地化辅助函数。

LLM 和 mock 输出可能使用略有差异的键名或英文标签。该模块负责将这些键名
规范化为稳定的前端契约，并将展示给用户的标签和文案本地化为中文。
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.assessment import (
    AssessmentCompletedResponse,
    AssessmentMeta,
    HighlightItem,
    NotebookSummary,
    ProfileDominantError,
    ProfileSnapshot,
    SuggestionItem,
)
from app.schemas.notebook import NotebookItemResponse, NotebookResponse
from app.schemas.profile import ProfileResponse

DIMENSION_LABELS = {
    "grammar_accuracy": "语法准确性",
    "task_response": "任务完成度",
    "coherence_cohesion": "连贯与衔接",
    "lexical_resource": "词汇资源",
}

ERROR_LABELS = {
    "grammar": "语法准确性",
    "task_response": "任务完成度",
    "coherence": "连贯与衔接",
    "lexical": "词汇资源",
    "none": "暂无",
}

HIGHLIGHT_LABELS = {
    "advanced_vocabulary": "高级词汇使用",
    "cohesive_device": "衔接手段使用",
    "clear_position": "立场表达清晰",
    "supporting_example": "论证例子有效",
}

KNOWLEDGE_SOURCE_LABELS = {
    "high_score_essay": "高分范文",
    "scoring_criteria": "评分标准",
    "error_case": "错误案例",
    "grammar_knowledge": "语法知识",
    "writing_template": "写作模板",
}

SECTION_LABELS = {
    "introduction": "开头段",
    "body": "主体段",
    "conclusion": "结论段",
}

_TOKEN_SEP_RE = re.compile(r"[\s\-/]+")


def _tokenize(raw: str | None) -> str:
    if not raw:
        return ""
    lowered = raw.strip().lower()
    lowered = _TOKEN_SEP_RE.sub("_", lowered)
    return re.sub(r"_+", "_", lowered).strip("_")


def normalize_dimension_key(raw: str | None) -> str:
    token = _tokenize(raw)
    alias_map = {
        "grammar_accuracy": "grammar_accuracy",
        "grammar": "grammar_accuracy",
        "语法准确性": "grammar_accuracy",
        "task_response": "task_response",
        "task": "task_response",
        "任务完成度": "task_response",
        "coherence_cohesion": "coherence_cohesion",
        "coherence": "coherence_cohesion",
        "cohesion": "coherence_cohesion",
        "连贯与衔接": "coherence_cohesion",
        "lexical_resource": "lexical_resource",
        "lexical": "lexical_resource",
        "vocabulary": "lexical_resource",
        "词汇资源": "lexical_resource",
    }
    if token in alias_map:
        return alias_map[token]
    if "grammar" in token or "grammatical" in token or "语法" in (raw or ""):
        return "grammar_accuracy"
    if "task" in token or "response" in token or "任务" in (raw or ""):
        return "task_response"
    if "cohere" in token or "cohes" in token or "连贯" in (raw or "") or "衔接" in (raw or ""):
        return "coherence_cohesion"
    if "lexical" in token or "vocab" in token or "词汇" in (raw or ""):
        return "lexical_resource"
    return token or "grammar_accuracy"


def normalize_error_key(raw: str | None) -> str:
    token = _tokenize(raw)
    alias_map = {
        "grammar": "grammar",
        "grammar_accuracy": "grammar",
        "语法": "grammar",
        "语法准确性": "grammar",
        "task": "task_response",
        "task_response": "task_response",
        "任务完成度": "task_response",
        "coherence": "coherence",
        "coherence_cohesion": "coherence",
        "cohesion": "coherence",
        "连贯与衔接": "coherence",
        "lexical": "lexical",
        "lexical_resource": "lexical",
        "vocabulary": "lexical",
        "词汇": "lexical",
        "词汇资源": "lexical",
        "none": "none",
        "暂无": "none",
    }
    if token in alias_map:
        return alias_map[token]
    if "grammar" in token or "grammatical" in token or "语法" in (raw or ""):
        return "grammar"
    if "task" in token or "response" in token or "任务" in (raw or ""):
        return "task_response"
    if "cohere" in token or "cohes" in token or "连贯" in (raw or "") or "衔接" in (raw or ""):
        return "coherence"
    if "lexical" in token or "vocab" in token or "词汇" in (raw or ""):
        return "lexical"
    return token or "none"


def normalize_highlight_key(raw: str | None) -> str:
    token = _tokenize(raw)
    alias_map = {
        "advanced_vocabulary": "advanced_vocabulary",
        "vocabulary": "advanced_vocabulary",
        "lexical": "advanced_vocabulary",
        "高级词汇使用": "advanced_vocabulary",
        "cohesive_device": "cohesive_device",
        "coherence": "cohesive_device",
        "cohesion": "cohesive_device",
        "衔接手段使用": "cohesive_device",
        "clear_position": "clear_position",
        "立场表达清晰": "clear_position",
        "supporting_example": "supporting_example",
        "论证例子有效": "supporting_example",
    }
    if token in alias_map:
        return alias_map[token]
    if "vocab" in token or "lexical" in token or "词汇" in (raw or ""):
        return "advanced_vocabulary"
    if "cohes" in token or "cohere" in token or "衔接" in (raw or ""):
        return "cohesive_device"
    if "position" in token or "立场" in (raw or ""):
        return "clear_position"
    if "example" in token or "例子" in (raw or "") or "论证" in (raw or ""):
        return "supporting_example"
    return token or "advanced_vocabulary"


def normalize_knowledge_source_type(raw: str | None) -> str:
    token = _tokenize(raw)
    alias_map = {
        "high_score_essay": "high_score_essay",
        "example_essay": "high_score_essay",
        "band_sample": "high_score_essay",
        "高分范文": "high_score_essay",
        "scoring_criteria": "scoring_criteria",
        "rubric": "scoring_criteria",
        "评分标准": "scoring_criteria",
        "error_case": "error_case",
        "error_examples": "error_case",
        "错误案例": "error_case",
        "grammar_knowledge": "grammar_knowledge",
        "grammar_note": "grammar_knowledge",
        "语法知识": "grammar_knowledge",
        "writing_template": "writing_template",
        "template": "writing_template",
        "写作模板": "writing_template",
    }
    if token in alias_map:
        return alias_map[token]
    return token or "scoring_criteria"


def normalize_heatmap_section(raw: str | None) -> str:
    token = _tokenize(raw)
    alias_map = {
        "introduction": "introduction",
        "开头段": "introduction",
        "body": "body",
        "主体段": "body",
        "conclusion": "conclusion",
        "结论段": "conclusion",
    }
    if token in alias_map:
        return alias_map[token]
    return token or "body"


def localize_dimension_label(raw: str | None) -> str:
    return DIMENSION_LABELS.get(normalize_dimension_key(raw), raw or "维度")


def localize_error_label(raw: str | None) -> str:
    return ERROR_LABELS.get(normalize_error_key(raw), raw or "暂无")


def localize_highlight_label(raw: str | None) -> str:
    return HIGHLIGHT_LABELS.get(normalize_highlight_key(raw), raw or "表达亮点")


def localize_knowledge_source_label(raw: str | None) -> str:
    return KNOWLEDGE_SOURCE_LABELS.get(normalize_knowledge_source_type(raw), raw or "参考资料")


def localize_heatmap_section_label(raw: str | None) -> str:
    return SECTION_LABELS.get(normalize_heatmap_section(raw), raw or "主体段")


def canonicalize_suggestions(suggestions: list[SuggestionItem]) -> list[SuggestionItem]:
    return [
        item.model_copy(
            update={
                "errorType": normalize_error_key(item.errorType),
            }
        )
        for item in suggestions
    ]


def canonicalize_highlights(highlights: list[HighlightItem]) -> list[HighlightItem]:
    return [
        item.model_copy(
            update={
                "type": normalize_highlight_key(item.type),
            }
        )
        for item in highlights
    ]


def canonicalize_profile_snapshot(profile: ProfileSnapshot) -> ProfileSnapshot:
    return profile.model_copy(
        update={
            "dominantErrors": [
                item.model_copy(update={"type": normalize_error_key(item.type)})
                for item in profile.dominantErrors
            ]
        }
    )


def canonicalize_notebook_summary(summary: NotebookSummary) -> NotebookSummary:
    return summary.model_copy(update={"dominantErrorType": normalize_error_key(summary.dominantErrorType)})


def canonicalize_charts_data(charts_data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(charts_data)
    normalized["radar"] = [
        {
            **point,
            "dimension": normalize_dimension_key(str(point.get("dimension", ""))),
        }
        for point in charts_data.get("radar", [])
    ]
    normalized["comparison"] = [
        {
            **point,
            "dimension": normalize_dimension_key(str(point.get("dimension", ""))),
        }
        for point in charts_data.get("comparison", [])
    ]
    normalized["heatmap"] = [
        {
            **point,
            "section": normalize_heatmap_section(str(point.get("section", ""))),
        }
        for point in charts_data.get("heatmap", [])
    ]
    normalized["errorPortrait"] = [
        {
            **point,
            "type": normalize_error_key(str(point.get("type", ""))),
        }
        for point in charts_data.get("errorPortrait", [])
    ]
    return normalized


def localize_charts_data(charts_data: dict[str, Any]) -> dict[str, Any]:
    localized = dict(charts_data)
    localized["radar"] = [
        {
            **point,
            "dimension": localize_dimension_label(str(point.get("dimension", ""))),
        }
        for point in charts_data.get("radar", [])
    ]
    localized["comparison"] = [
        {
            **point,
            "dimension": localize_dimension_label(str(point.get("dimension", ""))),
        }
        for point in charts_data.get("comparison", [])
    ]
    localized["heatmap"] = [
        {
            **point,
            "section": localize_heatmap_section_label(str(point.get("section", ""))),
        }
        for point in charts_data.get("heatmap", [])
    ]
    localized["errorPortrait"] = [
        {
            **point,
            "type": localize_error_label(str(point.get("type", ""))),
        }
        for point in charts_data.get("errorPortrait", [])
    ]
    return localized


def localize_meta(meta: AssessmentMeta) -> AssessmentMeta:
    return meta.model_copy(
        update={
            "knowledgeSources": [
                source.model_copy(update={"type": localize_knowledge_source_label(source.type)})
                for source in meta.knowledgeSources
            ]
        }
    )


def localize_suggestions(suggestions: list[SuggestionItem]) -> list[SuggestionItem]:
    return [
        item.model_copy(
            update={
                "errorType": localize_error_label(item.errorType),
            }
        )
        for item in suggestions
    ]


def localize_highlights(highlights: list[HighlightItem]) -> list[HighlightItem]:
    return [
        item.model_copy(
            update={
                "type": localize_highlight_label(item.type),
            }
        )
        for item in highlights
    ]


def localize_profile_snapshot(profile: ProfileSnapshot) -> ProfileSnapshot:
    return profile.model_copy(
        update={
            "dominantErrors": [
                item.model_copy(update={"type": localize_error_label(item.type)})
                for item in profile.dominantErrors
            ]
        }
    )


def localize_notebook_summary(summary: NotebookSummary) -> NotebookSummary:
    return summary.model_copy(update={"dominantErrorType": localize_error_label(summary.dominantErrorType)})


def localize_assessment_response(payload: AssessmentCompletedResponse) -> AssessmentCompletedResponse:
    return payload.model_copy(
        update={
            "meta": localize_meta(payload.meta),
            "suggestions": localize_suggestions(payload.suggestions),
            "highlights": localize_highlights(payload.highlights),
            "chartsData": localize_charts_data(payload.chartsData),
            "profile": localize_profile_snapshot(payload.profile),
            "notebookSummary": localize_notebook_summary(payload.notebookSummary),
        }
    )


def localize_notebook_response(response: NotebookResponse) -> NotebookResponse:
    return response.model_copy(
        update={
            "summary": localize_notebook_summary(response.summary),
            "items": [
                item.model_copy(update={"errorType": localize_error_label(item.errorType)})
                for item in response.items
            ],
        }
    )


def localize_profile_response(response: ProfileResponse) -> ProfileResponse:
    return response.model_copy(
        update={
            "dominantErrors": [
                ProfileDominantError(
                    type=localize_error_label(item.type),
                    count=item.count,
                    share=item.share,
                )
                for item in response.dominantErrors
            ]
        }
    )


def localize_notebook_item(item: NotebookItemResponse) -> NotebookItemResponse:
    return item.model_copy(update={"errorType": localize_error_label(item.errorType)})
