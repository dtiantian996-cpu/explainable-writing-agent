import { createPinia } from "pinia";

export const pinia = createPinia();

export function setupStore() {
  return pinia;
}

export { useAssessmentStore } from "./assessmentStore";
export { useAuthStore } from "./authStore";
export { useHistoryStore } from "./historyStore";
export { useNotebookStore } from "./notebookStore";
