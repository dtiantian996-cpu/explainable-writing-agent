# ruff: noqa: E402

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter


os.environ.setdefault("YASI_RAG_ENABLED", "true")

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.services.knowledge import KnowledgeRetriever


@dataclass(frozen=True)
class SpikeEssay:
    slug: str
    taskType: str
    topic: str
    text: str


@dataclass(frozen=True)
class SpikeResult:
    slug: str
    taskType: str
    status: str
    elapsedSeconds: float
    sourceCount: int
    sourceTypes: list[str]
    warnings: list[str]
    languageContextChars: int
    discourseContextChars: int
    scoringContextChars: int
    tutorContextChars: int
    passed: bool
    error: str | None = None


SAMPLE_ESSAYS = [
    SpikeEssay(
        slug="rag-task2-public-transport",
        taskType="task2",
        topic="Some people believe governments should spend more money on public transport, while others think building new roads is more important. Discuss both views and give your opinion.",
        text=(
            "People have different views about whether governments should prioritise public transport or spend more money on building new roads. "
            "Although road construction can solve some immediate traffic problems, I believe investment in public transport is a more effective long-term strategy.\n\n"
            "Those who support new roads often argue that growing cities need more physical capacity for cars, buses and delivery vehicles. "
            "In many urban areas, congestion is severe because road networks were designed decades ago for much smaller populations.\n\n"
            "However, expanding road infrastructure rarely solves congestion permanently. Reliable public transport can carry far more passengers using less urban land and reduce pollution at the same time."
        ),
    ),
    SpikeEssay(
        slug="rag-task1-academic-line-chart",
        taskType="task1_academic",
        topic="The chart below shows the number of students enrolled in online courses in three countries between 2010 and 2020. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
        text=(
            "The line chart compares the number of students who enrolled in online courses in three different countries from 2010 to 2020.\n\n"
            "Overall, the number of online learners rose in all three countries during the period shown. Country A experienced the fastest growth and finished with the highest figure, while Country C remained the lowest throughout the decade.\n\n"
            "In 2010, about 20,000 students in Country A took online courses. This figure climbed steadily before rising sharply to approximately 70,000 by 2020."
        ),
    ),
    SpikeEssay(
        slug="rag-task1-general-letter",
        taskType="task1_general",
        topic="You recently stayed at a hotel and were dissatisfied with the service. Write a letter to the manager. In your letter, explain what happened, describe how you were affected, and say what you would like the manager to do.",
        text=(
            "Dear Sir or Madam,\n\n"
            "I am writing to complain about the poor service I received during my stay at your hotel last weekend. "
            "Although I booked a quiet room in advance, I was placed next to a renovation area and could not sleep properly.\n\n"
            "As a result, I felt exhausted during an important meeting the following day. "
            "I would therefore like you to refund part of the room charge and explain how you plan to prevent similar problems in future.\n\n"
            "Yours faithfully,\nA Customer"
        ),
    ),
]


def build_markdown(results: list[SpikeResult], timeout_seconds: int) -> str:
    avg_elapsed = round(sum(item.elapsedSeconds for item in results) / len(results), 3)
    passed = sum(1 for item in results if item.passed)
    lines = [
        "# YASI RAG Spike",
        "",
        f"- 时间: {datetime.now(UTC).isoformat()}",
        f"- 样例数: {len(results)}",
        f"- 通过数: {passed}",
        f"- 平均耗时: {avg_elapsed}s",
        f"- 超时预算: {timeout_seconds}s",
        "",
        "## 明细",
        "",
        "| Essay | Task Type | Status | Passed | Elapsed(s) | Sources | Source Types | Warnings | Context Chars |",
        "|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for item in results:
        context_chars = "/".join(
            [
                str(item.languageContextChars),
                str(item.discourseContextChars),
                str(item.scoringContextChars),
                str(item.tutorContextChars),
            ]
        )
        warnings = "；".join(item.warnings) if item.warnings else "-"
        source_types = ", ".join(item.sourceTypes) if item.sourceTypes else "-"
        lines.append(
            f"| {item.slug} | {item.taskType} | {item.status} | {'yes' if item.passed else 'no'} | {item.elapsedSeconds:.3f} | {item.sourceCount} | {source_types} | {warnings} | {context_chars} |"
        )
        if item.error:
            lines.append(f"| {item.slug}-error | - | - | - | - | - | - | `{item.error}` | - |")
    lines.extend(
        [
            "",
            "## 判定标准",
            "",
            "- 至少命中 1 条 `scoring_criteria`",
            "- 总来源数 > 0",
            "- `task1_general` 必须出现回退 warning",
            "- 每篇检索耗时不应明显失控",
        ]
    )
    return "\n".join(lines) + "\n"


def evaluate_result(essay: SpikeEssay, status: str, source_types: list[str], warnings: list[str]) -> bool:
    if status not in {"enabled", "fallback"}:
        return False
    if not source_types:
        return False
    if "scoring_criteria" not in source_types:
        return False
    if essay.taskType == "task1_general":
        return any("回退" in warning or "缺少独立语料" in warning for warning in warnings)
    return True


def main() -> int:
    settings = get_settings()
    if not settings.dashscope_api_key:
        print("DASHSCOPE_API_KEY 未配置，无法执行 RAG live spike。", file=sys.stderr)
        return 1

    retriever = KnowledgeRetriever()
    results: list[SpikeResult] = []

    for essay in SAMPLE_ESSAYS:
        started = perf_counter()
        try:
            bundle = retriever.retrieve(task_type=essay.taskType, topic=essay.topic, essay_text=essay.text)
            elapsed = round(perf_counter() - started, 3)
            source_types = [source.type for source in bundle.sources]
            results.append(
                SpikeResult(
                    slug=essay.slug,
                    taskType=essay.taskType,
                    status=bundle.status.value,
                    elapsedSeconds=elapsed,
                    sourceCount=len(bundle.sources),
                    sourceTypes=source_types,
                    warnings=bundle.warnings,
                    languageContextChars=len(bundle.agent_contexts.language),
                    discourseContextChars=len(bundle.agent_contexts.discourse),
                    scoringContextChars=len(bundle.agent_contexts.scoring),
                    tutorContextChars=len(bundle.agent_contexts.tutor),
                    passed=evaluate_result(essay, bundle.status.value, source_types, bundle.warnings),
                )
            )
        except Exception as exc:  # pragma: no cover - live spike only
            elapsed = round(perf_counter() - started, 3)
            results.append(
                SpikeResult(
                    slug=essay.slug,
                    taskType=essay.taskType,
                    status="error",
                    elapsedSeconds=elapsed,
                    sourceCount=0,
                    sourceTypes=[],
                    warnings=[],
                    languageContextChars=0,
                    discourseContextChars=0,
                    scoringContextChars=0,
                    tutorContextChars=0,
                    passed=False,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    verification_dir = REPO_ROOT / "verification"
    verification_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = verification_dir / f"rag-spike-{stamp}.json"
    md_path = verification_dir / f"rag-spike-{stamp}.md"
    payload = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "results": [asdict(item) for item in results],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(results, settings.rag_timeout_seconds), encoding="utf-8")

    for item in results:
        print(
            f"[{'PASS' if item.passed else 'FAIL'}] {item.slug} "
            f"status={item.status} elapsed={item.elapsedSeconds:.3f}s "
            f"sources={item.sourceCount} warnings={len(item.warnings)}"
        )

    print(f"\nJSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 0 if all(item.passed for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
