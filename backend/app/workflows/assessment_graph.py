"""
作文评估工作流 - 基于 LangGraph 的多智能体协同系统

核心流程：
1. 输入标准化（文本/OCR）
2. 检索知识库（RAG）增强上下文
3. 并行执行四个智能体（语言、篇章、评分、辅导）
4. 主管智能体融合结果
5. 持久化结果并提取错题本条目
6. 更新用户画像摘要

使用 LangGraph 的有向图（StateGraph）管理状态流转，支持并行执行。
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Assessment, AssessmentResult, NotebookItem
from app.schemas.assessment import (
    AssessmentMeta,
    HighlightItem,
    KnowledgeSource,
    KnowledgeStatus,
    NotebookSummary,
    ProfileSnapshot,
    Report,
    SuggestionItem,
)
from app.schemas.common import AssessmentStatus
from app.schemas.workflow import PROGRESS_MAP
from app.services.agent_runtime import AgentRuntime, merge_reports
from app.services.knowledge import KnowledgeRetriever, task_type_to_ielts_task
from app.services.localization import (
    canonicalize_charts_data,
    canonicalize_highlights,
    canonicalize_notebook_summary,
    canonicalize_profile_snapshot,
    canonicalize_suggestions,
)
from app.services.mock_assessment import (
    EssayFeatures,
    generate_charts_data,
    generate_meta,
    generate_notebook_summary,
    generate_profile,
)
from app.services.ocr import OCRService
from app.services.scoring import (
    average_ielts_band,
    normalize_charts_data_scores,
    normalize_profile_snapshot_scores,
    normalize_report_scores,
)
from app.services.storage import RuntimeStorage


# ===================== 状态定义（State） =====================
class AssessmentState(TypedDict, total=False):
    """
    工作流全局状态，所有节点共享。
    使用 TypedDict 定义键的类型，total=False 表示所有字段可选。
    每个节点可以读取/写入部分字段。
    """
    assessment_id: str           # 评估任务唯一标识
    user_id: str                 # 用户 ID
    topic: str                   # 作文题目
    task_type: str               # 写作类型（如雅思任务1/任务2）
    source_mode: str             # 输入来源：text / image
    essay_text: str | None       # 用户直接输入的文本
    image_paths: list[str]       # 上传的图片路径列表
    ocr_text: str                # 图片 OCR 识别结果
    normalized_text: str         # 标准化后的完整文本（输入文本 + OCR 合并）
    word_count: int              # 单词数
    knowledge_context: str       # RAG 检索到的参考上下文（注入 Prompt）
    knowledge_status: KnowledgeStatus  # 知识库状态：可用/降级/禁用等
    knowledge_task: str | None        # 检索时使用的任务类型（如 IELTS_TASK_2）
    knowledge_warnings: list[str]     # 检索过程中的警告信息
    knowledge_sources: list[KnowledgeSource]  # 知识来源引用（范文、评分标准等）
    agent_contexts: dict[str, str]    # 为各智能体准备的专属上下文（key: language, discourse, scoring, tutor）
    features: EssayFeatures           # 作文特征（词数、词频等）
    history_scores: list[float]       # 用户历史评估的总体得分（用于趋势图）
    # 四个智能体的输出报告
    language_report: Report           # 语言智能体输出（语法、词汇）
    discourse_report: Report          # 篇章智能体输出（连贯与衔接、结构）
    scoring_report: Report            # 评分智能体输出（综合评分）
    suggestions: list[SuggestionItem] # 辅导智能体输出的修改建议
    highlights: list[HighlightItem]   # 亮点识别
    learning_path: list[str]          # 个性化学习路径建议
    # 融合后的最终结果
    report: Report                    # 最终评估报告（合并后）
    charts_data: dict[str, Any]       # 可视化图表数据（雷达图、柱状图等）
    meta: AssessmentMeta              # 评估元信息（耗时、知识库使用情况等）
    profile_snapshot: ProfileSnapshot # 用户画像快照（错误分布、能力雷达）
    notebook_summary: NotebookSummary # 错题本摘要
    timings: dict[str, float]         # 各阶段耗时（用于性能监控）


def overall_score(report: Report) -> float:
    """计算报告的总体得分（四个维度的平均分，使用雅思 band 算法）"""
    return average_ielts_band(
        [
            report.grammar_accuracy.score,      # 语法准确性与多样性
            report.task_response.score,         # 任务完成度
            report.coherence_cohesion.score,    # 连贯与衔接
            report.lexical_resource.score,      # 词汇丰富度
        ]
    )


# ===================== 工作流主类 =====================
class AssessmentWorkflow:
    """
    作文评估工作流编排器
    职责：
    1. 构建 LangGraph 状态图
    2. 定义每个节点（Node）的处理逻辑
    3. 提供 run() 方法启动评估
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],  # 数据库会话工厂
        agent_runtime: AgentRuntime,                         # 智能体运行时（封装 LLM 调用）
        knowledge_retriever: KnowledgeRetriever,             # RAG 知识检索器
        ocr_service: OCRService,                             # OCR 识别服务
        storage: RuntimeStorage,                             # 文件存储服务（图片上传）
    ) -> None:
        self.session_factory = session_factory
        self.agent_runtime = agent_runtime
        self.knowledge_retriever = knowledge_retriever
        self.ocr_service = ocr_service
        self.storage = storage
        self.graph = self._build_graph()  # 编译 LangGraph 图

    def _build_graph(self):
        """构建状态图，定义节点和边"""
        graph = StateGraph(AssessmentState)

        # ----- 添加节点（每个节点是一个异步函数，接收并返回状态）-----
        graph.add_node("normalize_input", self.normalize_input)           # 1. 输入标准化
        graph.add_node("ocr_if_needed", self.ocr_if_needed)               # 2. 图片 OCR
        graph.add_node("knowledge_context_adapter", self.knowledge_context_adapter)  # 3. 知识检索
        graph.add_node("language_agent", self.language_agent)             # 4. 语言智能体
        graph.add_node("discourse_agent", self.discourse_agent)           # 5. 篇章智能体
        graph.add_node("scoring_agent", self.scoring_agent)               # 6. 评分智能体
        graph.add_node("tutor_agent", self.tutor_agent)                   # 7. 辅导智能体
        graph.add_node("supervisor_merge", self.supervisor_merge)         # 8. 主管融合
        graph.add_node("persist_results", self.persist_results)           # 9. 持久化结果
        graph.add_node("extract_notebook_items", self.extract_notebook_items)  # 10. 生成错题本
        graph.add_node("update_profile_summary", self.update_profile_summary)  # 11. 更新画像

        # ----- 定义边（执行顺序）-----
        graph.add_edge(START, "normalize_input")                    # 起点 -> 标准化
        graph.add_edge("normalize_input", "ocr_if_needed")          # 标准化 -> OCR
        graph.add_edge("ocr_if_needed", "knowledge_context_adapter") # OCR -> 知识检索

        # 知识检索完成后，并行启动四个智能体（同时执行）
        graph.add_edge("knowledge_context_adapter", "language_agent")
        graph.add_edge("knowledge_context_adapter", "discourse_agent")
        graph.add_edge("knowledge_context_adapter", "scoring_agent")
        graph.add_edge("knowledge_context_adapter", "tutor_agent")

        # 四个智能体全部完成后，汇聚到主管融合节点
        graph.add_edge("language_agent", "supervisor_merge")
        graph.add_edge("discourse_agent", "supervisor_merge")
        graph.add_edge("scoring_agent", "supervisor_merge")
        graph.add_edge("tutor_agent", "supervisor_merge")

        # 后续串行执行
        graph.add_edge("supervisor_merge", "persist_results")
        graph.add_edge("persist_results", "extract_notebook_items")
        graph.add_edge("extract_notebook_items", "update_profile_summary")
        graph.add_edge("update_profile_summary", END)               # 结束

        return graph.compile()  # 编译为可执行图

    # --------------------- 辅助方法 ---------------------
    async def _update_progress(
        self,
        session: AsyncSession,
        assessment_id: str,
        *,
        status: AssessmentStatus,
        stage: str,
        message: str,
    ) -> None:
        """更新评估任务的进度（用于前端轮询显示）"""
        assessment = await session.get(Assessment, assessment_id)
        if assessment is None:
            return
        assessment.status = status.value
        assessment.progress_message = message
        assessment.progress_percent = PROGRESS_MAP[stage]  # 预设的百分比映射
        assessment.updated_at = datetime.now(UTC).replace(tzinfo=None)
        if assessment.started_at is None and status == AssessmentStatus.PROCESSING:
            assessment.started_at = assessment.updated_at
        await session.commit()

    async def _load_history_scores(self, session: AsyncSession, user_id: str) -> list[float]:
        """加载用户最近3次评估的总体得分（用于趋势图）"""
        rows = await session.execute(
            select(AssessmentResult.report)
            .join(Assessment, Assessment.id == AssessmentResult.assessment_id)
            .where(Assessment.user_id == user_id, Assessment.status == AssessmentStatus.COMPLETED.value)
            .order_by(Assessment.created_at.desc())
            .limit(3)
        )
        scores: list[float] = []
        for report_data in rows.scalars():
            report = Report.model_validate(report_data)
            scores.append(overall_score(report))
        return list(reversed(scores))  # 按时间升序

    async def load_state(self, assessment_id: str) -> AssessmentState:
        """从数据库加载评估任务的基本信息，构造初始状态"""
        async with self.session_factory() as session:
            assessment = await session.get(Assessment, assessment_id)
            if assessment is None:
                raise ValueError(f"assessment {assessment_id} not found")
            image_paths = self.storage.list_uploads(assessment_id)  # 获取已上传的图片路径
            history_scores = await self._load_history_scores(session, assessment.user_id)
            return AssessmentState(
                assessment_id=assessment.id,
                user_id=assessment.user_id,
                topic=assessment.topic,
                task_type=assessment.task_type,
                source_mode=assessment.source_mode,
                essay_text=assessment.essay_text,
                image_paths=image_paths,
                history_scores=history_scores,
                timings={},
            )

    async def run(self, assessment_id: str) -> None:
        """启动评估工作流（外部调用入口）"""
        initial_state = await self.load_state(assessment_id)
        await self.graph.ainvoke(initial_state)  # 异步执行整个图

    # ===================== 节点实现 =====================

    async def normalize_input(self, state: AssessmentState) -> AssessmentState:
        """
        节点1：输入标准化
        - 去除文本首尾空白
        - 计算单词数
        - 更新数据库中的标准化文本和单词数
        """
        text = (state.get("essay_text") or "").strip()
        features = self.agent_runtime.build_features(state["topic"], text or "placeholder")
        async with self.session_factory() as session:
            await self._update_progress(
                session,
                state["assessment_id"],
                status=AssessmentStatus.PROCESSING,
                stage="normalize_input",
                message="正在标准化输入内容",
            )
            assessment = await session.get(Assessment, state["assessment_id"])
            if assessment is not None:
                assessment.normalized_text = text or None
                assessment.word_count = 0 if not text else len(features.words)
                assessment.updated_at = datetime.now(UTC).replace(tzinfo=None)
                await session.commit()
        return {
            "normalized_text": text,
            "word_count": len(features.words) if text else 0,
        }

    async def ocr_if_needed(self, state: AssessmentState) -> AssessmentState:
        """
        节点2：OCR 识别（仅当有图片时执行）
        - 调用 OCR 服务识别图片中的文字
        - 将识别结果与用户输入的文本合并
        - 如果两者都为空则抛出异常
        """
        started = perf_counter()
        ocr_text = ""
        ocr_error = ""
        if state.get("image_paths"):
            async with self.session_factory() as session:
                await self._update_progress(
                    session,
                    state["assessment_id"],
                    status=AssessmentStatus.PROCESSING,
                    stage="ocr_if_needed",
                    message="正在识别图片作文",
                )
            try:
                ocr_text = await self.ocr_service.read_images(state["image_paths"])
            except Exception as exc:  # pragma: no cover
                ocr_error = str(exc)

        normalized_text = state.get("normalized_text", "")
        if normalized_text and ocr_text:
            normalized_text = f"{normalized_text}\n\n{ocr_text}".strip()
        elif not normalized_text:
            normalized_text = ocr_text

        if not normalized_text:
            if ocr_error:
                raise ValueError(f"OCR 失败且未提供可评估文本: {ocr_error}")
            raise ValueError("OCR 失败且未提供可评估文本")

        features = self.agent_runtime.build_features(state["topic"], normalized_text)
        async with self.session_factory() as session:
            assessment = await session.get(Assessment, state["assessment_id"])
            if assessment is not None:
                assessment.ocr_text = ocr_text or None
                assessment.normalized_text = normalized_text
                assessment.word_count = features.word_count
                if ocr_error and state.get("essay_text"):
                    assessment.progress_message = "图片识别失败，已回退到文本主链路"
                assessment.updated_at = datetime.now(UTC).replace(tzinfo=None)
                await session.commit()

        timings = dict(state.get("timings", {}))
        timings["ocr_if_needed"] = round(perf_counter() - started, 3)
        return {
            "ocr_text": ocr_text,
            "normalized_text": normalized_text,
            "word_count": features.word_count,
            "features": features,
            "timings": timings,
        }

    async def knowledge_context_adapter(self, state: AssessmentState) -> AssessmentState:
        """
        节点3：知识检索适配器（RAG）
        - 根据任务类型、题目、作文文本检索相关知识（范文、评分标准等）
        - 为每个智能体生成专属的上下文提示
        - 处理超时或失败时的降级逻辑
        """
        started = perf_counter()
        async with self.session_factory() as session:
            await self._update_progress(
                session,
                state["assessment_id"],
                status=AssessmentStatus.PROCESSING,
                stage="agent_parallel_run",
                message="正在检索参考依据并启动多智能体",
            )
        try:
            bundle = await asyncio.wait_for(
                asyncio.to_thread(
                    self.knowledge_retriever.retrieve,
                    task_type=state["task_type"],
                    topic=state["topic"],
                    essay_text=state["normalized_text"],
                ),
                timeout=self.knowledge_retriever.settings.rag_timeout_seconds,
            )
        except TimeoutError:
            # 超时降级：返回空上下文，标记为 FALLBACK
            bundle = self.knowledge_retriever.disabled_bundle(task=task_type_to_ielts_task(state["task_type"]))
            bundle = bundle.__class__(
                status=KnowledgeStatus.FALLBACK,
                task=bundle.task,
                warnings=["知识检索超时，已跳过参考上下文。"],
                sources=[],
                agent_contexts=bundle.agent_contexts,
            )
        timings = dict(state.get("timings", {}))
        timings["knowledge_context_adapter"] = round(perf_counter() - started, 3)
        return {
            "knowledge_context": bundle.agent_contexts.scoring,
            "knowledge_status": bundle.status,
            "knowledge_task": bundle.task,
            "knowledge_warnings": bundle.warnings,
            "knowledge_sources": bundle.sources,
            "agent_contexts": {
                "language": bundle.agent_contexts.language,
                "discourse": bundle.agent_contexts.discourse,
                "scoring": bundle.agent_contexts.scoring,
                "tutor": bundle.agent_contexts.tutor,
            },
            "timings": timings,
        }

    async def language_agent(self, state: AssessmentState) -> AssessmentState:
        """
        节点4：语言智能体
        - 评估语法准确性与多样性、词汇丰富度
        - 返回 Report 结构（包含分项得分和评语）
        """
        report = await self.agent_runtime.language_agent(
            state["topic"],
            state["normalized_text"],
            state.get("agent_contexts", {}).get("language"),
        )
        return {"language_report": report}

    async def discourse_agent(self, state: AssessmentState) -> AssessmentState:
        """
        节点5：篇章智能体
        - 评估连贯与衔接、任务完成度、文章结构
        """
        report = await self.agent_runtime.discourse_agent(
            state["topic"],
            state["normalized_text"],
            state.get("agent_contexts", {}).get("discourse"),
        )
        return {"discourse_report": report}

    async def scoring_agent(self, state: AssessmentState) -> AssessmentState:
        """
        节点6：评分智能体
        - 综合各项指标给出总体得分（雅思 band 或百分制）
        """
        report = await self.agent_runtime.scoring_agent(
            state["topic"],
            state["normalized_text"],
            state.get("agent_contexts", {}).get("scoring"),
        )
        return {"scoring_report": report}

    async def tutor_agent(self, state: AssessmentState) -> AssessmentState:
        """
        节点7：辅导智能体
        - 生成逐句修改建议（错误定位、解释、修改后句子）
        - 识别作文亮点（高级词汇、优秀表达）
        - 生成个性化学习路径
        """
        tutor = await self.agent_runtime.tutor_agent(
            state["topic"],
            state["normalized_text"],
            state.get("agent_contexts", {}).get("tutor"),
        )
        return {
            "suggestions": tutor.suggestions,
            "highlights": tutor.highlights,
            "learning_path": tutor.learningPath,
        }

    async def supervisor_merge(self, state: AssessmentState) -> AssessmentState:
        """
        节点8：主管融合智能体
        - 合并四个智能体的输出
        - 归一化评分（确保一致性）
        - 生成可视化图表数据、用户画像快照、错题本摘要
        """
        started = perf_counter()
        async with self.session_factory() as session:
            await self._update_progress(
                session,
                state["assessment_id"],
                status=AssessmentStatus.PROCESSING,
                stage="supervisor_merge",
                message="多智能体正在整合评分理由",
            )
        # 合并三个评估报告（语言、篇章、评分）
        report = normalize_report_scores(
            merge_reports(
                state["language_report"],
                state["discourse_report"],
                state["scoring_report"],
            )
        )
        features = state["features"]
        suggestions = canonicalize_suggestions(state["suggestions"])
        highlights = canonicalize_highlights(state["highlights"])
        # 生成用户画像快照（错误分布、能力雷达）
        profile_snapshot = canonicalize_profile_snapshot(
            normalize_profile_snapshot_scores(generate_profile(features, report, suggestions))
        )
        # 生成图表数据（雷达图、趋势折线图、错误热力图等）
        charts_data = canonicalize_charts_data(
            normalize_charts_data_scores(
                generate_charts_data(
                    report,
                    suggestions,
                    highlights,
                    state.get("history_scores", []) + [overall_score(report)],
                )
            )
        )
        # 生成评估元信息
        meta = generate_meta(
            features,
            state["source_mode"],
            knowledge_status=state.get("knowledge_status", KnowledgeStatus.DISABLED),
            knowledge_task=state.get("knowledge_task"),
            knowledge_warnings=state.get("knowledge_warnings", []),
            knowledge_sources=state.get("knowledge_sources", []),
        )
        notebook_summary = canonicalize_notebook_summary(generate_notebook_summary(suggestions))
        timings = dict(state.get("timings", {}))
        timings["supervisor_merge"] = round(perf_counter() - started, 3)
        return {
            "suggestions": suggestions,
            "highlights": highlights,
            "report": report,
            "profile_snapshot": profile_snapshot,
            "charts_data": charts_data,
            "meta": meta,
            "notebook_summary": notebook_summary,
            "timings": timings,
        }

    async def persist_results(self, state: AssessmentState) -> AssessmentState:
        """
        节点9：持久化评估结果
        - 将融合后的报告、建议、图表等存入数据库
        - 更新评估任务状态为 COMPLETED
        """
        async with self.session_factory() as session:
            await self._update_progress(
                session,
                state["assessment_id"],
                status=AssessmentStatus.PROCESSING,
                stage="persist_results",
                message="正在保存评估结果",
            )
            now = datetime.now(UTC).replace(tzinfo=None)
            # 查询是否已有结果记录（防止重复写入）
            existing = await session.execute(
                select(AssessmentResult).where(AssessmentResult.assessment_id == state["assessment_id"])
            )
            result = existing.scalar_one_or_none()
            if result is None:
                result = AssessmentResult(
                    assessment_id=state["assessment_id"],
                    meta=state["meta"].model_dump(),
                    report=state["report"].model_dump(),
                    suggestions=[item.model_dump() for item in state["suggestions"]],
                    highlights=[item.model_dump() for item in state["highlights"]],
                    charts_data=state["charts_data"],
                    profile_snapshot=state["profile_snapshot"].model_dump(),
                    notebook_summary=state["notebook_summary"].model_dump(),
                    created_at=now,
                    updated_at=now,
                )
                session.add(result)
            else:
                result.meta = state["meta"].model_dump()
                result.report = state["report"].model_dump()
                result.suggestions = [item.model_dump() for item in state["suggestions"]]
                result.highlights = [item.model_dump() for item in state["highlights"]]
                result.charts_data = state["charts_data"]
                result.profile_snapshot = state["profile_snapshot"].model_dump()
                result.notebook_summary = state["notebook_summary"].model_dump()
                result.updated_at = now

            assessment = await session.get(Assessment, state["assessment_id"])
            if assessment is not None:
                assessment.status = AssessmentStatus.COMPLETED.value
                assessment.progress_message = "评估已完成"
                assessment.progress_percent = PROGRESS_MAP["completed"]
                assessment.completed_at = now
                assessment.updated_at = now
            await session.commit()
        return {}

    async def extract_notebook_items(self, state: AssessmentState) -> AssessmentState:
        """
        节点10：提取错题本条目
        - 清除该次评估已有的错题本记录（避免重复）
        - 将每条修改建议（错误类型、原文、解释、修改后句子）存入错题本
        """
        async with self.session_factory() as session:
            # 先删除该评估已有的错题记录（确保幂等性）
            existing_rows = await session.execute(
                select(NotebookItem).where(NotebookItem.assessment_id == state["assessment_id"])
            )
            for row in existing_rows.scalars().all():
                await session.delete(row)
            now = datetime.now(UTC).replace(tzinfo=None)
            for suggestion in state["suggestions"]:
                session.add(
                    NotebookItem(
                        user_id=state["user_id"],
                        assessment_id=state["assessment_id"],
                        error_type=suggestion.errorType,
                        source_text=suggestion.sourceText,
                        explanation=suggestion.explanation,
                        revision=suggestion.revision,
                        revised_sentence=suggestion.revisedSentence,
                        position_start=suggestion.positionStart,
                        position_end=suggestion.positionEnd,
                        status="new",          # 错题状态：new/reviewed/mastered
                        created_at=now,
                        updated_at=now,
                    )
                )
            await session.commit()
        return {}

    async def update_profile_summary(self, state: AssessmentState) -> AssessmentState:
        """
        节点11：更新用户画像摘要
        当前为空实现，实际可在此处异步更新用户的长期画像统计（错误分布趋势、能力成长曲线）
        """
        # TODO: 异步更新用户画像（如错误类型频率统计、能力雷达图聚合）
        return {}


