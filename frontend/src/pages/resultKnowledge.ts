import type { AssessmentMeta, KnowledgeSource, KnowledgeStatus } from "@/types/api";

export function getKnowledgeStatusLabel(status?: KnowledgeStatus | null): string {
  if (status === "enabled") return "已启用";
  if (status === "fallback") return "降级";
  return "未启用";
}

export function getKnowledgeStatusClass(status?: KnowledgeStatus | null): string {
  if (status === "enabled") return "status-pill--success";
  if (status === "fallback") return "status-pill--warning";
  return "status-pill--info";
}

export function getKnowledgeBodyCopy(meta?: Pick<AssessmentMeta, "knowledgeStatus"> | null): string {
  if (meta?.knowledgeStatus === "enabled") {
    return "以下参考资料只作为 grounding context，最终评分、建议和亮点仍由多 Agent 主链独立生成。";
  }
  if (meta?.knowledgeStatus === "fallback") {
    return "知识检索已触发降级，系统会保留可用参考并继续完成评估，不会因为 RAG 波动中断主链。";
  }
  return "当前结果未启用知识检索，评估只基于作文正文与多 Agent 主链。";
}

export function getVisibleKnowledgeSources(
  sources?: KnowledgeSource[] | null,
  limit = 3
): KnowledgeSource[] {
  return (sources ?? []).slice(0, limit);
}
