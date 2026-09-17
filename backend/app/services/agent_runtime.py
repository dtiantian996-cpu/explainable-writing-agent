"""
智能体运行时模块

核心职责：
1. 封装四个专业智能体（Language、Discourse、Scoring、Tutor）的调用逻辑
2. 管理 Mock 模式与真实 DeepSeek API 的切换
3. 提供 Prompt 模板（system_prompt）和结构化输出约束
4. 实现报告合并（merge_reports）用于主管智能体融合结果
5. 包含建议定位修正函数（normalize_suggestions）保证高亮准确性
"""

from __future__ import annotations

from pydantic import BaseModel

from app.core.config import get_settings
from app.schemas.assessment import (
    DiscourseAgentOutput,
    HighlightItem,
    LanguageAgentOutput,
    Report,
    SuggestionItem,
)
from app.services.deepseek import DeepSeekClient
from app.services.mock_assessment import (
    EssayFeatures,
    build_features,
    generate_highlights,
    generate_profile,
    generate_report,
    generate_suggestions,
)
from app.services.scoring import average_ielts_band


class TutorResponse(BaseModel):
    """
    辅导智能体返回的标准化结构
    - suggestions: 逐句修改建议列表（错误定位+解释+改写）
    - highlights: 作文亮点列表（高级词汇、优秀表达）
    - learningPath: 个性化学习路径建议（字符串列表）
    """
    suggestions: list[SuggestionItem]
    highlights: list[HighlightItem]
    learningPath: list[str]


def normalize_suggestions(text: str, suggestions: list[SuggestionItem]) -> list[SuggestionItem]:
    """
    修正建议中的位置索引，确保高亮在原文中能准确定位。

    因为 LLM 返回的 positionStart/positionEnd 可能与实际文本有偏移（如空格、换行差异），
    该函数通过原文模糊匹配重新计算正确的位置。

    参数：
        text: 原始作文文本
        suggestions: LLM 返回的建议列表（可能包含不准确的位置）

    返回：
        修正后的建议列表，positionStart/positionEnd 指向 text 中的正确区间
    """
    normalized: list[SuggestionItem] = []
    lower_text = text.lower()
    search_cursor = 0

    for item in suggestions:
        start = item.positionStart
        end = item.positionEnd
        excerpt = item.sourceText.strip()  # 待匹配的原文片段

        # 如果片段为空，则使用文本前32个字符作为后备
        if not excerpt:
            excerpt = text[:32].strip() or "essay"

        # 检查 LLM 返回的索引是否有效且匹配
        current_slice = text[start:end].strip() if 0 <= start < len(text) and end <= len(text) else ""
        if start < 0 or end <= start or current_slice.lower() != excerpt.lower():
            # 索引无效或不匹配，执行模糊查找
            lowered_excerpt = excerpt.lower()
            found = lower_text.find(lowered_excerpt, search_cursor)
            if found < 0:
                found = lower_text.find(lowered_excerpt)  # 从头找
            if found >= 0:
                start = found
                end = found + len(excerpt)
                search_cursor = end  # 更新游标，避免重复匹配同一片段
            else:
                # 实在找不到，退化为首位置（避免崩溃）
                start = 0
                end = min(len(text), max(len(excerpt), 1))

        # 使用 model_copy 更新位置字段，保留其他字段不变
        normalized.append(
            item.model_copy(
                update={
                    "positionStart": start,
                    "positionEnd": end,
                }
            )
        )
    return normalized


