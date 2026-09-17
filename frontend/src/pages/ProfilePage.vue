<template>
  <main class="page-shell profile-page">
    <section class="page-hero profile-hero">
      <p class="page-eyebrow">Profile</p>
      <h1 class="page-title">{{ heroTitle }}</h1>
      <p class="page-subtitle">{{ heroSubtitle }}</p>
      <div class="hero-pills">
        <span class="hero-pill">平均分 {{ averageScore }}</span>
        <span class="hero-pill hero-pill--warm">下一目标 {{ nextTargetScore }}</span>
      </div>
    </section>

    <section class="metric-grid metric-grid--4">
      <article class="metric-card">
        <p class="metric-label">累计作文数</p>
        <p class="metric-value">{{ completedHistoryCountLabel }}</p>
        <p class="metric-caption">过去 30 天完成篇数</p>
      </article>
      <article class="metric-card">
        <p class="metric-label">当前平均分</p>
        <p class="metric-value">{{ averageScore }}</p>
        <p class="metric-caption">按雅思整分 / 半分规则统一展示</p>
      </article>
      <article class="metric-card">
        <p class="metric-label">主导错误</p>
        <p class="metric-value">{{ dominantErrorLabel }}</p>
        <p class="metric-caption">主导一类，先啃它</p>
      </article>
      <article class="metric-card">
        <p class="metric-label">下一步</p>
        <p class="metric-value profile-metric-note">先稳段落，再冲 8.0</p>
        <p class="metric-caption">先把结构短板压下去</p>
      </article>
    </section>

    <section class="profile-middle-grid">
      <article class="surface-card profile-chart-card scroll-pane">
        <p class="card-kicker">Average Trend</p>
        <h2 class="section-title">平均分趋势</h2>
        <BaseEChart v-if="!isProfileBootstrapping && profile" :option="trendOption" size="panel" />
        <p v-else class="card-copy">正在汇总最近成绩曲线，先不要把首帧占位误读成真实趋势。</p>
        <p class="card-copy">分数曲线不是装饰，而是判断你最近到底在涨还是横着走。</p>
      </article>

      <article class="surface-card profile-chart-card scroll-pane">
        <p class="card-kicker">Dominant Errors</p>
        <h2 class="section-title">长期错误分布</h2>
        <SvgMeterList v-if="dominantErrorMeters.length" :items="dominantErrorMeters" />
        <p v-else class="card-copy">
          {{ isProfileBootstrapping ? "正在聚合长期错误分布..." : "当前还没有足够样本形成稳定的长期错误画像。" }}
        </p>
        <p class="card-copy">主导错误不是平均分布的，先打掉第一类，收益最大。</p>
      </article>
    </section>

    <section class="profile-bottom-grid">
      <article class="surface-card profile-action-card">
        <p class="card-kicker">This Week</p>
        <h2 class="section-title">本周学习路径</h2>
        <div class="list-stack">
          <div v-for="(step, index) in learningPathSteps" :key="step" class="list-row">
            <p class="list-row__title">0{{ index + 1 }}</p>
            <p class="list-row__meta profile-action-card__copy">{{ step }}</p>
          </div>
        </div>
      </article>

      <article class="surface-card profile-action-card">
        <p class="card-kicker">Notebook Entry</p>
        <h2 class="section-title">错题本入口</h2>
        <p class="card-copy">已经累计 {{ notebookTotalLabel }} 条错题，其中待复习 {{ pendingNotebookCountLabel }} 条。</p>
        <RouterLink class="button-secondary profile-action-card__cta" to="/notebook">打开错题本</RouterLink>
      </article>

      <article class="action-rail profile-action-card profile-action-card--dark">
        <p class="card-kicker">Recommended Focus</p>
        <h2 class="section-title">推荐练习方向</h2>
        <p class="card-copy">{{ recommendedFocus }}</p>
        <RouterLink class="button-primary profile-action-card__cta" to="/submit">开始练习</RouterLink>
      </article>
    </section>

    <p v-if="errorMessage" class="feedback-text feedback-text--error">
      {{ errorMessage }}
    </p>
    <p v-if="isProfileBootstrapping && !errorMessage" class="feedback-text">
      正在加载画像...
    </p>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import type { EChartsOption } from "echarts";
