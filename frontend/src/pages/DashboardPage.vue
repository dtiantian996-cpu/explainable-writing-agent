<template>
  <main class="page-shell dashboard-page">
    <section class="page-hero dashboard-hero">
      <p class="page-eyebrow">Dashboard</p>
      <h1 class="page-title">{{ heroTitle }}</h1>
      <p class="page-subtitle">{{ heroSubtitle }}</p>
      <div class="hero-pills">
        <span class="hero-pill hero-pill--warm">{{ heroMeta }}</span>
        <span class="hero-pill">{{ heroSecondaryMeta }}</span>
      </div>
    </section>

    <section class="metric-grid metric-grid--4">
      <article class="metric-card">
        <p class="metric-label">累计评估次数</p>
        <p class="metric-value">{{ totalAssessmentsValue }}</p>
        <p class="metric-caption">本地演示环境中的全部作文记录</p>
      </article>
      <article class="metric-card">
        <p class="metric-label">平均分</p>
        <p class="metric-value">{{ averageScore }}</p>
        <p class="metric-caption">近段时间的稳定表现</p>
      </article>
      <article class="metric-card">
        <p class="metric-label">最近一次总分</p>
        <p class="metric-value">{{ latestScore }}</p>
        <p class="metric-caption">只统计已完成 assessment</p>
      </article>
      <article class="metric-card">
        <p class="metric-label">进行中任务</p>
        <p class="metric-value">{{ inProgressCountValue }}</p>
        <p class="metric-caption">{{ inProgressCaption }}</p>
      </article>
    </section>

    <section class="dashboard-grid">
      <div class="stack dashboard-column scroll-pane">
        <article class="surface-card dashboard-card">
          <div class="section-head">
            <div>
              <p class="card-kicker">Recent Essays</p>
              <h2 class="section-title">最近三次评估</h2>
            </div>
            <RouterLink class="button-link" to="/history">查看全部</RouterLink>
          </div>

          <div class="list-stack">
            <div v-if="isDashboardBootstrapping" class="list-row">
              <div>
                <p class="list-row__title">正在加载最近记录</p>
                <p class="card-copy">先拿到历史首包，再决定展示哪几篇。</p>
              </div>
              <p class="list-row__meta">--</p>
            </div>
            <div v-else-if="!previewItems.length" class="list-row">
              <div>
                <p class="list-row__title">还没有可回看的记录</p>
                <p class="card-copy">提交第一篇作文后，这里会显示最近三次评估。</p>
              </div>
              <p class="list-row__meta">--</p>
            </div>
            <div v-for="(item, index) in previewItems" :key="item.assessmentId" class="list-row">
              <div>
                <p class="list-row__title">{{ buildDashboardPreviewTitle(index) }}</p>
                <p class="card-copy">{{ buildDashboardPreviewMeta(item) }}</p>
              </div>
              <p class="list-row__meta">{{ formatScore(item) }}</p>
            </div>
          </div>
        </article>

        <article class="surface-card dashboard-card">
          <p class="card-kicker">Next Step</p>
          <h2 class="section-title">下一步最值得练的不是单词，而是段落推进。</h2>
          <p class="card-copy">
            系统把近期结果、主导错误和长期路径叠在一起，优先给你最稳妥的一步，不让建议散掉。
          </p>
          <div class="list-stack dashboard-path">
            <div v-for="(step, index) in learningPath" :key="step" class="list-row">
              <p class="list-row__title">0{{ index + 1 }}</p>
              <p class="list-row__meta dashboard-step">{{ step }}</p>
            </div>
          </div>
        </article>
      </div>

      <div class="stack dashboard-column scroll-pane">
        <article class="surface-card dashboard-card">
          <p class="card-kicker">Error Snapshot</p>
          <h2 class="section-title">错误画像缩略</h2>
          <p class="support-copy">高频错误不是平均分布的，先把主导类型压下去，整体得分会更稳。</p>
          <SvgMeterList v-if="errorMeters.length" :items="errorMeters" />
          <p v-else class="card-copy">
            {{ isDashboardBootstrapping ? "正在汇总长期画像..." : "当前还没有足够样本生成稳定画像。" }}
          </p>
        </article>

        <article class="action-rail dashboard-action">
          <p class="card-kicker">Recommended Action</p>
          <h2 class="section-title">推荐动作</h2>
          <p class="card-copy">{{ recommendationCopy }}</p>
          <div class="list-stack">
            <div v-for="(step, index) in actionBullets" :key="step" class="list-row">
              <p class="list-row__title">0{{ index + 1 }}</p>
              <p class="list-row__meta">{{ step }}</p>
            </div>
          </div>
          <div class="action-row">
            <RouterLink class="button-primary" to="/submit">开始新作文</RouterLink>
            <RouterLink class="button-secondary" to="/notebook">查看错题本</RouterLink>
          </div>
        </article>
      </div>
    </section>

    <p v-if="profileErrorMessage" class="feedback-text feedback-text--error">
      {{ profileErrorMessage }}
    </p>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { http, normalizeHttpError } from "@/api/http";
import SvgMeterList from "@/components/SvgMeterList.vue";
import { useHistoryStore } from "@/stores";
import { buildDashboardHeroMeta, buildDashboardPreviewMeta, buildDashboardPreviewTitle } from "./dashboardDisplay";
import type { HistoryItem, ProfileResponse } from "@/types/api";
import { localizeErrorLabel } from "@/utils/localization";
import { calculateIeltsBandGap, formatIeltsBand, formatIeltsBandWithScale } from "@/utils/score";

const historyStore = useHistoryStore();
const profile = ref<ProfileResponse | null>(null);
const profileLoaded = ref(false);
const profileLoading = ref(false);
const profileErrorMessage = ref("");

