import { defineStore } from "pinia";
import { http, normalizeHttpError } from "@/api/http";
import type { HistoryItem } from "@/types/api";

function normalizeHistoryPayload(payload: unknown): HistoryItem[] {
  if (Array.isArray(payload)) return payload as HistoryItem[];
  if (payload && typeof payload === "object") {
    const candidate = payload as Record<string, unknown>;
    if (Array.isArray(candidate.items)) return candidate.items as HistoryItem[];
  }
  return [];
}

export const useHistoryStore = defineStore("history", {
  state: () => ({
    items: [] as HistoryItem[],
    hasFetched: false,
    loading: false,
    errorMessage: ""
  }),
  getters: {
    latestRecord(state): HistoryItem | null {
      return state.items.length ? state.items[0] : null;
    },
    latestCompletedRecord(state): HistoryItem | null {
      return state.items.find((item) => item.status === "completed") ?? null;
    }
  },
  actions: {
    async fetchHistory() {
      this.loading = true;
      this.errorMessage = "";
      try {
        const { data } = await http.get<unknown>("/api/history");
        this.items = normalizeHistoryPayload(data);
        this.hasFetched = true;
      } catch (error) {
        this.hasFetched = true;
        this.errorMessage = normalizeHttpError(error, "获取历史记录失败");
      } finally {
        this.loading = false;
      }
    }
  }
});
