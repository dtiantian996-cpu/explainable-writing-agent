# ruff: noqa: E402

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.schemas.assessment import AssessmentCompletedResponse
from app.services.agent_runtime import AgentRuntime, merge_reports
from app.services.mock_assessment import (
    generate_charts_data,
    generate_meta,
    generate_notebook_summary,
    generate_profile,
)


@dataclass(frozen=True)
class SpikeEssay:
    slug: str
    topic: str
    text: str


@dataclass(frozen=True)
class SpikeResult:
    slug: str
    topic: str
    attempts: int
    elapsedSeconds: float
    overallScore: float
    suggestionCount: int
    highlightCount: int
    notebookItems: int
    dominantErrors: list[str]
    passed: bool
    error: str | None = None


SAMPLE_ESSAYS = [
    SpikeEssay(
        slug="task2-remote-work",
        topic="Some people think remote work should remain the main working model after the pandemic. To what extent do you agree or disagree?",
        text=(
            "In recent years, remote work has changed from a temporary response into a long-term option for many companies. "
            "I partly agree that it should remain a major working model after the pandemic, because it increases flexibility and reduces commuting pressure, "
            "but I do not believe it should replace office work completely.\n\n"
            "On the one hand, remote work offers clear advantages to both employees and employers. Workers can save time that would otherwise be wasted in traffic, "
            "and this often improves their overall work-life balance. In addition, companies may reduce office costs and attract talent from a wider geographical area. "
            "For example, a software firm can hire a skilled engineer from another city without forcing that person to relocate. This makes the labour market more efficient "
            "and allows businesses to respond faster to changing demands.\n\n"
            "On the other hand, a fully remote model can weaken communication and team cohesion. Certain discussions are more effective when colleagues meet face to face, "
            "especially when the task requires quick negotiation, creative brainstorming or close supervision of junior staff. Moreover, some employees struggle to separate "
            "their personal life from work when they stay at home all day. As a result, productivity may fall rather than rise if organisations rely on remote arrangements too heavily.\n\n"
            "In my view, the most practical solution is a balanced system in which remote work remains available but is combined with regular office attendance. "
            "This hybrid approach preserves flexibility while maintaining collaboration and accountability. Therefore, remote work should continue after the pandemic, "
            "yet it should be treated as a complementary model rather than the only one."
        ),
    ),
    SpikeEssay(
        slug="task1-academic-line-chart",
        topic="The chart below shows the number of students enrolled in online courses in three countries between 2010 and 2020. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
        text=(
            "The line chart compares the number of students who enrolled in online courses in three different countries from 2010 to 2020.\n\n"
            "Overall, the number of online learners rose in all three countries during the period shown. Country A experienced the fastest growth and finished with the highest figure, "
            "while Country C remained the lowest throughout the decade despite a gradual increase.\n\n"
            "In 2010, about 20,000 students in Country A took online courses. This figure climbed steadily to roughly 35,000 in 2014 and then rose more sharply, reaching approximately 70,000 by 2020. "
            "Country B started at around 15,000 students and increased at a more moderate pace. By the end of the period, it had reached just under 50,000.\n\n"
            "Country C had the smallest number of online learners at the beginning, with only about 8,000 students in 2010. Although the total increased every few years, the rise was relatively limited compared with the other two countries. "
            "By 2020, the figure had grown to around 25,000.\n\n"
            "It is also noticeable that the gap between Country A and the other two countries widened over time. While all three nations expanded access to online education, Country A appears to have invested in this area much more aggressively."
        ),
    ),
    SpikeEssay(
        slug="task2-public-transport",
        topic="Some people believe governments should spend more money on public transport, while others think building new roads is more important. Discuss both views and give your opinion.",
        text=(
            "People have different views about whether governments should prioritise public transport or spend more money on building new roads. "
            "Although road construction can solve some immediate traffic problems, I believe investment in public transport is a more effective long-term strategy.\n\n"
            "Those who support new roads often argue that growing cities need more physical capacity for cars, buses and delivery vehicles. In many urban areas, congestion is severe because road networks were designed decades ago for much smaller populations. "
            "If governments widen highways or build ring roads, traffic may move more smoothly and businesses can transport goods more efficiently. This can bring short-term economic benefits, especially in industrial regions.\n\n"
            "However, expanding road infrastructure rarely solves congestion permanently. When more roads are built, more people choose to drive, and the new space is quickly filled. By contrast, reliable public transport can carry far more passengers using less urban land. "
            "Subway systems, bus rapid transit and commuter rail services reduce the number of private vehicles on the road and also lower pollution levels. In addition, they provide affordable mobility for people who cannot drive, such as students, elderly residents and low-income workers.\n\n"
            "In my opinion, governments should still maintain road networks, but the larger share of funding ought to go to public transport. It improves accessibility, supports environmental goals and provides a more sustainable answer to population growth. "
            "Therefore, while roads remain necessary, public transport deserves greater public investment."
        ),
    ),
]


def overall_score(payload: AssessmentCompletedResponse) -> float:
    report = payload.report
    return round(
        (
            report.grammar_accuracy.score
            + report.task_response.score
            + report.coherence_cohesion.score
            + report.lexical_resource.score
        )
        / 4,
        1,
    )


