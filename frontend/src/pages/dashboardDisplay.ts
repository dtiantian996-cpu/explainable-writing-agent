import type { HistoryItem } from "@/types/api";
import { formatTaskType } from "@/utils/taskType";

export function buildDashboardHeroMeta(hasFetched: boolean, latestRecord: HistoryItem | null): string {
  if (!hasFetched) return "正在读取最近完成记录";
  if (!latestRecord) return "最近还没有完成的作文";
  return "最近一篇已完成";
}

export function buildDashboardPreviewTitle(index: number): string {
  return `最近评估 ${String(index + 1).padStart(2, "0")}`;
}

export function buildDashboardPreviewMeta(item: HistoryItem): string {
  if (item.status === "completed") {
    return `${formatTaskType(item.taskType)} · 已完成`;
  }
  if (item.status === "failed") {
    return `${formatTaskType(item.taskType)} · 失败`;
  }
  return `${formatTaskType(item.taskType)} · 进行中`;
}