class AgentRuntime:
    """
    智能体运行时 - 多智能体协同的核心执行器

    职责：
    1. 根据配置（use_mock_ai / deepseek_enabled）决定使用真实 LLM 还是 Mock 数据
    2. 为每个智能体构建专属的 system_prompt 和 user_prompt
    3. 调用 DeepSeekClient 获取结构化输出，并转换为标准 Schema
    4. 提供 build_features 辅助方法（提取作文特征，如词数、句数等）

    与 Prompt 工程的关系：
    - 每个智能体的 system_prompt 明确了角色、输出格式、字段约束
    - user_prompt 中可注入 RAG 知识上下文（knowledge_context）
    - 使用 JSON Schema 强制输出结构，避免自由文本
    """

    def __init__(self) -> None:
        self.settings = get_settings()  # 全局配置（API Key、Mock 开关等）
        self.deepseek = DeepSeekClient()  # DeepSeek API 客户端

    def build_features(self, topic: str, text: str) -> EssayFeatures:
        """提取作文特征（词数、句子数、常见错误统计等），供 Mock 模式使用"""
        return build_features(topic, text)

    def _context_block(self, knowledge_context: str | None) -> str:
        """将 RAG 知识上下文格式化为可注入 Prompt 的字符串"""
        return "" if not knowledge_context else f"参考上下文:\n{knowledge_context}\n\n"

    # ==================== 语言智能体 ====================
    async def language_agent(self, topic: str, text: str, knowledge_context: str | None = None) -> Report:
        """
        语言智能体：评估语法准确性与多样性

        仅输出 grammar_accuracy 维度，其他维度使用 Mock 数据填充。
        若 use_mock_ai 或 DeepSeek 不可用，直接返回 Mock 报告。
        """
        features = self.build_features(topic, text)
        base_report = generate_report(features)  # Mock 基础报告
        if self.settings.use_mock_ai or not self.settings.deepseek_enabled:
            return base_report

        # ---- Prompt 工程 ----
        system_prompt = (
            "你是 IELTS 写作语法评分 agent。"
            "你只能返回一个 JSON 对象，不要输出 markdown，不要解释。"
            'JSON 结构必须是 {"grammar_accuracy":{"score": number, "reasonBullets":["..."]}}。'
            "score 取值 0-9，可以保留 1 位小数；reasonBullets 必须提供 3 条简洁中文理由。"
        )
        user_prompt = (
            "请只评估 grammar_accuracy，不要返回其他维度。\n"
            f"{self._context_block(knowledge_context)}"  # 注入 RAG 知识
            f"题目: {topic}\n作文:\n{text}\n"
        )
        # 调用 DeepSeek 结构化输出，解析为 LanguageAgentOutput
        response = await self.deepseek.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=LanguageAgentOutput,
        )
        # 合并：语法用 LLM 结果，其他维度用 Mock 数据
        return Report(
            grammar_accuracy=response.grammar_accuracy,
            task_response=base_report.task_response,
            coherence_cohesion=base_report.coherence_cohesion,
            lexical_resource=base_report.lexical_resource,
        )

    # ==================== 篇章智能体 ====================
    async def discourse_agent(self, topic: str, text: str, knowledge_context: str | None = None) -> Report:
        """
        篇章智能体：评估任务完成度（task_response）和连贯与衔接（coherence_cohesion）
        """
        features = self.build_features(topic, text)
        base_report = generate_report(features)
        if self.settings.use_mock_ai or not self.settings.deepseek_enabled:
            return base_report

        system_prompt = (
            "你是 IELTS 写作结构与逻辑评分 agent。"
            "你只能返回一个 JSON 对象，不要输出 markdown，不要解释。"
            'JSON 结构必须是 {"task_response":{"score": number, "reasonBullets":["..."]},'
            '"coherence_cohesion":{"score": number, "reasonBullets":["..."]}}。'
            "每个维度提供 3 条简洁中文理由。"
        )
        user_prompt = (
            "请只评估 task_response 和 coherence_cohesion。\n"
            f"{self._context_block(knowledge_context)}"
            f"题目: {topic}\n作文:\n{text}\n"
        )
        response = await self.deepseek.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=DiscourseAgentOutput,
        )
        return Report(
            grammar_accuracy=base_report.grammar_accuracy,
            task_response=response.task_response,
            coherence_cohesion=response.coherence_cohesion,
            lexical_resource=base_report.lexical_resource,
        )

    # ==================== 评分智能体 ====================
    async def scoring_agent(self, topic: str, text: str, knowledge_context: str | None = None) -> Report:
        """
        评分智能体：综合四个维度给出完整评分报告
        """
        features = self.build_features(topic, text)
        if self.settings.use_mock_ai or not self.settings.deepseek_enabled:
            return generate_report(features)

        system_prompt = (
            "你是 IELTS 写作总评分 agent。"
            "你只能返回一个 JSON 对象，不要输出 markdown，不要解释。"
            'JSON 结构必须包含 grammar_accuracy、task_response、coherence_cohesion、lexical_resource，'
            '每个维度都必须是 {"score": number, "reasonBullets":["..."]}，每项提供 3 条简洁中文理由。'
        )
        user_prompt = (
            "请按 IELTS 四维完整返回 JSON。\n"
            f"{self._context_block(knowledge_context)}"
            f"题目: {topic}\n作文:\n{text}\n"
        )
        # 直接返回 Report 结构（包含四个维度）
        return await self.deepseek.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=Report,
        )

    # ==================== 辅导智能体 ====================
    async def tutor_agent(self, topic: str, text: str, knowledge_context: str | None = None) -> TutorResponse:
        """
        辅导智能体：生成修改建议、亮点识别和学习路径

        输出 TutorResponse，其中 suggestions 和 highlights 需要经过 normalize_suggestions
        修正位置索引，确保前端高亮准确。
        """
        features = self.build_features(topic, text)
        report = generate_report(features)
        suggestions = generate_suggestions(features)
        highlights = generate_highlights(features)
        profile = generate_profile(features, report, suggestions)

        if self.settings.use_mock_ai or not self.settings.deepseek_enabled:
            return TutorResponse(
                suggestions=suggestions,
                highlights=highlights,
                learningPath=profile.learningPath,
            )

        # ---- 复杂的 Prompt 工程 ----
        system_prompt = (
            "你是 IELTS 写作讲评 agent。"
            "你只能返回一个 JSON 对象，不要输出 markdown，不要解释。"
            '顶层结构必须是 {"suggestions":[...], "highlights":[...], "learningPath":["..."]}。'
            'suggestions 每项必须包含 errorType, sourceText, explanation, revision, revisedSentence, positionStart, positionEnd。'
            '其中 errorType 只能使用 grammar、task_response、coherence、lexical 四个稳定键；'
            "sourceText 和 revisedSentence 保持英文原句/改写句，explanation 与 revision 必须是中文。"
            'highlights 每项必须包含 type, location, explanation, encouragement。'
            '其中 type 只能使用 advanced_vocabulary、cohesive_device、clear_position、supporting_example 四个稳定键；'
            "location 保持原文片段，explanation 与 encouragement 必须是中文。"
            "suggestions 给 3-5 条，highlights 给 2-4 条，learningPath 给 3 条，learningPath 也必须是中文。"
        )
        user_prompt = (
            "请对以下作文生成逐句建议与亮点。\n"
            f"{self._context_block(knowledge_context)}"
            f"题目: {topic}\n作文:\n{text}\n"
        )
        response = await self.deepseek.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=TutorResponse,
        )
        # 修正建议中的位置索引，确保高亮准确
        return TutorResponse(
            suggestions=normalize_suggestions(text, response.suggestions),
            highlights=response.highlights,
            learningPath=response.learningPath,
        )


