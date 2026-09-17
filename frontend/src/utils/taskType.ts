import type { TaskType } from "@/types/api";

export function formatTaskType(taskType?: string): string {
  if (taskType === "task1_academic") return "任务一（学术类）";
  if (taskType === "task1_general") return "任务一（培训类）";
  return "任务二";
}

export function buildTaskTypeOptions(): Array<{ label: string; value: TaskType }> {
  return [
    { label: "任务一（学术类）", value: "task1_academic" },
    { label: "任务一（培训类）", value: "task1_general" },
    { label: "任务二", value: "task2" }
  ];
}