const previewItems = computed(() => historyStore.items.slice(0, 3));
const isDashboardBootstrapping = computed(() => !historyStore.hasFetched || profileLoading.value || !profileLoaded.value);
const learningPath = computed(() => {
  if (isDashboardBootstrapping.value) {
    return ["正在汇总最近结果和长期画像..."];
  }
  if (profile.value?.learningPath.length) {
    return profile.value.learningPath.slice(0, 3);
  }
  return ["先拿到更多作文样本，画像才会更稳定。"];
});
const totalAssessmentsValue = computed(() => (historyStore.hasFetched ? String(historyStore.items.length) : "--"));
const averageScore = computed(() =>
  profileLoaded.value && profile.value ? formatIeltsBand(profile.value.averageScore) : "--"
);
const latestScore = computed(() =>
  historyStore.hasFetched && historyStore.latestCompletedRecord
    ? formatIeltsBandWithScale(historyStore.latestCompletedRecord.overallScore)
    : "--"
);
const inProgressCount = computed(
  () => historyStore.items.filter((item) => item.status === "queued" || item.status === "processing").length
);
const inProgressCountValue = computed(() => (historyStore.hasFetched ? String(inProgressCount.value) : "--"));
const inProgressCaption = computed(() =>
  historyStore.hasFetched
    ? inProgressCount.value
      ? "当前有作文正在 OCR 或分析中"
      : "当前没有挂起任务"
    : "等待历史首包完成"
);
const dominantError = computed(() => profile.value?.dominantErrors[0]);
const heroTitle = computed(() => {
  if (isDashboardBootstrapping.value) {
    return "正在汇总最近评估和长期画像。";
  }
  if (profileErrorMessage.value || !profile.value) {
    return "画像暂时不可用，先回看最近记录，再稍后重试。";
  }
  const gap = formatIeltsBand(calculateIeltsBandGap(8, profile.value.averageScore ?? 0));
  return `离目标 8.0 还差 ${gap}。\n先修主导错误，再开下一篇。`;
});
const heroSubtitle = computed(() => {
  if (isDashboardBootstrapping.value) {
    return "先确认历史和画像首包，再给出真正有语义的判断。";
  }
  if (profileErrorMessage.value) {
    return profileErrorMessage.value;
  }
  return profile.value?.summaryNarrative ?? "最近一篇的表现、主导错误和下一步动作，都应该在首页一次说清。";
});
const heroMeta = computed(() => {
  return buildDashboardHeroMeta(historyStore.hasFetched, historyStore.latestCompletedRecord ?? null);
});
const heroSecondaryMeta = computed(() => {
  if (!dominantError.value) return "等待主导错误画像";
  return `主导错误 ${localizeErrorLabel(dominantError.value.type)}`;
});
const recommendationCopy = computed(() => {
  if (!dominantError.value) {
    return "先完成一篇作文，系统才会沉淀出真实的错误画像和下一步建议。";
  }

  return `主导错误目前是 ${localizeErrorLabel(dominantError.value.type)}。先回错题本集中复盘，再回提交页开下一篇。`;
});
const actionBullets = computed(() => {
  if (profile.value?.learningPath.length) {
    return profile.value.learningPath.slice(0, 3);
  }
  return ["先进入错题本集中复盘。", "再回提交页写下一篇。", "完成后用历史页核对变化。"];
});

function meterTone(index: number): "error" | "neutral" | "warning" | "success" {
  if (index === 0) return "error";
  if (index === 1) return "neutral";
  if (index === 2) return "warning";
  return "success";
}

const errorMeters = computed(() => {
  const items = profile.value?.dominantErrors ?? [];
  return items.slice(0, 4).map((item, index) => ({
    label: localizeErrorLabel(item.type),
    value: item.count,
    valueLabel: `${Math.round(item.share * 100)}%`,
    tone: meterTone(index)
  }));
});

function formatScore(item: HistoryItem): string {
  if (item.status === "completed") return formatIeltsBand(item.overallScore);
  if (item.status === "failed") return "失败";
  return "进行中";
}

async function fetchProfile() {
  profileLoading.value = true;
  profileErrorMessage.value = "";
  try {
    const { data } = await http.get<ProfileResponse>("/api/profile");
    profile.value = data;
  } catch (error) {
    profile.value = null;
    profileErrorMessage.value = normalizeHttpError(error, "获取画像失败");
  } finally {
    profileLoaded.value = true;
    profileLoading.value = false;
  }
}

onMounted(() => {
  if (!historyStore.hasFetched && !historyStore.loading) {
    void historyStore.fetchHistory();
  }
  void fetchProfile();
});
</script>

<style scoped>
.dashboard-page {
  align-content: start;
}

.dashboard-hero {
  max-width: 980px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.03fr) minmax(320px, 0.97fr);
  gap: 22px;
}

.dashboard-card,
.dashboard-action {
  display: grid;
  gap: 16px;
}

.dashboard-path .list-row__title,
.dashboard-action .list-row__title {
  flex: 0 0 40px;
  font-family: var(--font-secondary);
  color: var(--muted-foreground);
}

.dashboard-step {
  flex: 1;
  text-align: left;
}

@media (min-width: 1100px) {
  .dashboard-page {
    grid-template-rows: auto auto minmax(0, 1fr);
    min-height: 0;
    overflow-y: scroll;
    overflow-x: hidden;
  }

  .dashboard-grid,
  .dashboard-column {
    min-height: 0;
  }

  .dashboard-grid {
    min-height: 360px;
  }
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .metric-grid--4 {
    grid-template-columns: 1fr;
  }
}
</style>
