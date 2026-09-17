"""
Mock 评估模块 – 规则驱动的模拟数据生成器

当系统配置了 YASI_USE_MOCK_AI=true 或 DeepSeek API 不可用时，
该模块提供基于启发式规则（而非 LLM）的评估结果，确保：
- 前端联调不依赖外网
- 演示环境可稳定运行
- 单元测试有确定性输出

所有生成的评分和建议仅用于开发/演示，不代表真实 AI 评估水平。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.schemas.assessment import (
    AssessmentMeta,
    HighlightItem,
    KnowledgeSource,
    KnowledgeStatus,
    NotebookSummary,
    ProfileDominantError,
    ProfileSnapshot,
    Report,
    ReportDimension,
    SuggestionItem,
)
from app.services.scoring import average_ielts_band, clamp_ielts_band
from app.services.text_analyzer import (
    advanced_hits,
    compute_word_count,
    extract_words,
    lexical_diversity,
    normalize_whitespace,
    paragraph_count,
    repeated_words,
    safe_excerpt,
    sentence_length_stats,
    split_sentences,
    transition_hits,
)


# ==================== 作文特征提取 ====================

@dataclass
class EssayFeatures:
    """
    从作文原文中提取的统计特征，用于规则打分

    Attributes:
        topic: 作文题目
        text: 规范化后的作文文本
        words: 单词列表（已分词）
        sentences: 句子列表
        word_count: 总词数
        diversity: 词汇多样性（唯一词数 / 总词数）
        transitions: 检测到的衔接词列表
        advanced_words: 检测到的高级词汇列表
        repeated: 高频重复词及其次数
        paragraphs: 段落数
        average_sentence_length: 平均句长
        sentence_spread: 句长标准差（衡量句式变化）
    """
    topic: str
    text: str
    words: list[str]
    sentences: list[str]
    word_count: int
    diversity: float
    transitions: list[str]
    advanced_words: list[str]
    repeated: list[tuple[str, int]]
    paragraphs: int
    average_sentence_length: float
    sentence_spread: float


def build_features(topic: str, text: str) -> EssayFeatures:
    """
    从原始作文中提取所有统计特征

    流程：
    1. 规范化空白字符（合并多余空格、换行）
    2. 分词、分句
    3. 计算各项指标（词数、多样性、衔接词、高级词、重复词、段落数、句长统计）

    所有后续 Mock 函数都依赖这些特征。
    """
    normalized = normalize_whitespace(text)
    words = extract_words(normalized)
    sentences = split_sentences(normalized)
    average, spread = sentence_length_stats(sentences)
    return EssayFeatures(
        topic=topic,
        text=normalized,
        words=words,
        sentences=sentences,
        word_count=compute_word_count(normalized),
        diversity=lexical_diversity(words),
        transitions=transition_hits(words),
        advanced_words=advanced_hits(words),
        repeated=repeated_words(words),
        paragraphs=paragraph_count(text),
        average_sentence_length=average,
        sentence_spread=spread,
    )


# ==================== 辅助评分函数 ====================

def _clamp_score(value: float) -> float:
    """将分数限制在 5.0 ~ 9.0 的雅思范围内"""
    return clamp_ielts_band(value, minimum=5.0, maximum=9.0)


def _report_dimension(score: float, bullets: list[str]) -> ReportDimension:
    """构造一个 ReportDimension 对象，自动钳位分数并限制理由条数最多 4 条"""
    return ReportDimension(score=_clamp_score(score), reasonBullets=bullets[:4])


# ==================== 生成四维评分报告 ====================

def generate_report(features: EssayFeatures) -> Report:
    """
    基于作文特征生成模拟的四维评估报告

    评分规则（启发式，仅供 Mock）：
    - grammar: 基础分 6.0 + 句长变化度/12 + 平均句长/25
    - task_response: 6.0 + 词数/180 + (0.4 如果段落≥3)
    - coherence: 6.0 + 衔接词数×0.3 + (0.4 如果段落≥4)
    - lexical: 6.0 + 词汇多样性×3 + 高级词汇数×0.2
    """
    grammar = 6.0 + min(features.sentence_spread / 12, 1.4) + min(features.average_sentence_length / 25, 0.8)
    task = 6.0 + min(features.word_count / 180, 1.2) + (0.4 if features.paragraphs >= 3 else 0.0)
    coherence = 6.0 + min(len(features.transitions) * 0.3, 0.9) + (0.4 if features.paragraphs >= 4 else 0.0)
    lexical = 6.0 + min(features.diversity * 3, 1.8) + min(len(features.advanced_words) * 0.2, 0.8)

    return Report(
        grammar_accuracy=_report_dimension(
            grammar,
            [
                f"句长变化为 {features.sentence_spread:.1f}，说明你已经尝试使用不同长度的句子。",
                "整体未见大面积碎句，但复杂句控制还可以更稳定。",
                "若能减少局部重复表达，语法准确性会更稳。",
            ],
        ),
        task_response=_report_dimension(
            task,
            [
                f"全文约 {features.word_count} 词，基本达到雅思写作的展开要求。",
                f"当前分为 {features.paragraphs} 段，主体结构已经具备。",
                "结论和立场表达较清楚，但论证层次仍可更紧。",
            ],
        ),
        coherence_cohesion=_report_dimension(
            coherence,
            [
                f"检测到 {len(features.transitions)} 个较明显的衔接词，段间连接意识是存在的。",
                "如果能在段首和句间建立更稳定的推进关系，整体会更顺。",
                "部分句子之间仍偏并列，逻辑递进还可以更明确。",
            ],
        ),
        lexical_resource=_report_dimension(
            lexical,
            [
                f"词汇多样率约为 {features.diversity:.2f}，说明你有一定替换意识。",
                f"检测到 {len(features.advanced_words)} 个较成熟的学术词或连接表达。",
                "少数高频词重复偏多，进一步替换能把词汇维度再往上推。",
            ],
        ),
    )


# ==================== 生成修改建议 ====================

def generate_suggestions(features: EssayFeatures) -> list[SuggestionItem]:
    """
    根据作文特征生成模拟的修改建议列表

    策略：
    - 针对高频重复词（前3个）生成词汇替换建议
    - 针对首句生成结构连贯性建议
    - 如果词数 < 220，生成增加例证的建议
    - 最多返回 5 条建议
    """
    suggestions: list[SuggestionItem] = []
    text = features.text

    # 高频重复词建议
    for word, count in features.repeated[:3]:
        start = text.lower().find(word)
        if start >= 0:
            suggestions.append(
                SuggestionItem(
                    errorType="lexical",
                    sourceText=word,
                    explanation=f"该词在全文中重复出现 {count} 次，词汇替换空间较大。",
                    revision="尝试用近义表达替换部分重复词，避免语义密度下降。",
                    revisedSentence=f"可将部分 {word} 改写为更具体的同义表达。",
                    positionStart=start,
                    positionEnd=start + len(word),
                )
            )

    # 首句建议（提升连贯性）
    if features.sentences:
        first_sentence = features.sentences[0]
        suggestions.append(
            SuggestionItem(
                errorType="coherence",
                sourceText=safe_excerpt(first_sentence, 72),
                explanation="开头句已经给出观点，但与下文的展开关系还可以更直接。",
                revision="在立场句后补一个明确的展开方向，帮助读者预判结构。",
                revisedSentence=f"{safe_excerpt(first_sentence, 60)} Therefore, the discussion should focus on both causes and practical solutions.",
                positionStart=0,
                positionEnd=min(len(first_sentence), 72),
            )
        )

    # 篇幅不足建议
    if features.word_count < 220:
        source = safe_excerpt(features.text, 80)
        suggestions.append(
            SuggestionItem(
                errorType="task_response",
                sourceText=source,
                explanation="篇幅略紧，导致论证层次偏少，影响任务完成度。",
                revision="每个主体段再增加一组原因或例子，让观点落地。",
                revisedSentence="Add one concrete example in each body paragraph to strengthen task response.",
                positionStart=0,
                positionEnd=min(len(features.text), 80),
            )
        )

    return suggestions[:5]


# ==================== 生成亮点 ====================

def generate_highlights(features: EssayFeatures) -> list[HighlightItem]:
    """
    根据作文特征生成模拟的亮点列表

    策略：
    - 高级词汇前3个 → 亮点类型 advanced_vocabulary
    - 衔接词前2个 → 亮点类型 cohesive_device
    - 最多 4 条亮点
    """
    highlights: list[HighlightItem] = []
    for word in features.advanced_words[:3]:
        highlights.append(
            HighlightItem(
                type="advanced_vocabulary",
                location=word,
                explanation=f"`{word}` 带有比较明显的学术语气，能抬高表达层级。",
                encouragement="这种词汇选择方向是对的，继续保持。",
            )
        )

    for transition in features.transitions[:2]:
        highlights.append(
            HighlightItem(
                type="cohesive_device",
                location=transition,
                explanation=f"`{transition}` 帮助句间衔接更自然。",
                encouragement="你已经有组织段落推进的意识了。",
            )
        )
    return highlights[:4]


# ==================== 生成用户画像快照 ====================

def generate_profile(features: EssayFeatures, report: Report, suggestions: list[SuggestionItem]) -> ProfileSnapshot:
    """
    根据本次评估结果生成模拟的用户画像快照

    - dominantErrors: 根据 suggestion 中的 errorType 统计错误频率
    - learningPath: 固定 3 条学习建议
    - nextTargetScore: 当前总分 + 0.5（不超过 8.0）
    - summaryNarrative: 固定中文总结
    """
    counter: dict[str, int] = {}
    for item in suggestions:
        counter[item.errorType] = counter.get(item.errorType, 0) + 1
    total = max(1, sum(counter.values()))
    dominant = [
        ProfileDominantError(type=key, count=value, share=round(value / total, 2))
        for key, value in sorted(counter.items(), key=lambda pair: pair[1], reverse=True)
    ]
    overall = average_ielts_band(
        [
            report.grammar_accuracy.score,
            report.task_response.score,
            report.coherence_cohesion.score,
            report.lexical_resource.score,
        ]
    )
    return ProfileSnapshot(
        dominantErrors=dominant,
        learningPath=[
            "先处理高频重复词，把词汇替换做稳定。",
            "补强主体段的例证，让任务完成度更扎实。",
            "继续练习连接词后的逻辑推进，减少并列堆叠。",
        ],
        nextTargetScore=clamp_ielts_band(overall + 0.5, maximum=8.0),
        summaryNarrative="当前短板集中在表达稳定性和论证展开，先把高频错误压下去，分数会更稳。",
    )


# ==================== 生成可视化图表数据 ====================

def generate_charts_data(
    report: Report,
    suggestions: list[SuggestionItem],
    highlights: list[HighlightItem],
    recent_scores: list[float],
) -> dict[str, Any]:
    """
    生成用于前端图表的数据结构

    返回字典包含：
    - radar: 四维雷达图数据
    - comparison: 与目标分数（7.5）的对比
    - wordCloud: 词云数据（基于亮点中的词汇）
    - heatmap: 章节热力图（简单模拟）
    - errorPortrait: 错误类型分布
    - trendLine: 历史分数趋势
    """
    error_counter: dict[str, int] = {}
    for item in suggestions:
        error_counter[item.errorType] = error_counter.get(item.errorType, 0) + 1

    radar = [
        {"dimension": "grammar_accuracy", "score": report.grammar_accuracy.score},
        {"dimension": "task_response", "score": report.task_response.score},
        {"dimension": "coherence_cohesion", "score": report.coherence_cohesion.score},
        {"dimension": "lexical_resource", "score": report.lexical_resource.score},
    ]
    comparison = [
        {"dimension": row["dimension"], "score": row["score"], "ieltsTarget": 7.5}
        for row in radar
    ]
    heatmap = [
        {"section": "introduction", "value": round(report.task_response.score / 9, 2)},
        {"section": "body", "value": round(report.coherence_cohesion.score / 9, 2)},
        {"section": "conclusion", "value": round(report.grammar_accuracy.score / 9, 2)},
    ]

    return {
        "radar": radar,
        "comparison": comparison,
        "wordCloud": [
            {"text": item.location, "weight": 8 + index * 2} for index, item in enumerate(highlights)
        ],
        "heatmap": heatmap,
        "errorPortrait": [{"type": key, "count": value} for key, value in error_counter.items()],
        "trendLine": recent_scores,
    }


# ==================== 生成评估元信息 ====================

def generate_meta(
    features: EssayFeatures,
    source_mode: str,
    *,
    knowledge_status: KnowledgeStatus = KnowledgeStatus.DISABLED,
    knowledge_task: str | None = None,
    knowledge_warnings: list[str] | None = None,
    knowledge_sources: list[KnowledgeSource] | None = None,
) -> AssessmentMeta:
    """
    构造评估元数据，包括来源模式、词数、生成时间、知识库状态等

    knowledge_status 默认 DISABLED，在 Mock 模式下不会真正检索知识库。
    """
    return AssessmentMeta(
        sourceMode=source_mode,
        wordCount=features.word_count,
        generatedAt=datetime.now(UTC).isoformat(),
        knowledgeStatus=knowledge_status,
        knowledgeTask=knowledge_task,
        knowledgeWarnings=knowledge_warnings or [],
        knowledgeSources=knowledge_sources or [],
    )


# ==================== 生成错题本摘要 ====================

def generate_notebook_summary(suggestions: list[SuggestionItem]) -> NotebookSummary:
    """
    根据本次评估的建议列表生成错题本摘要

    - totalItems: 建议总数
    - reviewedItems: 固定 0（Mock 模式下不处理复习状态）
    - pendingReviewCount: 等于总数
    - dominantErrorType: 出现最多的错误类型
    """
    if not suggestions:
        return NotebookSummary(totalItems=0, reviewedItems=0, pendingReviewCount=0, dominantErrorType="none")

    counter: dict[str, int] = {}
    for item in suggestions:
        counter[item.errorType] = counter.get(item.errorType, 0) + 1
    dominant = max(counter.items(), key=lambda pair: pair[1])[0]
    return NotebookSummary(
        totalItems=len(suggestions),
        reviewedItems=0,
        pendingReviewCount=len(suggestions),
        dominantErrorType=dominant,
    )