# ===================== 辅助并行执行函数 =====================
async def run_parallel_agents(workflow: AssessmentWorkflow, state: AssessmentState) -> AssessmentState:
    """
    并行执行四个智能体（语言、篇章、评分、辅导）
    这是 LangGraph 图中四个独立节点的并行版本，可用于手动调用或测试。
    注意：实际工作流中已通过图边实现了并行，此函数保留作为备用。
    """
    language_report, discourse_report, scoring_report, tutor = await asyncio.gather(
        workflow.agent_runtime.language_agent(
            state["topic"],
            state["normalized_text"],
            state.get("agent_contexts", {}).get("language"),
        ),
        workflow.agent_runtime.discourse_agent(
            state["topic"],
            state["normalized_text"],
            state.get("agent_contexts", {}).get("discourse"),
        ),
        workflow.agent_runtime.scoring_agent(
            state["topic"],
            state["normalized_text"],
            state.get("agent_contexts", {}).get("scoring"),
        ),
        workflow.agent_runtime.tutor_agent(
            state["topic"],
            state["normalized_text"],
            state.get("agent_contexts", {}).get("tutor"),
        ),
    )
    return {
        "language_report": language_report,
        "discourse_report": discourse_report,
        "scoring_report": scoring_report,
        "suggestions": tutor.suggestions,
        "highlights": tutor.highlights,
        "learning_path": tutor.learningPath,
    }