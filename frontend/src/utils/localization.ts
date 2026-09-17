const tokenSepRe = /[\s\-/]+/g;

function tokenize(raw?: string | null): string {
  if (!raw) return "";
  return raw
    .trim()
    .toLowerCase()
    .replace(tokenSepRe, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function includesAny(raw: string, keywords: string[]): boolean {
  return keywords.some((keyword) => raw.includes(keyword));
}

export function localizeDimensionLabel(raw?: string | null): string {
  const token = tokenize(raw);
  if (includesAny(token, ["grammar", "grammatical"]) || includesAny(raw ?? "", ["语法"])) return "语法准确性";
  if (includesAny(token, ["task", "response"]) || includesAny(raw ?? "", ["任务"])) return "任务完成度";
  if (includesAny(token, ["cohere", "cohes"]) || includesAny(raw ?? "", ["连贯", "衔接"])) return "连贯与衔接";
  if (includesAny(token, ["lexical", "vocab"]) || includesAny(raw ?? "", ["词汇"])) return "词汇资源";
  return raw || "维度";
}

export function localizeErrorLabel(raw?: string | null): string {
  const token = tokenize(raw);
  if (token === "none" || raw === "暂无") return "暂无";
  if (includesAny(token, ["grammar", "grammatical"]) || includesAny(raw ?? "", ["语法"])) return "语法准确性";
  if (includesAny(token, ["task", "response"]) || includesAny(raw ?? "", ["任务"])) return "任务完成度";
  if (includesAny(token, ["cohere", "cohes"]) || includesAny(raw ?? "", ["连贯", "衔接"])) return "连贯与衔接";
  if (includesAny(token, ["lexical", "vocab"]) || includesAny(raw ?? "", ["词汇"])) return "词汇资源";
  return raw || "暂无";
}

export function localizeHighlightLabel(raw?: string | null): string {
  const token = tokenize(raw);
  if (includesAny(token, ["vocab", "lexical"]) || includesAny(raw ?? "", ["词汇"])) return "高级词汇使用";
  if (includesAny(token, ["cohes", "cohere"]) || includesAny(raw ?? "", ["衔接"])) return "衔接手段使用";
  if (includesAny(token, ["position"]) || includesAny(raw ?? "", ["立场"])) return "立场表达清晰";
  if (includesAny(token, ["example"]) || includesAny(raw ?? "", ["例子", "论证"])) return "论证例子有效";
  return raw || "表达亮点";
}

export function localizeKnowledgeSourceType(raw?: string | null): string {
  const token = tokenize(raw);
  if (includesAny(token, ["high_score_essay", "band_sample", "example_essay"]) || raw === "高分范文") {
    return "高分范文";
  }
  if (includesAny(token, ["scoring_criteria", "rubric"]) || raw === "评分标准") return "评分标准";
  if (includesAny(token, ["error_case"]) || raw === "错误案例") return "错误案例";
  if (includesAny(token, ["grammar_knowledge", "grammar_note"]) || raw === "语法知识") return "语法知识";
  if (includesAny(token, ["writing_template", "template"]) || raw === "写作模板") return "写作模板";
  return raw || "参考资料";
}

export function localizeHeatmapSection(raw?: string | null): string {
  const token = tokenize(raw);
  if (token === "introduction" || raw === "开头段") return "开头段";
  if (token === "conclusion" || raw === "结论段") return "结论段";
  if (token === "body" || raw === "主体段") return "主体段";
  return raw || "主体段";
}
