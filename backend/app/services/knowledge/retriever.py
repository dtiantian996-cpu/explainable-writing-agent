"""用于评估参考上下文的 RAG 检索服务。

检索器会查询本地 Chroma 知识库，并可选使用 DashScope 对结果重排，
然后为每个 AI Agent 准备独立的上下文字符串。即使检索被禁用或降级，
工作流也可以继续安全执行。
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from app.core.config import get_settings
from app.schemas.assessment import KnowledgeSource, KnowledgeStatus
from app.schemas.common import TaskType
from app.services.text_analyzer import normalize_whitespace, safe_excerpt


LOGGER = logging.getLogger(__name__)
DEFAULT_COLLECTION_NAME = "rag_knowledge_base"
TYPE_QUOTAS = {
    "scoring_criteria": 1,
    "high_score_essay": 2,
    "error_case": 2,
    "example_essay": 1,
    "grammar_knowledge": 1,
    "writing_template": 1,
}
SELECTION_REASONS = {
    "scoring_criteria": "作为评分标准锚点",
    "high_score_essay": "作为高分结构与表达参考",
    "error_case": "作为典型失分模式参考",
    "example_essay": "作为常规展开方式参考",
    "grammar_knowledge": "作为语法知识点参考",
    "writing_template": "作为结构模板参考",
}
MANDATORY_TYPES = ("scoring_criteria",)


@dataclass(frozen=True)
class AgentContexts:
    """为每个评估智能体定制的 Prompt 上下文片段。"""

    language: str
    discourse: str
    scoring: str
    tutor: str


@dataclass(frozen=True)
class KnowledgeContextBundle:
    """LangGraph 工作流消费的完整知识检索结果。"""

    status: KnowledgeStatus
    task: str | None
    warnings: list[str]
    sources: list[KnowledgeSource]
    agent_contexts: AgentContexts


def task_type_to_ielts_task(task_type: str | TaskType) -> str:
    """将内部题型值映射为知识库中的雅思任务标签。"""

    normalized = task_type.value if isinstance(task_type, TaskType) else task_type
    if normalized in {TaskType.TASK1_ACADEMIC.value, TaskType.TASK1_GENERAL.value}:
        return "Task 1"
    return "Task 2"


class KnowledgeRetriever:
    """基于 Chroma 和 DashScope 的检索器，支持优雅降级。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        self._collection = None
        self._embeddings = None
        self._reranker = None

    @property
    def enabled(self) -> bool:
        """运行时配置中是否启用 RAG 检索。"""

        return self.settings.rag_enabled

    def disabled_bundle(self, *, task: str | None, warnings: list[str] | None = None) -> KnowledgeContextBundle:
        """当检索被禁用或不可用时，返回空的知识上下文包。"""

        return KnowledgeContextBundle(
            status=KnowledgeStatus.DISABLED,
            task=task,
            warnings=warnings or [],
            sources=[],
            agent_contexts=AgentContexts(language="", discourse="", scoring="", tutor=""),
        )

    def retrieve(self, *, task_type: str | TaskType, topic: str, essay_text: str) -> KnowledgeContextBundle:
        """检索参考资料，并转换为各智能体专属上下文。"""

        target_task = task_type_to_ielts_task(task_type)
        if not self.enabled:
            return self.disabled_bundle(task=target_task)

        warnings: list[str] = []
        if (task_type.value if isinstance(task_type, TaskType) else task_type) == TaskType.TASK1_GENERAL.value:
            warnings.append("Task 1 General 缺少独立语料，已回退到 Task 1 通用参考。")

        if not self.settings.dashscope_api_key:
            return self.disabled_bundle(
                task=target_task,
                warnings=["未配置 DASHSCOPE_API_KEY，已跳过知识检索。"],
            )

        if not self.settings.rag_chroma_dir.exists():
            return self.disabled_bundle(
                task=target_task,
                warnings=[f"知识库目录缺失：{self.settings.rag_chroma_dir}"],
            )

        try:
            sources = self._retrieve_sources(topic=topic, essay_text=essay_text, target_task=target_task)
        except ModuleNotFoundError as exc:
            return self.disabled_bundle(
                task=target_task,
                warnings=[f"RAG 依赖未安装：{exc.name}"],
            )
        except Exception as exc:  # pragma: no cover - guarded by integration tests and runtime fallback
            LOGGER.exception("knowledge retrieval failed")
            return KnowledgeContextBundle(
                status=KnowledgeStatus.FALLBACK,
                task=target_task,
                warnings=warnings + [f"知识检索失败，已降级为空上下文：{exc}"],
                sources=[],
                agent_contexts=AgentContexts(language="", discourse="", scoring="", tutor=""),
            )

        if not sources:
            return KnowledgeContextBundle(
                status=KnowledgeStatus.FALLBACK,
                task=target_task,
                warnings=warnings + ["未检索到足够匹配的参考资料，已回退为空上下文。"],
                sources=[],
                agent_contexts=AgentContexts(language="", discourse="", scoring="", tutor=""),
            )

        status = KnowledgeStatus.FALLBACK if warnings else KnowledgeStatus.ENABLED
        return KnowledgeContextBundle(
            status=status,
            task=target_task,
            warnings=warnings,
            sources=sources,
            agent_contexts=self._build_agent_contexts(sources),
        )

    def _get_collection(self):
        """延迟打开持久化 Chroma 集合。"""

        if self._collection is not None:
            return self._collection

        import chromadb
        from chromadb.config import Settings as ChromaSettings

        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.settings.rag_chroma_dir),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
            )
        self._collection = self._client.get_or_create_collection(
            name=DEFAULT_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def _get_embeddings(self):
        """延迟创建 DashScope Embedding 客户端。"""

        if self._embeddings is not None:
            return self._embeddings

        from langchain_community.embeddings import DashScopeEmbeddings

        self._embeddings = DashScopeEmbeddings(
            model="text-embedding-v3",
            dashscope_api_key=self.settings.dashscope_api_key,
        )
        return self._embeddings

    def _get_reranker(self):
        """延迟创建可选的 DashScope 重排序器。"""

        if self._reranker is not None:
            return self._reranker

        from langchain_community.document_compressors.dashscope_rerank import DashScopeRerank

        self._reranker = DashScopeRerank(
            model="ops-bge-reranker-larger",
            dashscope_api_key=self.settings.dashscope_api_key,
            top_n=self.settings.rag_top_k,
        )
        return self._reranker

    def _search_by_type(self, *, query_embedding: list[float], knowledge_type: str, target_task: str) -> list[dict[str, Any]]:
        """按知识类型检索，并在元数据可用时按雅思任务过滤。"""

        collection = self._get_collection()
        raw = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(2, self.settings.rag_recall_top_k),
            where={"type": knowledge_type},
            include=["documents", "metadatas", "distances"],
        )
        ids = raw.get("ids", [[]])[0]
        if not ids:
            return []

        docs: list[dict[str, Any]] = []
        for index, doc_id in enumerate(ids):
            metadata = dict(raw["metadatas"][0][index])
            ielts_task = metadata.get("ielts_task")
            if ielts_task and ielts_task != target_task:
                continue
            score = round(1 - raw["distances"][0][index], 4)
            docs.append(
                {
                    "id": doc_id,
                    "title": metadata.pop("title", ""),
                    "type": metadata.pop("type", knowledge_type),
                    "metadata": metadata,
                    "content": raw["documents"][0][index],
                    "score": score,
                }
            )
        return docs

    def _rerank(self, *, query: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """启用重排序时，对召回文档重新排序。"""

        if not docs or not self.settings.rag_rerank_enabled:
            return docs

        reranker = self._get_reranker()
        payload = [f"{doc['title']}\n{doc['content']}" for doc in docs]
        rerank_results = reranker.rerank(
            documents=payload,
            query=query,
            top_n=min(len(docs), self.settings.rag_top_k * 2),
        )

        reranked: list[dict[str, Any]] = []
        for item in rerank_results:
            index = item.get("index") if isinstance(item, dict) else getattr(item, "index", None)
            score = item.get("relevance_score") if isinstance(item, dict) else getattr(item, "relevance_score", None)
            if index is None or not (0 <= index < len(docs)):
                continue
            ranked = dict(docs[index])
            if score is not None:
                ranked["rerankScore"] = round(float(score), 4)
            reranked.append(ranked)
        return reranked or docs

    def _retrieve_sources(self, *, topic: str, essay_text: str, target_task: str) -> list[KnowledgeSource]:
        """完成召回、重排、按配额选择，并转换为知识来源结构。"""

        query = normalize_whitespace(f"{topic}\n{essay_text[:1800]}")
        embeddings = self._get_embeddings()
        query_embedding = embeddings.embed_query(query)

        pool_by_type: dict[str, list[dict[str, Any]]] = {knowledge_type: [] for knowledge_type in TYPE_QUOTAS}
        pool: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for knowledge_type in TYPE_QUOTAS:
            for doc in self._search_by_type(
                query_embedding=query_embedding,
                knowledge_type=knowledge_type,
                target_task=target_task,
            ):
                if doc["id"] in seen_ids:
                    continue
                seen_ids.add(doc["id"])
                pool.append(doc)
                pool_by_type[knowledge_type].append(doc)

        reranked_pool = self._rerank(query=query, docs=pool)
        selected_docs: list[dict[str, Any]] = []
        selected_ids: set[str] = set()
        per_type_count: dict[str, int] = {}
        for doc in reranked_pool:
            knowledge_type = doc["type"]
            quota = TYPE_QUOTAS.get(knowledge_type, 0)
            if quota <= 0:
                continue
            if per_type_count.get(knowledge_type, 0) >= quota:
                continue
            selected_docs.append(doc)
            selected_ids.add(doc["id"])
            per_type_count[knowledge_type] = per_type_count.get(knowledge_type, 0) + 1
            if len(selected_docs) >= self.settings.rag_top_k:
                break

        for knowledge_type in MANDATORY_TYPES:
            if per_type_count.get(knowledge_type, 0) > 0:
                continue
            fallback_doc = next((doc for doc in pool_by_type.get(knowledge_type, []) if doc["id"] not in selected_ids), None)
            if fallback_doc is None:
                continue
            selected_docs.insert(0, fallback_doc)
            selected_ids.add(fallback_doc["id"])
            per_type_count[knowledge_type] = 1

        selected_docs = selected_docs[: self.settings.rag_top_k]
        return [self._to_knowledge_source(doc) for doc in selected_docs]

    def _to_knowledge_source(self, doc: dict[str, Any]) -> KnowledgeSource:
        """将原始 Chroma 文档转换为对外使用的知识来源结构。"""

        knowledge_type = doc["type"]
        return KnowledgeSource(
            id=doc["id"],
            title=doc["title"] or knowledge_type,
            type=knowledge_type,
            score=doc["score"],
            rerankScore=doc.get("rerankScore"),
            ieltsTask=doc["metadata"].get("ielts_task"),
            excerpt=safe_excerpt(doc["content"], 220),
            selectionReason=SELECTION_REASONS.get(knowledge_type, "作为参考依据"),
        )

    def _build_agent_contexts(self, sources: list[KnowledgeSource]) -> AgentContexts:
        """准备注入各智能体 Prompt 的角色专属上下文块。"""

        body = "\n\n".join(
            [
                (
                    f"[{source.type}] {source.title}\n"
                    f"Task: {source.ieltsTask or 'General'}\n"
                    f"Reason: {source.selectionReason}\n"
                    f"Excerpt: {source.excerpt}"
                )
                for source in sources
            ]
        )
        base = (
            "以下是内部知识检索返回的参考摘要。它们只能作为 grounding context，"
            "不能替代当前作文本身，更不能虚构第二套评分结果。\n\n"
            f"{body}"
        )
        return AgentContexts(
            language=f"{base}\n\n请优先从 error_case 与 grammar_knowledge 中吸收语法和表达失误模式。",
            discourse=f"{base}\n\n请优先关注 scoring_criteria、high_score_essay 与 writing_template 的结构线索。",
            scoring=f"{base}\n\n请把这些内容仅作为评分参考锚点，最终评分必须基于当前作文本身。",
            tutor=f"{base}\n\n请把这些内容转换成更可执行的讲评与练习建议，而不是照抄参考答案。",
        )