import { http, normalizeHttpError } from "@/api/http";
import BaseEChart from "@/components/BaseEChart.vue";
import SvgMeterList from "@/components/SvgMeterList.vue";
import { useHistoryStore, useNotebookStore } from "@/stores";
import type { ProfileResponse } from "@/types/api";
import { localizeErrorLabel } from "@/utils/localization";
import { formatIeltsBand } from "@/utils/score";

const historyStore = useHistoryStore();
const notebookStore = useNotebookStore();
const profile = ref<ProfileResponse | null>(null);
const errorMessage = ref("");
const profileLoaded = ref(false);
const profileLoading = ref(false);

const completedHistory = computed(() =>
  historyStore.items.filter((item) => item.status === "completed")
);
const pendingNotebookCount = computed(() => notebookStore.summary.pendingReviewCount);
const isProfileBootstrapping = computed(
  () => !historyStore.hasFetched || !notebookStore.hasFetched || profileLoading.value || !profileLoaded.value
);
const completedHistoryCountLabel = computed(() =>
  historyStore.hasFetched ? String(completedHistory.value.length) : "--"
);
const notebookTotalLabel = computed(() =>
  notebookStore.hasFetched ? String(notebookStore.summary.totalItems) : "--"
);
const pendingNotebookCountLabel = computed(() =>
  notebookStore.hasFetched ? String(pendingNotebookCount.value) : "--"
);
const averageScore = computed(() =>
  profileLoaded.value && profile.value ? formatIeltsBand(profile.value.averageScore) : "--"
);
const nextTargetScore = computed(() =>
  profileLoaded.value && profile.value ? formatIeltsBand(profile.value.nextTargetScore) : "--"
);
const dominantErrorLabel = computed(() => {
  if (!profileLoaded.value) return "--";
  return localizeErrorLabel(profile.value?.dominantErrors[0]?.type ?? "none");
});
const heroTitle = computed(() => {
  if (isProfileBootstrapping.value) {
    return "正在汇总长期成绩和错题画像。";
  }
  if (errorMessage.value || !profile.value) {
    return "画像暂时不可用，恢复连接后再试。";
  }
  if (!profile.value.dominantErrors.length) {
    return "样本还在积累，先用更多作文把画像站稳。";
  }
  return `当前最该先压下去的，是${dominantErrorLabel.value}。`;
});
const heroSubtitle = computed(() => {
  if (isProfileBootstrapping.value) {
    return "这页只回答两件事：你是否在进步，以及下一步最该补哪里。";
  }
  if (errorMessage.value) {
    return errorMessage.value;
  }
  return profile.value?.summaryNarrative ?? "这页只回答两件事：你是否在进步，以及下一步最该补哪里。";
});

function meterTone(index: number): "error" | "neutral" | "warning" | "success" {
  if (index === 0) return "error";
  if (index === 1) return "neutral";
  if (index === 2) return "warning";
  return "success";
}

