"""历史记录、错题本和用户画像 API 的读取模型构建器。

这些函数查询规范化后的数据库表，并组装适合前端页面直接使用的响应结构。
除了明确的错题复习动作外，这里不会修改评估结果数据。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assessment, AssessmentResult, NotebookItem
from app.schemas.assessment import NotebookSummary, ProfileDominantError, Report
from app.schemas.common import AssessmentStatus
from app.schemas.history import HistoryItem, HistoryResponse
from app.schemas.notebook import NotebookItemResponse, NotebookResponse, NotebookReviewResponse
from app.schemas.profile import ProfileResponse
from app.services.localization import (
    localize_notebook_response,
    localize_profile_response,
)
from app.services.scoring import average_ielts_band, clamp_ielts_band
from app.workflows.assessment_graph import overall_score


async def get_history(session: AsyncSession, user_id: str) -> HistoryResponse:
    """返回用户的全部评估记录，按时间倒序排列，并附带总分。"""

    rows = await session.execute(
        select(Assessment, AssessmentResult.report)
        .outerjoin(AssessmentResult, AssessmentResult.assessment_id == Assessment.id)
        .where(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc())
    )
    items: list[HistoryItem] = []
    for assessment, report_data in rows.all():
        score = 0.0
        if report_data:
            score = overall_score(Report.model_validate(report_data))
        items.append(
            HistoryItem(
                assessmentId=assessment.id,
                topic=assessment.topic,
                taskType=assessment.task_type,
                overallScore=score,
                status=assessment.status,
                createdAt=assessment.created_at.replace(tzinfo=UTC).isoformat(),
            )
        )
    return HistoryResponse(items=items)


async def get_notebook(session: AsyncSession, user_id: str) -> NotebookResponse:
    """根据持久化的建议派生条目构建错题本页面数据。"""

    rows = await session.execute(
        select(NotebookItem, Assessment.topic, Assessment.task_type)
        .join(Assessment, Assessment.id == NotebookItem.assessment_id)
        .where(NotebookItem.user_id == user_id)
        .order_by(NotebookItem.created_at.desc())
    )
    pairs = rows.all()
    # 摘要指标用于驱动错题本顶部卡片和筛选统计。
    reviewed = sum(1 for item, _, _ in pairs if item.status == "reviewed")
    pending = sum(1 for item, _, _ in pairs if item.status != "reviewed")
    dominant = "none"
    if pairs:
        counts: dict[str, int] = {}
        for item, _, _ in pairs:
            counts[item.error_type] = counts.get(item.error_type, 0) + 1
        dominant = max(counts.items(), key=lambda pair: pair[1])[0]

    summary = NotebookSummary(
        totalItems=len(pairs),
        reviewedItems=reviewed,
        pendingReviewCount=pending,
        dominantErrorType=dominant,
    )
    response_items = [
        NotebookItemResponse(
            id=item.id,
            assessmentId=item.assessment_id,
            sourceEssayTitle=topic,
            taskType=task_type,
            errorType=item.error_type,
            sourceText=item.source_text,
            explanation=item.explanation,
            revision=item.revision,
            revisedSentence=item.revised_sentence,
            status=item.status,
            createdAt=item.created_at.replace(tzinfo=UTC).isoformat(),
        )
        for item, topic, task_type in pairs
    ]
    return localize_notebook_response(NotebookResponse(summary=summary, items=response_items))


async def review_notebook_item(session: AsyncSession, item_id: str, user_id: str) -> NotebookReviewResponse:
    """将当前用户的一条错题本条目标记为已复习。"""

    item = await session.get(NotebookItem, item_id)
    if item is None or item.user_id != user_id:
        raise ValueError("notebook item not found")
    item.status = "reviewed"
    item.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    item.updated_at = item.reviewed_at
    await session.commit()
    return NotebookReviewResponse(
        id=item.id,
        status=item.status,
        reviewedAt=item.reviewed_at.replace(tzinfo=UTC).isoformat(),
    )


async def get_profile(session: AsyncSession, user_id: str) -> ProfileResponse:
    """聚合历史记录和错题本数据，生成长期用户画像视图。"""

    history = await get_history(session, user_id)
    notebook = await get_notebook(session, user_id)
    # 只有已完成的评估才参与长期分数统计。
    completed_history = [item for item in history.items if item.status == AssessmentStatus.COMPLETED]
    average = 0.0
    if completed_history:
        average = average_ielts_band(
            item.overallScore for item in completed_history
        )

    counts: dict[str, int] = {}
    for item in notebook.items:
        counts[item.errorType] = counts.get(item.errorType, 0) + 1
    # 主导错误按出现频率排序，用于首页和画像页的进度条展示。
    total = max(1, sum(counts.values()))
    dominant_errors = [
        ProfileDominantError(type=key, count=value, share=round(value / total, 2))
        for key, value in sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
    ]

    learning_path = [
        "优先处理最近 7 天里重复出现最多的错误类型。",
        "完成一次错题复习后，再回到提交页做下一篇作文。",
        "把结论段和主体段连接词一起练，提升收束感。",
    ]
    if dominant_errors:
        learning_path[0] = f"先集中复习 {dominant_errors[0].type} 类错误，避免同类问题反复出现。"

    recent_scores = [item.overallScore for item in completed_history[:4]]
    next_target = clamp_ielts_band(
        (recent_scores[0] if recent_scores else 6.5) + 0.5,
        maximum=8.0,
    )
    summary = "画像样本还在积累，继续写作会让建议更稳定。"
    if dominant_errors:
        summary = f"当前主导错误是 {dominant_errors[0].type}，先把这一类错误压下去，整体分数会更稳。"

    response = ProfileResponse(
        averageScore=average,
        recentScores=list(reversed(recent_scores)),
        dominantErrors=dominant_errors,
        learningPath=learning_path,
        nextTargetScore=next_target,
        summaryNarrative=summary,
    )
    return localize_profile_response(response)


async def get_demo_user_id(session: AsyncSession, email: str) -> str:
    result = await session.execute(select(Assessment.user_id).limit(1))
    user_id = result.scalar_one_or_none()
    if user_id:
        return user_id

    from app.models import User

    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        raise ValueError("demo user not initialized")
    return user.id
