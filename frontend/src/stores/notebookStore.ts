import { defineStore } from "pinia";
import { http, normalizeHttpError } from "@/api/http";
import type { NotebookItem, NotebookResponse, NotebookSummary } from "@/types/api";

export type ReviewActionState = "idle" | "submitting" | "success" | "error";

function normalizeNotebookPayload(payload: unknown): NotebookResponse {
  if (payload && typeof payload === "object") {
    const candidate = payload as Record<string, unknown>;
    if (Array.isArray(candidate.items) && candidate.summary && typeof candidate.summary === "object") {
      return {
        items: candidate.items as NotebookItem[],
        summary: candidate.summary as NotebookSummary
      };
    }
  }
  if (Array.isArray(payload)) {
    return {
      items: payload as NotebookItem[],
      summary: {
        totalItems: payload.length,
        reviewedItems: 0,
        pendingReviewCount: payload.length,
        dominantErrorType: "none"
      }
    };
  }
  return {
    items: [],
    summary: {
      totalItems: 0,
      reviewedItems: 0,
      pendingReviewCount: 0,
      dominantErrorType: "none"
    }
  };
}

function isReviewed(item: NotebookItem): boolean {
  return item.status === "reviewed";
}

function buildSummary(items: NotebookItem[], fallback: NotebookSummary): NotebookSummary {
  const reviewedItems = items.filter(isReviewed).length;
  return {
    totalItems: items.length,
    reviewedItems,
    pendingReviewCount: items.length - reviewedItems,
    dominantErrorType: fallback.dominantErrorType
  };
}

function updateReviewedItem(items: NotebookItem[], id: string): NotebookItem[] {
  return items.map((item) => (item.id === id ? { ...item, status: "reviewed" } : item));
}

export const useNotebookStore = defineStore("notebook", {
  state: () => ({
    items: [] as NotebookItem[],
    summary: {
      totalItems: 0,
      reviewedItems: 0,
      pendingReviewCount: 0,
      dominantErrorType: "none"
    } as NotebookSummary,
    hasFetched: false,
    loading: false,
    selectedItemId: "",
    reviewActionState: "idle" as ReviewActionState,
    errorMessage: ""
  }),
  getters: {
    selectedItem(state): NotebookItem | null {
      return state.items.find((item) => item.id === state.selectedItemId) ?? null;
    }
  },
  actions: {
    selectItem(id: string) {
      this.selectedItemId = id;
    },
    async fetchNotebook() {
      this.loading = true;
      this.errorMessage = "";
      try {
        const { data } = await http.get<unknown>("/api/notebook");
        const normalized = normalizeNotebookPayload(data);
        this.items = normalized.items;
        this.summary = buildSummary(normalized.items, normalized.summary);
        this.hasFetched = true;
        if (!this.selectedItemId && this.items.length) {
          this.selectedItemId = this.items[0].id;
        }
      } catch (error) {
        this.hasFetched = true;
        this.errorMessage = normalizeHttpError(error, "获取错题本失败");
      } finally {
        this.loading = false;
      }
    },
    async markReviewed(id: string) {
      this.reviewActionState = "submitting";
      this.errorMessage = "";
      try {
        await http.post(`/api/notebook/items/${id}/review`);
        this.items = updateReviewedItem(this.items, id);
        this.summary = buildSummary(this.items, this.summary);
        this.reviewActionState = "success";
      } catch (error) {
        this.reviewActionState = "error";
        this.errorMessage = normalizeHttpError(error, "标记复习失败");
      }
    }
  }
});
