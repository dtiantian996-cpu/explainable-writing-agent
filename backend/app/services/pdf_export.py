"""PDF 评估报告导出服务。

该模块使用 ReportLab 将已完成的评估响应转换为可打印 PDF。
内容结构与结果页一致，包括总览分数、四维报告、修改建议、亮点和学习画像。
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.pdfbase.pdfmetrics import registerFont  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas import AssessmentCompletedResponse
from app.services.scoring import average_ielts_band, format_ielts_band

PAGE_WIDTH, PAGE_HEIGHT = A4
PAGE_MARGIN_X = 16 * mm
PAGE_MARGIN_TOP = 20 * mm
PAGE_MARGIN_BOTTOM = 16 * mm

GEIST_FONT = "Geist"
GEIST_SEMIBOLD_FONT = "GeistSemiBold"
GEIST_MONO_FONT = "GeistMono"
NOTO_FONT = "NotoSansSC"

_FONTS_REGISTERED = False


@dataclass(slots=True)
class ExportContext:
    """用于渲染 PDF 标题和元信息的小型上下文对象。"""

    topic: str
    task_type: str


class MetricBar(Flowable):
    """绘制带标签横向指标条的 ReportLab Flowable。"""

    def __init__(
        self,
        label: str,
        value_label: str,
        ratio: float,
        *,
        width: float = 170,
        bar_height: float = 8,
        tone: str = "#171717",
    ) -> None:
        super().__init__()
        self.label = label
        self.value_label = value_label
        self.ratio = max(0.0, min(1.0, ratio))
        self.width = width
        self.bar_height = bar_height
        self.tone = colors.HexColor(tone)
        self.height = 20

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        self.width = min(self.width, available_width)
        return self.width, self.height

    def draw(self) -> None:
        self.canv.setFont(GEIST_MONO_FONT, 8)
        self.canv.setFillColor(colors.HexColor("#666666"))
        self.canv.drawString(0, 12, self.label.upper())
        self.canv.drawRightString(self.width, 12, self.value_label)
        self.canv.setFillColor(colors.HexColor("#eeeeee"))
        self.canv.roundRect(0, 0, self.width, self.bar_height, self.bar_height / 2, fill=1, stroke=0)
        self.canv.setFillColor(self.tone)
        self.canv.roundRect(
            0,
            0,
            max(self.bar_height, self.width * self.ratio),
            self.bar_height,
            self.bar_height / 2,
            fill=1,
            stroke=0,
        )


def build_assessment_pdf(
    payload: AssessmentCompletedResponse,
    *,
    topic: str,
    task_type: str,
) -> bytes:
    _register_fonts()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=PAGE_MARGIN_X,
        rightMargin=PAGE_MARGIN_X,
        topMargin=PAGE_MARGIN_TOP,
        bottomMargin=PAGE_MARGIN_BOTTOM,
        title=f"YASI Assessment {payload.assessmentId}",
        author="YASI",
    )
    context = ExportContext(topic=topic, task_type=task_type)
    styles = _build_styles()
    story = _build_story(payload, context, styles)
    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_page_frame(canvas, doc, payload.assessmentId),
        onLaterPages=lambda canvas, doc: _draw_page_frame(canvas, doc, payload.assessmentId),
    )
    return buffer.getvalue()


def _register_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    font_dir = Path(__file__).resolve().parents[2] / "assets" / "fonts"
    registerFont(TTFont(GEIST_FONT, str(font_dir / "Geist-Regular.ttf")))
    registerFont(TTFont(GEIST_SEMIBOLD_FONT, str(font_dir / "Geist-SemiBold.ttf")))
    registerFont(TTFont(GEIST_MONO_FONT, str(font_dir / "GeistMono-Regular.ttf")))
    registerFont(TTFont(NOTO_FONT, str(font_dir / "NotoSansSC-Variable.ttf")))
    _FONTS_REGISTERED = True


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "YasiTitle",
            parent=base["Title"],
            fontName=NOTO_FONT,
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#171717"),
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "section": ParagraphStyle(
            "YasiSection",
            parent=base["Heading2"],
            fontName=NOTO_FONT,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#171717"),
            spaceAfter=0,
        ),
        "subsection": ParagraphStyle(
            "YasiSubsection",
            parent=base["Heading3"],
            fontName=NOTO_FONT,
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#171717"),
            spaceAfter=0,
        ),
        "body": ParagraphStyle(
            "YasiBody",
            parent=base["BodyText"],
            fontName=NOTO_FONT,
            fontSize=10.5,
            leading=16,
            textColor=colors.HexColor("#171717"),
            spaceAfter=0,
        ),
        "muted": ParagraphStyle(
            "YasiMuted",
            parent=base["BodyText"],
            fontName=NOTO_FONT,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#666666"),
            spaceAfter=0,
        ),
        "mono": ParagraphStyle(
            "YasiMono",
            parent=base["BodyText"],
            fontName=GEIST_MONO_FONT,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#666666"),
            spaceAfter=0,
        ),
        "metric": ParagraphStyle(
            "YasiMetric",
            parent=base["BodyText"],
            fontName=GEIST_SEMIBOLD_FONT,
            fontSize=18,
            leading=21,
            textColor=colors.HexColor("#171717"),
            alignment=TA_RIGHT,
            spaceAfter=0,
        ),
        "metric_label": ParagraphStyle(
            "YasiMetricLabel",
            parent=base["BodyText"],
            fontName=GEIST_MONO_FONT,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#666666"),
            spaceAfter=0,
        ),
        "center": ParagraphStyle(
            "YasiCenter",
            parent=base["BodyText"],
            fontName=NOTO_FONT,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#171717"),
        ),
        "right": ParagraphStyle(
            "YasiRight",
            parent=base["BodyText"],
            fontName=NOTO_FONT,
            fontSize=10,
            leading=14,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#171717"),
        ),
    }
    return styles


def _build_story(
    payload: AssessmentCompletedResponse,
    context: ExportContext,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    story: list[Flowable] = []
    overall_score = _compute_overall_score(payload)
    task_label = _format_task_type(context.task_type)

    story.extend(
        [
            Paragraph("YASI / IELTS Writing Report", styles["mono"]),
            Spacer(1, 4),
            Paragraph(_escape_paragraph(context.topic or "本次雅思写作评估"), styles["title"]),
            Spacer(1, 6),
            Paragraph(
                _escape_paragraph(
                    f"Assessment {payload.assessmentId} · {task_label} · {payload.meta.generatedAt}"
                ),
                styles["muted"],
            ),
            Spacer(1, 16),
            _build_summary_table(payload, overall_score, task_label, styles),
            Spacer(1, 18),
            _section_header("四维报告", "四个维度保持一套评分语言，不做花哨视觉复刻。", styles),
            Spacer(1, 10),
            _build_report_grid(payload, styles),
            Spacer(1, 18),
            _section_header("参考依据", "只保留 knowledge 状态、warning 和前三条来源。", styles),
            Spacer(1, 10),
        ]
    )
    story.extend(_build_knowledge_section(payload, styles))
    story.extend(
        [
            Spacer(1, 18),
            _section_header("逐句建议", "保留错误类型、解释、建议与改写句。", styles),
            Spacer(1, 10),
        ]
    )
    story.extend(_build_suggestions(payload, styles))
    story.extend(
        [
            Spacer(1, 18),
            _section_header("亮点分析", "保留鼓励性说明，但不灌水。", styles),
            Spacer(1, 10),
        ]
    )
    story.extend(_build_highlights(payload, styles))
    story.extend(
        [
            Spacer(1, 18),
            _section_header("学习结论与错题摘要", "长期问题、学习路径和错题沉淀集中展示。", styles),
            Spacer(1, 10),
            _build_profile_summary(payload, styles),
            Spacer(1, 18),
            _section_header("图表摘要", "用轻量条形摘要替代前端图表截图。", styles),
            Spacer(1, 10),
        ]
    )
    story.extend(_build_chart_summary(payload, styles))
    story.extend(
        [
            PageBreak(),
            _section_header("原文归档", "按段落排版，方便回看原文和建议是否匹配。", styles),
            Spacer(1, 10),
        ]
    )
    story.extend(_build_essay_archive(payload, styles))
    return story


def _section_header(title: str, description: str, styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [
            Paragraph(_escape_paragraph(title), styles["section"]),
            Paragraph(_escape_paragraph(description), styles["right"]),
        ]
    ]
    table = Table(data, colWidths=[95 * mm, None])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _build_summary_table(
    payload: AssessmentCompletedResponse,
    overall_score: float,
    task_label: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    cells = [
        ("总分", f"{format_ielts_band(overall_score)} / 9"),
        ("输入来源", _format_source_mode(payload.meta.sourceMode)),
        ("Task Type", task_label),
        ("字数", str(payload.meta.wordCount)),
        ("Assessment ID", payload.assessmentId),
        ("生成时间", payload.meta.generatedAt),
        ("知识检索", payload.meta.knowledgeStatus),
        ("下一目标", format_ielts_band(payload.profile.nextTargetScore)),
    ]
    rows = []
    for index in range(0, len(cells), 2):
        left = _build_summary_cell(cells[index][0], cells[index][1], styles)
        right = _build_summary_cell(cells[index + 1][0], cells[index + 1][1], styles)
        rows.append([left, right])
    table = Table(rows, colWidths=[None, None], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#ebebeb")),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#ebebeb")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _build_summary_cell(label: str, value: str, styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    value_style = styles["metric"] if label == "总分" else styles["subsection"]
    return [
        Paragraph(_escape_paragraph(label), styles["metric_label"]),
        Spacer(1, 4),
        Paragraph(_escape_paragraph(value), value_style),
    ]


def _build_report_grid(
    payload: AssessmentCompletedResponse,
    styles: dict[str, ParagraphStyle],
) -> Table:
    report_sections = [
        ("语法多样性与准确性", payload.report.grammar_accuracy),
        ("任务完成度", payload.report.task_response),
        ("连贯与衔接", payload.report.coherence_cohesion),
        ("词汇丰富度", payload.report.lexical_resource),
    ]
    cells = [
        _build_report_card(label, dimension.score, dimension.reasonBullets, styles)
        for label, dimension in report_sections
    ]
    table = Table([cells[:2], cells[2:]], colWidths=[None, None], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#ebebeb")),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#ebebeb")),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _build_report_card(
    label: str,
    score: float,
    bullets: Iterable[str],
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    flowables: list[Flowable] = [
        Paragraph(_escape_paragraph(label), styles["subsection"]),
        Spacer(1, 4),
        Paragraph(format_ielts_band(score), styles["metric"]),
        Spacer(1, 6),
    ]
    for bullet in bullets:
        flowables.append(Paragraph(_bullet_text(bullet), styles["body"]))
        flowables.append(Spacer(1, 4))
    if flowables[-1].__class__ is Spacer:
        flowables.pop()
    return flowables


def _build_knowledge_section(
    payload: AssessmentCompletedResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    content: list[Flowable] = [
        Paragraph(
            _escape_paragraph(
                f"knowledgeStatus: {payload.meta.knowledgeStatus} · knowledgeTask: {payload.meta.knowledgeTask or 'N/A'}"
            ),
            styles["body"],
        )
    ]
    if payload.meta.knowledgeWarnings:
        content.append(Spacer(1, 6))
        for warning in payload.meta.knowledgeWarnings:
            content.append(Paragraph(_bullet_text(warning), styles["body"]))
    sources = payload.meta.knowledgeSources[:3]
    if not sources:
        content.extend([Spacer(1, 8), Paragraph("当前没有稳定命中的参考资料。", styles["muted"])])
        return content
    for source in sources:
        content.extend(
            [
                Spacer(1, 10),
                _build_card(
                    [
                        Paragraph(_escape_paragraph(source.title), styles["subsection"]),
                        Spacer(1, 4),
                        Paragraph(
                            _escape_paragraph(
                                f"{source.type} · {source.ieltsTask or payload.meta.knowledgeTask or 'General'}"
                            ),
                            styles["mono"],
                        ),
                        Spacer(1, 6),
                        Paragraph(_escape_paragraph(source.selectionReason), styles["body"]),
                        Spacer(1, 4),
                        Paragraph(_escape_paragraph(source.excerpt), styles["muted"]),
                        Spacer(1, 4),
                        Paragraph(
                            _escape_paragraph(
                                f"检索分 {source.score:.2f}"
                                + (
                                    f" · 重排分 {source.rerankScore:.2f}"
                                    if source.rerankScore is not None
                                    else ""
                                )
                            ),
                            styles["mono"],
                        ),
                    ]
                )
            ]
        )
    return content


def _build_suggestions(
    payload: AssessmentCompletedResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    if not payload.suggestions:
        return [Paragraph("当前结果没有逐句建议条目。", styles["muted"])]
    flowables: list[Flowable] = []
    for item in payload.suggestions:
        card = _build_card(
            [
                Paragraph(_escape_paragraph(item.errorType), styles["subsection"]),
                Spacer(1, 4),
                Paragraph(
                    _escape_paragraph(f"位置 {item.positionStart} - {item.positionEnd}"),
                    styles["mono"],
                ),
                Spacer(1, 6),
                Paragraph(f"<b>原文：</b>{_escape_paragraph(item.sourceText)}", styles["body"]),
                Spacer(1, 4),
                Paragraph(f"<b>解释：</b>{_escape_paragraph(item.explanation)}", styles["body"]),
                Spacer(1, 4),
                Paragraph(f"<b>建议：</b>{_escape_paragraph(item.revision)}", styles["body"]),
                Spacer(1, 4),
                Paragraph(f"<b>改写句：</b>{_escape_paragraph(item.revisedSentence)}", styles["body"]),
            ]
        )
        flowables.extend([card, Spacer(1, 10)])
    flowables.pop()
    return flowables


def _build_highlights(
    payload: AssessmentCompletedResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    if not payload.highlights:
        return [Paragraph("当前结果没有独立亮点条目。", styles["muted"])]
    flowables: list[Flowable] = []
    for item in payload.highlights:
        card = _build_card(
            [
                Paragraph(_escape_paragraph(item.type), styles["subsection"]),
                Spacer(1, 4),
                Paragraph(_escape_paragraph(item.location), styles["mono"]),
                Spacer(1, 6),
                Paragraph(_escape_paragraph(item.explanation), styles["body"]),
                Spacer(1, 4),
                Paragraph(_escape_paragraph(item.encouragement), styles["muted"]),
            ]
        )
        flowables.extend([card, Spacer(1, 10)])
    flowables.pop()
    return flowables


def _build_profile_summary(
    payload: AssessmentCompletedResponse,
    styles: dict[str, ParagraphStyle],
) -> Table:
    dominant_errors = payload.profile.dominantErrors or []
    dominant_error_text = (
        "；".join(
            f"{item.type} {item.count} 条（{round(item.share * 100)}%）" for item in dominant_errors[:4]
        )
        if dominant_errors
        else "当前暂无稳定主导错误。"
    )
    learning_path = (
        "<br/>".join(
            f"{index + 1}. {_escape_paragraph(step)}" for index, step in enumerate(payload.profile.learningPath[:4])
        )
        if payload.profile.learningPath
        else "当前暂无稳定学习路径。"
    )
    notebook = payload.notebookSummary

    table = Table(
        [
            [
                _build_card(
                    [
                        Paragraph("长期结论", styles["subsection"]),
                        Spacer(1, 6),
                        Paragraph(_escape_paragraph(payload.profile.summaryNarrative), styles["body"]),
                        Spacer(1, 8),
                        Paragraph(
                            _escape_paragraph(f"下一目标 {format_ielts_band(payload.profile.nextTargetScore)}"),
                            styles["mono"],
                        ),
                    ]
                ),
                _build_card(
                    [
                        Paragraph("学习路径", styles["subsection"]),
                        Spacer(1, 6),
                        Paragraph(learning_path, styles["body"]),
                    ]
                ),
            ],
            [
                _build_card(
                    [
                        Paragraph("主导错误", styles["subsection"]),
                        Spacer(1, 6),
                        Paragraph(_escape_paragraph(dominant_error_text), styles["body"]),
                    ]
                ),
                _build_card(
                    [
                        Paragraph("错题摘要", styles["subsection"]),
                        Spacer(1, 6),
                        Paragraph(
                            _escape_paragraph(
                                f"累计 {notebook.totalItems} 条 · 已复习 {notebook.reviewedItems} 条 · 待复习 {notebook.pendingReviewCount} 条"
                            ),
                            styles["body"],
                        ),
                        Spacer(1, 4),
                        Paragraph(
                            _escape_paragraph(f"主导错题类型：{notebook.dominantErrorType}"),
                            styles["muted"],
                        ),
                    ]
                ),
            ],
        ],
        colWidths=[None, None],
    )
    table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _build_chart_summary(
    payload: AssessmentCompletedResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    flowables: list[Flowable] = []
    trend_line = payload.chartsData.get("trendLine") or []
    flowables.append(
        Paragraph(
            _escape_paragraph(
                "最近趋势："
                + (" → ".join(format_ielts_band(float(score)) for score in trend_line) if trend_line else "暂无历史趋势数据。")
            ),
            styles["body"],
        )
    )
    flowables.append(Spacer(1, 10))

    comparison = payload.chartsData.get("comparison") or []
    if comparison:
        flowables.append(Paragraph("评分对比", styles["subsection"]))
        flowables.append(Spacer(1, 6))
        for point in comparison[:4]:
            score = float(point.get("score", 0))
            target = max(float(point.get("ieltsTarget", 9)), 0.1)
            flowables.append(
                MetricBar(
                    point.get("dimension", "dimension"),
                    f"{format_ielts_band(score)} / {format_ielts_band(target)}",
                    score / target,
                    tone="#171717",
                )
            )
            flowables.append(Spacer(1, 6))

    error_portrait = payload.chartsData.get("errorPortrait") or []
    if error_portrait:
        flowables.append(Spacer(1, 4))
        flowables.append(Paragraph("错误画像", styles["subsection"]))
        flowables.append(Spacer(1, 6))
        max_count = max(int(item.get("count", 0)) for item in error_portrait[:4]) or 1
        tones = ["#8c2f2f", "#171717", "#8f4a00", "#456b8a"]
        for index, item in enumerate(error_portrait[:4]):
            count = int(item.get("count", 0))
            flowables.append(
                MetricBar(
                    item.get("type", "error"),
                    f"{count} 条",
                    count / max_count,
                    tone=tones[index % len(tones)],
                )
            )
            flowables.append(Spacer(1, 6))
    return flowables


def _build_essay_archive(
    payload: AssessmentCompletedResponse,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    paragraphs = [part.strip() for part in payload.essayText.split("\n\n") if part.strip()]
    if not paragraphs:
        return [Paragraph("当前没有可展示的原文内容。", styles["muted"])]
    flowables: list[Flowable] = []
    for paragraph in paragraphs:
        flowables.append(_build_card([Paragraph(_escape_paragraph(paragraph), styles["body"])]))
        flowables.append(Spacer(1, 10))
    flowables.pop()
    return flowables


def _build_card(flowables: list[Flowable]) -> Table:
    table = Table([[flowables]], colWidths=[None])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#ebebeb")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _draw_page_frame(canvas, document, assessment_id: str) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#ebebeb"))
    canvas.setLineWidth(0.6)
    canvas.line(PAGE_MARGIN_X, PAGE_HEIGHT - 12 * mm, PAGE_WIDTH - PAGE_MARGIN_X, PAGE_HEIGHT - 12 * mm)
    canvas.line(PAGE_MARGIN_X, 11 * mm, PAGE_WIDTH - PAGE_MARGIN_X, 11 * mm)

    canvas.setFillColor(colors.HexColor("#171717"))
    canvas.setFont(GEIST_SEMIBOLD_FONT, 9)
    canvas.drawString(PAGE_MARGIN_X, PAGE_HEIGHT - 9 * mm, "YASI / IELTS WRITING REPORT")

    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.setFont(GEIST_MONO_FONT, 8)
    canvas.drawRightString(PAGE_WIDTH - PAGE_MARGIN_X, PAGE_HEIGHT - 9 * mm, assessment_id.upper())
    canvas.drawString(PAGE_MARGIN_X, 7 * mm, "Generated by backend PDF export")
    canvas.drawRightString(PAGE_WIDTH - PAGE_MARGIN_X, 7 * mm, f"Page {document.page}")
    canvas.restoreState()


def _compute_overall_score(payload: AssessmentCompletedResponse) -> float:
    report = payload.report
    return average_ielts_band(
        [
            report.grammar_accuracy.score,
            report.task_response.score,
            report.coherence_cohesion.score,
            report.lexical_resource.score,
        ]
    )


def _format_task_type(task_type: str) -> str:
    if task_type == "task1_academic":
        return "Academic Task 1"
    if task_type == "task1_general":
        return "General Task 1"
    return "Task 2"


def _format_source_mode(source_mode: str) -> str:
    if source_mode == "image":
        return "图片 OCR 输入"
    if source_mode == "mixed":
        return "文本 + 图片混合"
    return "文本主输入"


def _escape_paragraph(value: str) -> str:
    return escape(value).replace("\n", "<br/>")


def _bullet_text(value: str) -> str:
    return f"- {_escape_paragraph(value)}"