async def run_single(runtime: AgentRuntime, essay: SpikeEssay) -> SpikeResult:
    elapsed = 0.0
    last_error = "unknown error"
    for attempt in range(1, 4):
        started = perf_counter()
        try:
            language_report, discourse_report, scoring_report, tutor = await asyncio.gather(
                runtime.language_agent(essay.topic, essay.text),
                runtime.discourse_agent(essay.topic, essay.text),
                runtime.scoring_agent(essay.topic, essay.text),
                runtime.tutor_agent(essay.topic, essay.text),
            )
            report = merge_reports(language_report, discourse_report, scoring_report)
            features = runtime.build_features(essay.topic, essay.text)
            profile = generate_profile(features, report, tutor.suggestions)
            charts_data = generate_charts_data(
                report,
                tutor.suggestions,
                tutor.highlights,
                [overall_score_placeholder(report)],
            )
            notebook_summary = generate_notebook_summary(tutor.suggestions)
            payload = AssessmentCompletedResponse.model_validate(
                {
                    "assessmentId": essay.slug,
                    "essayText": essay.text,
                    "meta": generate_meta(features, "text"),
                    "report": report.model_dump(),
                    "suggestions": [item.model_dump() for item in tutor.suggestions],
                    "highlights": [item.model_dump() for item in tutor.highlights],
                    "chartsData": charts_data,
                    "profile": profile.model_dump(),
                    "notebookSummary": notebook_summary.model_dump(),
                }
            )
            elapsed = round(perf_counter() - started, 3)
            return SpikeResult(
                slug=essay.slug,
                topic=essay.topic,
                attempts=attempt,
                elapsedSeconds=elapsed,
                overallScore=overall_score(payload),
                suggestionCount=len(payload.suggestions),
                highlightCount=len(payload.highlights),
                notebookItems=payload.notebookSummary.totalItems,
                dominantErrors=[row.type for row in payload.profile.dominantErrors],
                passed=True,
            )
        except Exception as exc:  # pragma: no cover - exercised by real spike run
            elapsed = round(perf_counter() - started, 3)
            message = str(exc).strip() or repr(exc)
            last_error = f"{type(exc).__name__}: {message} (attempt={attempt}, elapsed={elapsed}s)"
            if attempt < 3:
                await asyncio.sleep(attempt)

    return SpikeResult(
        slug=essay.slug,
        topic=essay.topic,
        attempts=3,
        elapsedSeconds=elapsed,
        overallScore=0.0,
        suggestionCount=0,
        highlightCount=0,
        notebookItems=0,
        dominantErrors=[],
        passed=False,
        error=last_error,
    )


def overall_score_placeholder(report) -> float:
    return round(
        (
            report.grammar_accuracy.score
            + report.task_response.score
            + report.coherence_cohesion.score
            + report.lexical_resource.score
        )
        / 4,
        1,
    )


def build_markdown(settings_model: str, results: list[SpikeResult]) -> str:
    passed = [item for item in results if item.passed]
    failed = [item for item in results if not item.passed]
    avg_elapsed = round(sum(item.elapsedSeconds for item in results) / len(results), 3)
    lines = [
        "# DeepSeek Structured Output Spike",
        "",
        f"- 时间: {datetime.now(UTC).isoformat()}",
        f"- 模型: `{settings_model}`",
        f"- 样例数: {len(results)}",
        f"- 成功数: {len(passed)}",
        f"- 失败数: {len(failed)}",
        f"- 平均耗时: {avg_elapsed}s",
        "",
        "## 明细",
        "",
        "| Essay | Passed | Attempts | Elapsed(s) | Score | Suggestions | Highlights | Dominant Errors |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in results:
        dominant = ", ".join(item.dominantErrors) if item.dominantErrors else "-"
        lines.append(
            f"| {item.slug} | {'yes' if item.passed else 'no'} | {item.attempts} | {item.elapsedSeconds:.3f} | {item.overallScore:.1f} | {item.suggestionCount} | {item.highlightCount} | {dominant} |"
        )
        if item.error:
            lines.append(f"| {item.slug}-error | - | - | - | - | - | - | `{item.error}` |")
    lines.extend(
        [
            "",
            "## 结论",
            "",
            "连续样例以现有 schema 进行整包校验；只有全部通过，才说明真机结构化输出稳定。",
        ]
    )
    return "\n".join(lines) + "\n"


async def main() -> int:
    settings = get_settings()
    if settings.use_mock_ai:
        print("YASI_USE_MOCK_AI=true，当前仍是 mock 模式，无法执行 DeepSeek 真机 Spike。", file=sys.stderr)
        return 1
    if not settings.deepseek_enabled:
        print("DEEPSEEK_API_KEY 未配置或仍为占位值，无法执行 DeepSeek 真机 Spike。", file=sys.stderr)
        return 1

    runtime = AgentRuntime()
    results = [await run_single(runtime, essay) for essay in SAMPLE_ESSAYS]

    verification_dir = REPO_ROOT / "verification"
    verification_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = verification_dir / f"deepseek-spike-{stamp}.json"
    md_path = verification_dir / f"deepseek-spike-{stamp}.md"
    json_payload = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "model": settings.deepseek_model,
        "results": [asdict(item) for item in results],
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(settings.deepseek_model, results), encoding="utf-8")

    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    for item in results:
        status = "PASS" if item.passed else "FAIL"
        print(f"[{status}] {item.slug} elapsed={item.elapsedSeconds:.3f}s score={item.overallScore:.1f}")
        if item.error:
            print(f"  error: {item.error}")

    return 0 if all(item.passed for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
