import type { AssessmentDraft } from "@/stores/assessmentStore";

export type SubmitPrimaryMode = "text" | "image";

export function buildPrimaryModeDraftPatch(mode: SubmitPrimaryMode): Partial<AssessmentDraft> {
  if (mode === "text") {
    return { images: [] };
  }

  return {
    essayText: "",
    taskType: "task2"
  };
}

export function shouldShowTaskTypeControls(mode: SubmitPrimaryMode): boolean {
  return mode === "text";
}
