import { defineStore } from "pinia";
import { http, normalizeHttpError } from "@/api/http";
import type {
  AssessmentCompletedResponse,
  AssessmentCreateResponse,
  AssessmentProgressResponse,
  TaskType
} from "@/types/api";

export type SubmitState = "idle" | "creating" | "polling" | "failed" | "completed";

export interface AssessmentDraft {
  topic: string;
  taskType: TaskType;
  essayText: string;
  images: File[];
}

function isCompletedResponse(payload: unknown): payload is AssessmentCompletedResponse {
  if (!payload || typeof payload !== "object") return false;
  const candidate = payload as Record<string, unknown>;
  return "meta" in candidate && "report" in candidate && "suggestions" in candidate;
}

export const useAssessmentStore = defineStore("assessment", {
  state: () => ({
    draft: {
      topic: "",
      taskType: "task2",
      essayText: "",
      images: []
    } as AssessmentDraft,
    submitState: "idle" as SubmitState,
    currentAssessmentId: "",
    progressMessage: "",
    progressPercent: 0,
    result: null as AssessmentCompletedResponse | null,
    errorMessage: ""
  }),
  getters: {
    wordCount(state): number {
      return state.draft.essayText.trim().split(/\s+/).filter(Boolean).length;
    }
  },
  actions: {
    updateDraft(patch: Partial<AssessmentDraft>) {
      this.draft = { ...this.draft, ...patch };
    },
    resetDraft() {
      this.draft = {
        topic: "",
        taskType: "task2",
        essayText: "",
        images: []
      };
    },
    setCurrentAssessment(id: string) {
      this.currentAssessmentId = id;
    },
    clearResult() {
      this.result = null;
      this.errorMessage = "";
      this.progressMessage = "";
      this.progressPercent = 0;
      this.submitState = "idle";
    },
    async createAssessment() {
      this.submitState = "creating";
      this.result = null;
      this.errorMessage = "";
      this.progressMessage = "";
      this.progressPercent = 0;

      try {
        const formData = new FormData();
        formData.set("topic", this.draft.topic);
        formData.set("task_type", this.draft.taskType);
        if (this.draft.essayText.trim()) {
          formData.set("essay_text", this.draft.essayText);
        }
        for (const image of this.draft.images) {
          formData.append("images", image);
        }

        const { data } = await http.post<AssessmentCreateResponse>("/api/assessments", formData);
        this.currentAssessmentId = data.assessmentId;
        this.submitState = "polling";
        this.progressPercent = 5;
        this.progressMessage = "任务已创建";
        return data.assessmentId;
      } catch (error) {
        this.submitState = "failed";
        this.errorMessage = normalizeHttpError(error, "创建评估任务失败");
        return "";
      }
    },
    async fetchAssessmentStatus(assessmentId?: string) {
      const targetId = assessmentId ?? this.currentAssessmentId;
      if (!targetId) return null;

      if (targetId !== this.currentAssessmentId) {
        this.currentAssessmentId = targetId;
        this.result = null;
        this.errorMessage = "";
        this.progressMessage = "";
        this.progressPercent = 0;
      }

      try {
        const { data } = await http.get<AssessmentProgressResponse | AssessmentCompletedResponse>(
          `/api/assessments/${targetId}`
        );

        if (isCompletedResponse(data)) {
          this.result = data;
          this.submitState = "completed";
          this.progressPercent = 100;
          this.progressMessage = "评估已完成";
          return data;
        }

        if (data.status === "failed") {
          this.submitState = "failed";
          this.errorMessage = data.errorMessage ?? "评估任务失败";
          this.progressPercent = data.progressPercent;
          this.progressMessage = data.progressMessage;
          return data;
        }

        this.submitState = "polling";
        this.progressPercent = data.progressPercent;
        this.progressMessage = data.progressMessage;
        return data;
      } catch (error) {
        this.submitState = "failed";
        this.errorMessage = normalizeHttpError(error, "获取评估状态失败");
        return null;
      }
    }
  }
});
