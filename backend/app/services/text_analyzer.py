"""轻量级作文文本分析辅助函数。

这些函数用于支持 mock 评估生成、图表数据和 RAG 摘录处理，
并且不依赖额外的 NLP 包。
"""

from collections import Counter
import re


COMMON_WORDS = {
    "the",
    "and",
    "to",
    "of",
    "a",
    "in",
    "is",
    "it",
    "for",
    "that",
    "on",
    "with",
    "as",
    "are",
    "be",
    "this",
    "people",
}

TRANSITIONS = {"however", "moreover", "therefore", "consequently", "furthermore", "overall"}
ADVANCED_WORDS = {
    "substantial",
    "consequently",
    "perspective",
    "sustainable",
    "inevitable",
    "significant",
    "mitigate",
    "allocate",
    "compelling",
}


def normalize_whitespace(text: str) -> str:
    """压缩重复空白字符，让后续文本匹配更稳定。"""

    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    """根据标点将文本切分为简单句子片段。"""

    parts = re.split(r"(?<=[.!?])\s+", normalize_whitespace(text))
    return [part.strip() for part in parts if part.strip()]


def extract_words(text: str) -> list[str]:
    """提取小写英文单词 token。"""

    return re.findall(r"[A-Za-z']+", text.lower())


def compute_word_count(text: str) -> int:
    """统计文本中的英文单词数量。"""

    return len(extract_words(text))


def lexical_diversity(words: list[str]) -> float:
    """返回词汇多样性比例，供报告和图表使用。"""

    if not words:
        return 0.0
    return round(len(set(words)) / len(words), 4)


def repeated_words(words: list[str], limit: int = 5) -> list[tuple[str, int]]:
    """返回出现频率最高的非常见词。"""

    counts = Counter(word for word in words if len(word) > 3 and word not in COMMON_WORDS)
    return counts.most_common(limit)


def transition_hits(words: list[str]) -> list[str]:
    """查找作文中出现的衔接词。"""

    unique_words = set(words)
    return sorted(unique_words & TRANSITIONS)


def advanced_hits(words: list[str]) -> list[str]:
    """查找命中的预设高级词汇。"""

    unique_words = set(words)
    return sorted(unique_words & ADVANCED_WORDS)


def paragraph_count(text: str) -> int:
    """估算段落数量，至少返回 1。"""

    paragraphs = [part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]
    return max(1, len(paragraphs))


def sentence_length_stats(sentences: list[str]) -> tuple[float, float]:
    """返回平均句长和句长跨度，单位为单词数。"""

    if not sentences:
        return 0.0, 0.0
    lengths = [compute_word_count(sentence) for sentence in sentences]
    average = sum(lengths) / len(lengths)
    spread = max(lengths) - min(lengths) if lengths else 0.0
    return round(average, 2), round(spread, 2)


def safe_excerpt(text: str, max_length: int = 96) -> str:
    """返回压缩空白后的安全摘录，超长时用省略号截断。"""

    stripped = normalize_whitespace(text)
    if len(stripped) <= max_length:
        return stripped
    return stripped[: max_length - 3].rstrip() + "..."
