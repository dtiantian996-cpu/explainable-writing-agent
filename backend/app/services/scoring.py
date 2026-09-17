"""雅思分数归一化辅助函数。

AI 智能体可能返回任意数值，因此所有对外报告、画像和图表中的分数
在返回前端前都会经过这里的统一处理。
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

from app.schemas.assessment import AssessmentCompletedResponse, ProfileSnapshot, Report

_HALF_STEP = Decimal("0.5")
_ONE = Decimal("1")


def round_ielts_band(value: float) -> float:
    """将数值分数四舍五入到最近的雅思半分档。"""

    decimal_value = Decimal(str(value))
    rounded = (decimal_value / _HALF_STEP).quantize(_ONE, rounding=ROUND_HALF_UP) * _HALF_STEP
    return float(rounded)


def clamp_ielts_band(
    value: float,
    *,
    minimum: float = 0.0,
    maximum: float = 9.0,
) -> float:
    """将分数限制在雅思范围内，并归一化到半分档。"""

    return round_ielts_band(min(maximum, max(minimum, value)))


def average_ielts_band(
    values: Iterable[float],
    *,
    minimum: float = 0.0,
    maximum: float = 9.0,
) -> float:
    """计算平均分，并归一化为有效雅思分数。"""

    items = list(values)
    if not items:
        raise ValueError("at least one score is required")
    return clamp_ielts_band(sum(items) / len(items), minimum=minimum, maximum=maximum)


def format_ielts_band(value: float) -> str:
    """将雅思分数格式化为一位小数的展示文本。"""

    return f"{round_ielts_band(value):.1f}"


def normalize_report_scores(report: Report) -> Report:
    """归一化报告中每个维度的分数。"""

    return report.model_copy(
        update={
            "grammar_accuracy": report.grammar_accuracy.model_copy(
                update={"score": clamp_ielts_band(report.grammar_accuracy.score)}
            ),
            "task_response": report.task_response.model_copy(
                update={"score": clamp_ielts_band(report.task_response.score)}
            ),
            "coherence_cohesion": report.coherence_cohesion.model_copy(
                update={"score": clamp_ielts_band(report.coherence_cohesion.score)}
            ),
            "lexical_resource": report.lexical_resource.model_copy(
                update={"score": clamp_ielts_band(report.lexical_resource.score)}
            ),
        }
    )


def normalize_profile_snapshot_scores(profile: ProfileSnapshot) -> ProfileSnapshot:
    """归一化用户画像快照中的分数类字段。"""

    return profile.model_copy(
        update={
            "nextTargetScore": clamp_ielts_band(profile.nextTargetScore),
        }
    )


def normalize_charts_data_scores(charts_data: dict[str, Any]) -> dict[str, Any]:
    """归一化图表数据字典中的分数字段。"""

    normalized = dict(charts_data)
    normalized["radar"] = [
        {**point, "score": clamp_ielts_band(float(point.get("score", 0)), minimum=0.0)}
        for point in charts_data.get("radar", [])
    ]
    normalized["comparison"] = [
        {
            **point,
            "score": clamp_ielts_band(float(point.get("score", 0)), minimum=0.0),
            "ieltsTarget": clamp_ielts_band(float(point.get("ieltsTarget", 0)), minimum=0.0),
        }
        for point in charts_data.get("comparison", [])
    ]
    normalized["trendLine"] = [
        clamp_ielts_band(float(score), minimum=0.0) for score in charts_data.get("trendLine", [])
    ]
    return normalized


def normalize_assessment_scores(payload: AssessmentCompletedResponse) -> AssessmentCompletedResponse:
    """归一化完整评估响应中所有包含分数的部分。"""

    return payload.model_copy(
        update={
            "report": normalize_report_scores(payload.report),
            "profile": normalize_profile_snapshot_scores(payload.profile),
            "chartsData": normalize_charts_data_scores(payload.chartsData),
        }
    )
