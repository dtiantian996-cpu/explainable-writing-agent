"""
API 路由模块

定义所有面向客户端的 RESTful 端点，包括：
- 系统健康检查
- 用户认证（注册/登录/登出/获取当前用户）
- 作文评估任务创建与结果查询
- 评估报告 PDF 导出
- 历史记录、错题本、用户画像

所有认证接口使用 HttpOnly Cookie 维护会话，无需前端手动管理 token。
"""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models import Assessment, AssessmentResult, User
from app.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthSessionResponse,
    AuthUserResponse,
    AssessmentMeta,
    AssessmentCompletedResponse,
    AssessmentCreateResponse,
    AssessmentProgressResponse,
    AssessmentStatus,
    HighlightItem,
    HistoryResponse,
    NotebookSummary,
    NotebookResponse,
    NotebookReviewResponse,
    ProfileSnapshot,
    ProfileResponse,
    Report,
    SuggestionItem,
    TaskType,
)
from app.services.read_models import get_history, get_notebook, get_profile, review_notebook_item
from app.services.auth import (
    clear_session_cookie,
    hash_password,
    require_current_user,
    set_session_cookie,
    verify_password,
)
from app.services.localization import localize_assessment_response
from app.services.pdf_export import build_assessment_pdf
from app.services.scoring import normalize_assessment_scores

# 创建 API 路由器，所有路由以 /api 为前缀
router = APIRouter(prefix="/api")

# ==================== 内部辅助函数 ====================

def _build_auth_response(user: User) -> AuthSessionResponse:
    """将 User 模型转换为认证响应结构（含用户信息）"""
    return AuthSessionResponse(user=AuthUserResponse.model_validate(user))


async def _get_assessment_or_404(session: AsyncSession, assessment_id: str, user_id: str) -> Assessment:
    """根据 assessment_id 和 user_id 查询评估记录，不存在则返回 404"""
    assessment = await session.scalar(
        select(Assessment).where(Assessment.id == assessment_id, Assessment.user_id == user_id)
    )
    if assessment is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    return assessment


async def _build_completed_response(
    session: AsyncSession,
    assessment: Assessment,
) -> AssessmentCompletedResponse:
    """从数据库构建完整的评估结果响应（用于已完成的任务）"""
    from sqlalchemy import select

    result = await session.scalar(
        select(AssessmentResult).where(AssessmentResult.assessment_id == assessment.id)
    )
    if result is None:
        raise HTTPException(status_code=500, detail="assessment result missing")

    # 组装完整响应，字段来源：
    # - meta/report/suggestions/highlights 等来自 AssessmentResult（多智能体输出）
    # - essayText 优先使用 normalized_text，其次原始文本或 OCR 文本
    payload = AssessmentCompletedResponse(
        assessmentId=assessment.id,
        essayText=assessment.normalized_text or assessment.essay_text or assessment.ocr_text or "",
        meta=AssessmentMeta.model_validate(result.meta),
        report=Report.model_validate(result.report),
        suggestions=[SuggestionItem.model_validate(item) for item in result.suggestions],
        highlights=[HighlightItem.model_validate(item) for item in result.highlights],
        chartsData=result.charts_data,
        profile=ProfileSnapshot.model_validate(result.profile_snapshot),
        notebookSummary=NotebookSummary.model_validate(result.notebook_summary),
    )
    # 本地化（中文输出） + 归一化评分（确保所有维度分数一致）
    return localize_assessment_response(normalize_assessment_scores(payload))


# ==================== 系统接口 ====================

@router.get("/healthz", tags=["system"])
async def healthz() -> dict[str, str]:
    """健康检查接口，返回服务状态、环境和版本"""
    settings = get_settings()
    return {
        "status": "ok",
        "service": "backend",
        "env": settings.app_env,
        "version": settings.app_version,
    }


# ==================== 认证接口 ====================