def merge_reports(*reports: Report) -> Report:
    """
    合并多个智能体的报告（用于主管融合节点）

    策略：
    - 每个维度的最终得分 = 各报告该维度得分的平均分（使用 IELTS band 平均算法）
    - 理由列表 = 各报告理由的并集，最多保留4条（避免过长）

    参数：
        *reports: 至少一个 Report 对象（通常传入 language_report, discourse_report, scoring_report）

    返回：
        融合后的 Report 对象
    """
    merged_reports = list(reports)
    if not merged_reports:
        raise ValueError("at least one report is required")

    def merge_dimension(name: str):
        # 提取所有报告中该维度的对象
        dimensions = [getattr(report, name) for report in merged_reports]
        # 得分取平均
        score = average_ielts_band(item.score for item in dimensions)
        # 理由去重合并
        reasons: list[str] = []
        for item in dimensions:
            for bullet in item.reasonBullets:
                if bullet not in reasons:
                    reasons.append(bullet)
        # 返回新的维度对象（使用第一个报告的类型，通常所有维度的类相同）
        return dimensions[0].__class__(score=score, reasonBullets=reasons[:4])

    return Report(
        grammar_accuracy=merge_dimension("grammar_accuracy"),
        task_response=merge_dimension("task_response"),
        coherence_cohesion=merge_dimension("coherence_cohesion"),
        lexical_resource=merge_dimension("lexical_resource"),
    )