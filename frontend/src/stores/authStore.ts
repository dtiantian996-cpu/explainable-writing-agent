import { defineStore } from "pinia";
import axios from "axios";
import { http, normalizeHttpError } from "@/api/http";
import { useAssessmentStore } from "@/stores/assessmentStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useNotebookStore } from "@/stores/notebookStore";
import type {
  AuthLoginPayload,
  AuthRegisterPayload,
  AuthSessionResponse,
  AuthUser
} from "@/types/api";

const AUTH_SNAPSHOT_KEY = "yasi-auth-user";

let hydratePromise: Promise<AuthUser | null> | null = null;

function readCachedUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(AUTH_SNAPSHOT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    window.localStorage.removeItem(AUTH_SNAPSHOT_KEY);
    return null;
  }
}

function cacheUser(user: AuthUser | null) {
  if (typeof window === "undefined") return;
  if (user) {
    window.localStorage.setItem(AUTH_SNAPSHOT_KEY, JSON.stringify(user));
    return;
  }
  window.localStorage.removeItem(AUTH_SNAPSHOT_KEY);
}

function resetWorkspaceStores() {
  useAssessmentStore().$reset();
  useHistoryStore().$reset();
  useNotebookStore().$reset();
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as AuthUser | null,
    initialized: false,
    loading: false,
    submitting: false,
    errorMessage: ""
  }),
  getters: {
    isAuthenticated(state): boolean {
      return !!state.user;
    },
    userInitial(state): string {
      return state.user?.displayName.slice(0, 1).toUpperCase() ?? "Y";
    }
  },
  actions: {
    clearError() {
      this.errorMessage = "";
    },
    setUser(user: AuthUser | null) {
      this.user = user;
      cacheUser(user);
    },
    async fetchMe() {
      this.loading = true;
      this.errorMessage = "";
      try {
        const { data } = await http.get<AuthSessionResponse>("/api/auth/me");
        this.setUser(data.user);
        this.initialized = true;
        return data.user;
      } catch (error) {
        this.initialized = true;
        this.setUser(null);
        if (axios.isAxiosError(error) && error.response?.status === 401) {
          return null;
        }
        this.errorMessage = normalizeHttpError(error, "获取登录状态失败");
        return null;
      } finally {
        this.loading = false;
      }
    },
    async ensureSession(force = false) {
      if (this.initialized && !force) {
        return this.user;
      }

      if (typeof navigator !== "undefined" && navigator.onLine === false) {
        const cachedUser = readCachedUser();
        this.setUser(cachedUser);
        this.initialized = true;
        return cachedUser;
      }

      if (hydratePromise) {
        return hydratePromise;
      }

      hydratePromise = this.fetchMe().finally(() => {
        hydratePromise = null;
      });
      return hydratePromise;
    },
    async register(payload: AuthRegisterPayload) {
      this.submitting = true;
      this.errorMessage = "";
      try {
        const { data } = await http.post<AuthSessionResponse>("/api/auth/register", payload);
        resetWorkspaceStores();
        this.setUser(data.user);
        this.initialized = true;
        return true;
      } catch (error) {
        this.setUser(null);
        this.errorMessage = normalizeHttpError(error, "注册失败");
        return false;
      } finally {
        this.submitting = false;
      }
    },
    async login(payload: AuthLoginPayload) {
      this.submitting = true;
      this.errorMessage = "";
      try {
        const { data } = await http.post<AuthSessionResponse>("/api/auth/login", payload);
        resetWorkspaceStores();
        this.setUser(data.user);
        this.initialized = true;
        return true;
      } catch (error) {
        this.setUser(null);
        this.errorMessage = normalizeHttpError(error, "登录失败");
        return false;
      } finally {
        this.submitting = false;
      }
    },
    async logout() {
      this.submitting = true;
      this.errorMessage = "";
      try {
        await http.post("/api/auth/logout");
      } catch (error) {
        this.errorMessage = normalizeHttpError(error, "退出登录失败");
      } finally {
        resetWorkspaceStores();
        this.setUser(null);
        this.initialized = true;
        this.submitting = false;
      }
    }
  }
});