const dominantErrorMeters = computed(() =>
  (profile.value?.dominantErrors ?? []).slice(0, 4).map((item, index) => ({
    label: localizeErrorLabel(item.type),
    value: item.count,
    valueLabel: `${Math.round(item.share * 100)}%`,
    tone: meterTone(index)
  }))
);
const recommendedFocus = computed(() => {
  if (isProfileBootstrapping.value) {
    return "正在汇总推荐练习方向...";
  }
  if (errorMessage.value) {
    return "画像暂时不可用，请恢复网络后重新加载。";
  }
  if (!profile.value?.learningPath.length) {
    return "先提交更多作文，再让系统给出稳定的长期路径。";
  }
  return profile.value.learningPath[0];
});
const learningPathSteps = computed(() => {
  if (isProfileBootstrapping.value) {
    return ["正在整理本周学习路径..."];
  }
  if (errorMessage.value) {
    return ["画像暂时不可用，请恢复网络后重新加载。"];
  }
  if (profile.value?.learningPath.length) {
    return profile.value.learningPath;
  }
  return ["先提交更多作文，再让系统给出稳定的长期路径。"];
});
const trendOption = computed<EChartsOption>(() => {
  const scores = profile.value?.recentScores ?? [];
  return {
    animation: false,
    grid: {
      top: 16,
      left: 30,
      right: 16,
      bottom: 22
    },
    xAxis: {
      type: "category",
      data: scores.map((_, index) => `D${index + 1}`),
      axisLine: { lineStyle: { color: "#ebebeb" } },
      axisLabel: { color: "#666666", fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 9,
      splitNumber: 3,
      axisLabel: { color: "#666666", fontSize: 11 },
      splitLine: { lineStyle: { color: "#f0f0f0" } }
    },
    series: [
      {
        type: "line",
        smooth: false,
        data: scores,
        symbol: "circle",
        symbolSize: 7,
        lineStyle: {
          color: "#171717",
          width: 2
        },
        itemStyle: {
          color: "#171717"
        }
      }
    ]
  };
});

async function fetchProfile() {
  profileLoading.value = true;
  errorMessage.value = "";
  try {
    const { data } = await http.get<ProfileResponse>("/api/profile");
    profile.value = data;
  } catch (error) {
    profile.value = null;
    errorMessage.value = normalizeHttpError(error, "获取画像失败");
  } finally {
    profileLoaded.value = true;
    profileLoading.value = false;
  }
}

onMounted(() => {
  if (!historyStore.hasFetched && !historyStore.loading) {
    void historyStore.fetchHistory();
  }
  if (!notebookStore.hasFetched && !notebookStore.loading) {
    void notebookStore.fetchNotebook();
  }
  void fetchProfile();
});
</script>

<style scoped>
.profile-page {
  align-content: start;
}

.profile-hero {
  max-width: 980px;
}

.profile-metric-note {
  font-size: 24px;
  line-height: 1.12;
}

.profile-middle-grid,
.profile-bottom-grid,
.profile-chart-card,
.profile-action-card {
  display: grid;
  gap: 18px;
}

.profile-middle-grid {
  grid-template-columns: minmax(0, 1.06fr) minmax(320px, 0.94fr);
}

.profile-bottom-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.profile-action-card__copy {
  flex: 1;
  text-align: left;
}

.profile-action-card__cta {
  margin-top: auto;
}

@media (min-width: 1100px) {
  .profile-page {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
    overflow-y: scroll;
    overflow-x: hidden;
  }

  .profile-hero {
    padding: 18px 20px;
    gap: 8px;
  }

  .profile-hero .page-title {
    max-width: 24ch;
    font-size: 30px;
  }

  .profile-hero .page-subtitle {
    max-width: 90ch;
    font-size: 13px;
    line-height: 1.5;
  }

  .profile-page .metric-grid {
    gap: 10px;
  }

  .profile-page .metric-card {
    gap: 6px;
    padding: 12px 14px;
  }

  .profile-page .metric-value {
    font-size: 24px;
  }

  .profile-page .metric-caption {
    display: none;
  }

  .profile-middle-grid {
    flex: 0 0 auto;
    min-height: auto;
    gap: 12px;
  }

  .profile-middle-grid,
  .profile-chart-card {
    min-height: 0;
  }

  .profile-chart-card,
  .profile-action-card {
    gap: 8px;
    padding: 14px;
  }

  .profile-chart-card {
    min-height: 240px;
  }

  .profile-chart-card .section-title,
  .profile-action-card .section-title {
    font-size: 18px;
  }

  .profile-bottom-grid {
    gap: 10px;
  }

  .profile-action-card .card-copy,
  .profile-action-card__copy {
    font-size: 12px;
    line-height: 1.45;
  }

  .profile-action-card .list-row {
    padding: 8px 0;
  }

  .profile-action-card .list-stack .list-row:nth-child(n+3) {
    display: none;
  }

  .profile-action-card--dark .card-copy {
    display: -webkit-box;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
  }
}

@media (max-width: 1100px) {
  .profile-middle-grid,
  .profile-bottom-grid {
    grid-template-columns: 1fr;
  }
}
</style>