@router.post(
    "/auth/register",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
async def register(
    payload: AuthRegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> AuthSessionResponse:
    """
    用户注册
    - 检查邮箱是否已被注册（409 冲突）
    - 加密密码，创建 User 记录
    - 设置 session cookie，直接返回登录态
    """
    existing_user = await session.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="该邮箱已被注册")

    now = datetime.now(UTC).replace(tzinfo=None)
    user = User(
        email=payload.email,
        display_name=payload.displayName,
        password_hash=hash_password(payload.password),
        role="student",
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    set_session_cookie(response, user.id)   # 设置登录 cookie
    return _build_auth_response(user)


@router.post("/auth/login", response_model=AuthSessionResponse, tags=["auth"])
async def login(
    payload: AuthLoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> AuthSessionResponse:
    """
    用户登录
    - 验证邮箱和密码
    - 设置 session cookie
    """
    user = await session.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    set_session_cookie(response, user.id)
    return _build_auth_response(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
async def logout(response: Response) -> Response:
    """登出：清除 session cookie"""
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/auth/me", response_model=AuthSessionResponse, tags=["auth"])
async def me(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AuthSessionResponse:
    """获取当前登录用户信息（通过 cookie 中的 session 识别）"""
    user = await require_current_user(request, session)
    return _build_auth_response(user)


# ==================== 作文评估核心接口 ====================

@router.post("/assessments", response_model=AssessmentCreateResponse, tags=["assessments"])
async def create_assessment(
    request: Request,
    topic: str = Form(...),
    task_type: TaskType = Form(...),
    essay_text: str | None = Form(default=None),
    images: list[UploadFile] = File(default_factory=list),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_current_user),
) -> AssessmentCreateResponse:
    """
    创建作文评估任务

    - 支持纯文本提交或图片上传（可混合）
    - 持久化用户上传的图片到存储
    - 在数据库中创建 Assessment 记录（状态为 QUEUED）
    - 异步启动 LangGraph 工作流（runtime.start）
    - 立即返回 assessmentId，前端通过轮询获取结果
    """
    text = (essay_text or "").strip()
    if not topic.strip():
        raise HTTPException(status_code=422, detail="请输入作文题目")
    if not text and not images:
        raise HTTPException(status_code=422, detail="请至少提供正文或图片")

    # 从 app 状态中获取工作流运行时和存储服务（在 main.py 中初始化）
    runtime = request.app.state.assessment_runtime
    storage = request.app.state.storage
    assessment_id = str(uuid.uuid4())
    saved_paths = await storage.persist_uploads(assessment_id, images) if images else []

    # 判断输入模式（文本/图片/混合）
    source_mode = "text"
    if text and saved_paths:
        source_mode = "mixed"
    elif saved_paths:
        source_mode = "image"

    now = datetime.now(UTC).replace(tzinfo=None)
    assessment = Assessment(
        id=assessment_id,
        user_id=current_user.id,
        topic=topic.strip(),
        task_type=task_type.value,
        source_mode=source_mode,
        essay_text=text or None,
        status=AssessmentStatus.QUEUED.value,
        progress_message="等待开始评估",
        progress_percent=5,
        created_at=now,
        updated_at=now,
    )
    session.add(assessment)
    await session.commit()

    # 异步启动工作流（不等待完成）
    runtime.start(assessment_id)
    return AssessmentCreateResponse(
        assessmentId=assessment_id,
        status=AssessmentStatus.QUEUED,
        etaSeconds=120,
    )


@router.get("/assessments/{assessment_id}", tags=["assessments"])
async def get_assessment(
    assessment_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_current_user),
) -> AssessmentProgressResponse | AssessmentCompletedResponse:
    """
    获取评估任务状态或结果

    - 如果任务未完成（QUEUED/PROCESSING/FAILED），返回进度信息
    - 如果任务已完成（COMPLETED），返回完整评估报告
    - 此接口用于前端轮询（建议每 2-3 秒调用一次）
    """
    assessment = await _get_assessment_or_404(session, assessment_id, current_user.id)

    if assessment.status != AssessmentStatus.COMPLETED.value:
        return AssessmentProgressResponse(
            assessmentId=assessment.id,
            status=AssessmentStatus(assessment.status),
            progressMessage=assessment.progress_message or "处理中",
            progressPercent=assessment.progress_percent,
            errorMessage=assessment.error_message,
        )

    return await _build_completed_response(session, assessment)


@router.get("/assessments/{assessment_id}/export.pdf", tags=["assessments"])
async def export_assessment_pdf(
    assessment_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_current_user),
) -> Response:
    """
    导出评估报告为 PDF 文件

    - 仅当评估状态为 COMPLETED 时允许导出
    - 使用 weasyprint 或其他 PDF 引擎生成
    - 文件名格式: yasi-assessment-{id}.pdf
    """
    assessment = await _get_assessment_or_404(session, assessment_id, current_user.id)
    if assessment.status != AssessmentStatus.COMPLETED.value:
        raise HTTPException(status_code=409, detail="结果尚未完成，暂时不能导出 PDF")

    payload = await _build_completed_response(session, assessment)
    pdf_bytes = build_assessment_pdf(payload, topic=assessment.topic, task_type=assessment.task_type)
    filename = f'yasi-assessment-{assessment.id}.pdf'
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==================== 历史记录与错题本 ====================

@router.get("/history", response_model=HistoryResponse, tags=["history"])
async def history(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_current_user),
) -> HistoryResponse:
    """获取当前用户的历史评估列表（按时间倒序）"""
    return await get_history(session, current_user.id)


@router.get("/notebook", response_model=NotebookResponse, tags=["notebook"])
async def notebook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_current_user),
) -> NotebookResponse:
    """获取当前用户的错题本（所有错误条目及摘要统计）"""
    return await get_notebook(session, current_user.id)


@router.post(
    "/notebook/items/{item_id}/review",
    response_model=NotebookReviewResponse,
    tags=["notebook"],
)
async def review_notebook(
    item_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_current_user),
) -> NotebookReviewResponse:
    """
    标记错题本某一条目为“已复习”

    - 更新条目状态为 reviewed
    - 记录复习时间
    """
    try:
        return await review_notebook_item(session, item_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/profile", response_model=ProfileResponse, tags=["profile"])
async def profile(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_current_user),
) -> ProfileResponse:
    """获取当前用户的综合画像（平均分、常见错误、学习路径等）"""
    return await get_profile(session, current_user.id)