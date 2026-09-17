<template>
  <div class="app-shell">
    <aside class="workspace-sidebar" aria-label="Workspace">
      <div class="sidebar-header">
        <div class="brand-row">
          <span class="brand-mark">Y</span>
          <div>
            <p class="brand-name">YASI</p>
            <p class="brand-copy">IELTS Writing Lab</p>
          </div>
        </div>
        <p class="sidebar-kicker">Single-user training workspace</p>
      </div>

      <div class="sidebar-content">
        <p class="sidebar-section-title">学习工作台</p>
        <nav class="workflow-list">
          <RouterLink
            v-for="item in workflowItems"
            :key="item.label"
            :to="item.to"
            class="workflow-link"
            :class="{ 'is-active': activeWorkflow === item.workflow }"
          >
            <span class="workflow-icon">{{ item.icon }}</span>
            <span class="workflow-label">{{ item.label }}</span>
          </RouterLink>
        </nav>
      </div>

      <div class="sidebar-footer">
        <div class="brand-row">
          <span class="brand-mark">{{ authStore.userInitial }}</span>
          <div>
            <p class="brand-name">{{ userName }}</p>
            <p class="brand-copy">{{ userEmail }}</p>
          </div>
        </div>
      </div>
    </aside>

    <aside class="workspace-rail" aria-label="Collapsed workspace">
      <div class="rail-brand">Y</div>
      <div class="rail-stack">
        <RouterLink
          v-for="item in workflowItems"
          :key="item.workflow"
          :to="item.to"
          class="rail-link"
          :class="{ 'is-active': activeWorkflow === item.workflow }"
          :aria-label="item.label"
          :title="item.label"
        >
          <span class="rail-icon">{{ item.railIcon }}</span>
        </RouterLink>
      </div>
    </aside>

    <div class="workspace-panel">
      <header class="panel-topbar">
        <div class="topbar-brand-group">
          <p class="topbar-brand">YASI</p>
          <p class="topbar-copy">IELTS Writing Lab</p>
        </div>

        <nav class="topbar-nav" aria-label="Global">
          <RouterLink
            v-for="item in topbarItems"
            :key="item.key"
            :to="item.to"
            class="topbar-link"
            :class="{ 'is-active': activeTopbar === item.key }"
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <div class="topbar-meta">
          <span class="topbar-meta__usage">{{ userEmail }}</span>
          <button class="button-secondary topbar-logout" type="button" @click="void onLogout()">退出登录</button>
          <span class="topbar-avatar">{{ authStore.userInitial }}</span>
        </div>
      </header>

      <main class="panel-main">
        <div v-if="!isOnline" class="panel-banner panel-banner--offline" role="status" aria-live="polite">
          当前处于离线状态，页面正在使用缓存壳层显示。恢复网络后再刷新数据。
        </div>
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores";

type WorkflowKey = "dashboard" | "submit" | "history" | "notebook" | "profile";
type TopbarKey = "dashboard" | "submit" | "history" | "profile";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const isOnline = ref(typeof navigator === "undefined" ? true : navigator.onLine);

const workflowItems: Array<{
  label: string;
  to: string;
  icon: string;
  railIcon: string;
  workflow: WorkflowKey;
}> = [
  { label: "首页总览", to: "/", icon: "DB", railIcon: "总", workflow: "dashboard" },
  { label: "新作文", to: "/submit", icon: "NW", railIcon: "写", workflow: "submit" },
  { label: "历史评估", to: "/history", icon: "HS", railIcon: "历", workflow: "history" },
  { label: "错题本", to: "/notebook", icon: "NB", railIcon: "错", workflow: "notebook" },
  { label: "学习路径", to: "/profile", icon: "LP", railIcon: "路", workflow: "profile" }
];
const topbarItems: Array<{ key: TopbarKey; label: string; to: string }> = [
  { key: "dashboard", label: "首页", to: "/" },
  { key: "submit", label: "提交作文", to: "/submit" },
  { key: "history", label: "历史记录", to: "/history" },
  { key: "profile", label: "我的画像", to: "/profile" }
];

const activeWorkflow = computed<WorkflowKey>(() => {
  const path = route.path;

  if (path === "/") return "dashboard";
  if (path.startsWith("/submit")) return "submit";
  if (path.startsWith("/history") || path.startsWith("/result")) return "history";
  if (path.startsWith("/notebook")) return "notebook";
  return "profile";
});
const activeTopbar = computed<TopbarKey | null>(() => {
  const path = route.path;

  if (path === "/") return "dashboard";
  if (path.startsWith("/submit")) return "submit";
  if (path.startsWith("/history") || path.startsWith("/result")) return "history";
  if (path.startsWith("/profile")) return "profile";
  return null;
});
const userName = computed(() => authStore.user?.displayName ?? "YASI User");
const userEmail = computed(() => authStore.user?.email ?? "未登录");

function syncConnectivityState() {
  isOnline.value = typeof navigator === "undefined" ? true : navigator.onLine;
}

async function onLogout() {
  await authStore.logout();
  await router.push("/login");
}

onMounted(() => {
  window.addEventListener("online", syncConnectivityState);
  window.addEventListener("offline", syncConnectivityState);
});

onBeforeUnmount(() => {
  window.removeEventListener("online", syncConnectivityState);
  window.removeEventListener("offline", syncConnectivityState);
});
</script>
