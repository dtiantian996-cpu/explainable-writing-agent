<template>
  <main class="page-shell result-page">
    <section class="surface-card result-summary">
      <div class="result-summary__lead">
        <p class="card-kicker">Result / Summary Bar</p>
        <h1 class="result-summary__title">{{ summaryTitle }}</h1>
        <p class="page-subtitle">{{ summarySubtitle }}</p>
        <div class="hero-pills">
          <span class="status-pill" :class="statusPillClass">{{ statusLabel }}</span>
          <span v-if="assessmentTopic" class="hero-pill">{{ assessmentTopic }}</span>
          <span class="hero-pill">{{ taskTypeLabel }}</span>
          <span class="hero-pill">{{ summarySourceMode }}</span>
        </div>
      </div>

      <div class="result-summary__scorecard">
        <div class="result-summary__scorebox">
          <p class="card-kicker">Overall</p>
          <p class="hero-score">{{ overallScore }}</p>
          <p class="card-copy">{{ statusLine }}</p>
        </div>

        <div class="result-summary__actions">
          <button class="button-secondary" type="button" @click="void refreshResult()">刷新状态</button>
          <button
            class="button-primary"
            type="button"
            :disabled="!result || exportState === 'exporting'"
            @click="void exportPdf()"
          >
            {{ exportButtonLabel }}
          </button>
        </div>

        <div class="result-summary__meta">
          <div class="result-summary__metric">
            <span>字数</span>
            <strong>{{ result ? result.meta.wordCount : "--" }}</strong>
          </div>
          <div class="result-summary__metric">
            <span>错题</span>
            <strong>{{ result ? result.notebookSummary.totalItems : "--" }}</strong>
          </div>
          <div class="result-summary__metric">
            <span>生成时间</span>
            <strong>{{ generatedAtLabel }}</strong>
          </div>
          <div class="result-summary__metric">
            <span>下一目标</span>
            <strong>{{ result ? formatIeltsBand(result.profile.nextTargetScore) : "--" }}</strong>
          </div>
        </div>
      </div>
    </section>

    <p v-if="exportMessage" class="feedback-text" :class="{ 'feedback-text--error': exportMessageIsError }">
      {{ exportMessage }}
    </p>

    <section v-if="isLoadingState" class="state-card result-state">
      <p class="card-kicker">Result Loading</p>
      <h2 class="section-title">评分、建议和画像正在收成一页。</h2>
      <p class="card-copy">
        当前已经进入结果页壳层，后端会继续轮询状态。等结构化结果齐全后，这里直接切成正式双栏舞台，而不是再跳别的页面。
      </p>
      <div class="result-state__progress">
        <div class="result-state__track">
          <div class="result-state__fill" :style="{ width: `${Math.max(12, assessmentStore.progressPercent)}%` }" />
        </div>
        <div class="result-state__meta">
          <span>{{ assessmentStore.progressMessage || "正在生成结果" }}</span>
          <strong>{{ assessmentStore.progressPercent }}%</strong>
        </div>
      </div>
    </section>

    <section v-else-if="isFailureState" class="state-card result-state">
      <p class="card-kicker">Result Failure</p>
      <h2 class="section-title">这次评估没有完整落成，需要重新拉取。</h2>
      <p class="card-copy">
        {{ assessmentStore.errorMessage || "后端返回失败态，当前结果未形成完整 schema。" }}
      </p>
      <div class="action-row">
        <button class="button-primary" type="button" @click="void refreshResult()">再次查询</button>
        <RouterLink class="button-secondary" to="/history">回历史页</RouterLink>
        <RouterLink class="button-secondary" to="/submit">重新提交</RouterLink>
      </div>
    </section>

    <section v-else-if="result" class="surface-card result-workbench">
      <div class="result-workbench__top">
        <div class="tab-strip">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="tab-button"
            :class="{ 'is-active': activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>

      <div class="result-layout">
        <div class="result-layout__essay">
          <article class="surface-card result-essay-panel">
            <EssayViewer :text="result.essayText" :suggestions="result.suggestions" />
          </article>

          <article class="action-rail result-quick">
            <p class="card-kicker">Next Action</p>
            <h2 class="section-title">{{ nextActionHeadline }}</h2>
            <p class="card-copy">{{ nextActionBody }}</p>
            <div class="list-stack">
              <div v-for="(step, index) in actionSteps" :key="`${index}-${step}`" class="list-row">
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

        <div class="result-layout__analysis scroll-pane">
          <article v-if="activeTab === 'report'" class="surface-card result-panel">
            <div class="section-head">
              <div>
                <p class="card-kicker">Report</p>
                <h2 class="section-title">评估报告 / Report Stage</h2>
              </div>
              <span class="status-pill status-pill--success">已完成</span>
            </div>

            <div class="result-card-grid">
              <article v-for="dimension in reportCards" :key="dimension.label" class="metric-card result-dimension">
                <p class="metric-label">{{ dimension.label }}</p>
                <p class="metric-value">{{ formatIeltsBand(dimension.score) }}</p>
                <div class="list-stack result-dimension__notes">
                  <p v-for="reason in dimension.reasons" :key="reason" class="card-copy">{{ reason }}</p>
                </div>
              </article>
            </div>

            <article class="surface-muted knowledge-panel">
              <div class="section-head">
                <div>
                  <p class="card-kicker">Knowledge</p>
                  <h3 class="chart-panel__title">参考依据</h3>
                </div>
                <span class="status-pill" :class="knowledgeStatusClass">{{ knowledgeStatusLabel }}</span>
              </div>
              <p class="card-copy">{{ knowledgeBodyCopy }}</p>
              <template v-if="result.meta.knowledgeStatus !== 'disabled'">
                <div v-if="result.meta.knowledgeWarnings.length" class="list-stack">
                  <p
                    v-for="warning in result.meta.knowledgeWarnings"
                    :key="warning"
                    class="card-copy knowledge-warning"
                  >
                    {{ warning }}
                  </p>
                </div>
                <div v-if="knowledgeSources.length" class="knowledge-source-list">
                  <article
                    v-for="source in knowledgeSources"
                    :key="source.id"
                    class="surface-card knowledge-source"
                  >
                    <div class="review-card__head">
                      <span class="status-pill status-pill--info">{{ localizeKnowledgeSourceType(source.type) }}</span>
                      <span class="metric-label">
                        {{ source.ieltsTask || result.meta.knowledgeTask || "General" }}
                      </span>
                    </div>
                    <h4 class="knowledge-source__title">{{ source.title }}</h4>
                    <p class="card-copy">{{ source.selectionReason }}</p>
                    <p class="review-card__copy">{{ source.excerpt }}</p>
                    <p class="metric-label">
                      检索 {{ source.score.toFixed(2) }}
                      <template v-if="source.rerankScore != null"> · 重排 {{ source.rerankScore.toFixed(2) }}</template>
                    </p>
                  </article>
                </div>
                <p v-else class="card-copy">本次没有稳定命中的参考资料，已按空上下文继续评估。</p>
              </template>
            </article>
          </article>

          <article v-else-if="activeTab === 'suggestions'" class="surface-card result-panel">
            <div class="section-head">
              <div>
                <p class="card-kicker">Suggestions</p>
                <h2 class="section-title">逐句建议 / Review Stage</h2>
              </div>
              <span class="hero-pill">{{ result.suggestions.length }} 条重点问题</span>
            </div>
            <div class="stack">
              <article
                v-for="item in result.suggestions"
                :key="`${item.positionStart}-${item.sourceText}`"
                class="surface-card review-card"
              >
                <div class="review-card__head">
                  <span class="status-pill status-pill--error">{{ localizeErrorLabel(item.errorType) }}</span>
                  <span class="metric-label">{{ item.positionStart }} - {{ item.positionEnd }}</span>
                </div>
                <div class="review-card__body">
                  <div class="review-card__block">
                    <p class="card-kicker">Original</p>
                    <p class="review-card__copy">{{ item.sourceText }}</p>
                  </div>
                  <div class="review-card__block">
                    <p class="card-kicker">Why</p>
                    <p class="review-card__copy">{{ item.explanation }}</p>
                  </div>
                  <div class="review-card__split">
                    <div>
                      <p class="card-kicker">Revision</p>
                      <p class="review-card__copy">{{ item.revision }}</p>
                    </div>
                    <div>
                      <p class="card-kicker">Rewrite</p>
                      <p class="review-card__copy">{{ item.revisedSentence }}</p>
                    </div>
                  </div>
                </div>
              </article>
            </div>
          </article>

          <article v-else-if="activeTab === 'highlights'" class="surface-card result-panel">
            <div class="section-head">
              <div>
                <p class="card-kicker">Highlights</p>
                <h2 class="section-title">亮点分析 / Highlight Stage</h2>
              </div>
              <span class="hero-pill">{{ result.highlights.length || 0 }} 个亮点</span>
            </div>
            <div v-if="result.highlights.length" class="stack">
              <article
                v-for="item in result.highlights"
                :key="`${item.type}-${item.location}`"
                class="surface-card highlight-card"
              >
                <div class="review-card__head">
                  <span class="status-pill status-pill--success">{{ localizeHighlightLabel(item.type) }}</span>
                  <span class="metric-label">{{ item.location }}</span>
                </div>
                <p class="review-card__copy">{{ item.explanation }}</p>
                <p class="card-copy">{{ item.encouragement }}</p>
              </article>
            </div>
            <article v-else class="surface-muted highlight-card">
              <p class="card-kicker">No Highlights Yet</p>
              <p class="review-card__copy">当前结果没有独立亮点条目，但整体评分和建议已经完整生成。</p>
            </article>
          </article>

          <article v-else-if="activeTab === 'charts'" class="surface-card result-panel">
            <div class="section-head">
              <div>
                <p class="card-kicker">Charts</p>
                <h2 class="section-title">可视化 / Chart Stage</h2>
              </div>
              <span class="hero-pill">2 x 2</span>
            </div>
            <div class="chart-grid">
              <article class="surface-muted chart-panel">
                <p class="card-kicker">Radar</p>
                <h3 class="chart-panel__title">四维评分</h3>
                <BaseEChart :option="radarOption" />
              </article>
              <article class="surface-muted chart-panel">
                <p class="card-kicker">Comparison</p>
                <h3 class="chart-panel__title">目标对比</h3>
                <BaseEChart :option="comparisonOption" />
              </article>
              <article class="surface-muted chart-panel">
                <p class="card-kicker">Word Cloud</p>
                <h3 class="chart-panel__title">亮点词云</h3>
                <WordCloudSvg :items="wordCloudItems" />
              </article>
              <article class="surface-muted chart-panel">
                <p class="card-kicker">Heatmap</p>
                <h3 class="chart-panel__title">结构热力</h3>
                <BaseEChart :option="heatmapOption" />
              </article>
            </div>
          </article>

          <article v-else class="surface-card result-panel">
            <div class="section-head">
              <div>
                <p class="card-kicker">Profile</p>
                <h2 class="section-title">学习建议 / Long-term Focus</h2>
              </div>
              <span class="hero-pill">下一目标 {{ formatIeltsBand(result.profile.nextTargetScore) }}</span>
            </div>

            <article class="surface-muted result-profile-stage">
              <p class="card-kicker">Summary</p>
              <h3 class="chart-panel__title">{{ profileHeadline }}</h3>
              <p class="card-copy">{{ result.profile.summaryNarrative }}</p>
            </article>

            <div class="result-profile-grid">
              <article class="surface-muted">
                <p class="card-kicker">Dominant Errors</p>
                <h3 class="chart-panel__title">主导错误</h3>
                <SvgMeterList :items="profileMeters" />
              </article>
              <article class="surface-muted">
                <p class="card-kicker">Learning Path</p>
                <h3 class="chart-panel__title">下一步练什么</h3>
                <div class="list-stack">
                  <div v-for="(step, index) in result.profile.learningPath" :key="step" class="list-row">
                    <p class="list-row__title">0{{ index + 1 }}</p>
                    <p class="list-row__meta result-path__copy">{{ step }}</p>
                  </div>
                </div>
              </article>
            </div>
          </article>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import type { EChartsOption } from "echarts";
import BaseEChart from "@/components/BaseEChart.vue";
import EssayViewer from "@/components/EssayViewer.vue";
import SvgMeterList from "@/components/SvgMeterList.vue";
import WordCloudSvg from "@/components/WordCloudSvg.vue";
import { AssessmentExportError, exportAssessmentToPdf } from "./resultExport";
import {
  getKnowledgeBodyCopy,
  getKnowledgeStatusClass,
  getKnowledgeStatusLabel,
  getVisibleKnowledgeSources
} from "./resultKnowledge";
import { useAssessmentStore, useHistoryStore } from "@/stores";
import type {
  AssessmentProgressResponse,
  ComparisonPoint,
  HeatmapPoint,
  RadarPoint,
  WordCloudPoint
} from "@/types/api";
import {
  localizeDimensionLabel,
  localizeErrorLabel,
  localizeHeatmapSection,
  localizeHighlightLabel,
  localizeKnowledgeSourceType
} from "@/utils/localization";
import { calculateIeltsBandGap, formatIeltsBand, formatIeltsBandWithScale, roundIeltsBand } from "@/utils/score";
import { formatTaskType } from "@/utils/taskType";

const props = defineProps<{
  assessmentId?: string;
}>();

const assessmentStore = useAssessmentStore();
const historyStore = useHistoryStore();
const tabs = [
  { key: "report", label: "评估报告" },
  { key: "suggestions", label: "逐句建议" },
  { key: "highlights", label: "亮点分析" },
  { key: "charts", label: "可视化" },
  { key: "profile", label: "学习建议" }
] as const;
const activeTab = ref<(typeof tabs)[number]["key"]>("report");
const exportMessage = ref("");
const exportMessageIsError = ref(false);
const exportState = ref<"idle" | "exporting">("idle");
let pollTimer: ReturnType<typeof window.setTimeout> | null = null;

const result = computed(() => assessmentStore.result);
const assessmentEntry = computed(() =>
  historyStore.items.find((item) => item.assessmentId === props.assessmentId) ?? null
);
const assessmentTopic = computed(() => assessmentEntry.value?.topic || assessmentStore.draft.topic.trim());
const taskTypeLabel = computed(() => formatTaskType(assessmentEntry.value?.taskType));
const numericOverallScore = computed(() => {
  if (!result.value) return null;
  const report = result.value.report;
  const total =
    report.grammar_accuracy.score +
    report.task_response.score +
    report.coherence_cohesion.score +
    report.lexical_resource.score;
  return roundIeltsBand(total / 4);
});
const overallScore = computed(() => {
  if (numericOverallScore.value == null) {
    if (assessmentStore.submitState === "failed") return "失败";
    return "生成中";
  }
  return formatIeltsBandWithScale(numericOverallScore.value);
});
const dominantErrorLabel = computed(() =>
  localizeErrorLabel(result.value?.profile.dominantErrors[0]?.type ?? "coherence")
);
const summaryTitle = computed(() => {
  if (result.value && numericOverallScore.value != null) {
    const gap = formatIeltsBand(calculateIeltsBandGap(8, numericOverallScore.value));
    return `离目标 8.0 还差 ${gap}。\n${buildFocusSentence(dominantErrorLabel.value)}`;
  }
  if (assessmentStore.submitState === "failed") {
    return "这次结果没有完整落成。\n先确认失败原因，再决定是否重试。";
  }
  return "评分、建议和画像正在汇总。\n结果页会直接切成正式舞台。";
});
const summarySubtitle = computed(() => {
  if (result.value) {
    return result.value.profile.summaryNarrative;
  }
  if (assessmentStore.submitState === "failed") {
    return "结果页不做假完成态。只有拿到完整 schema，才会渲染正式双栏结构。";
  }
  return "当前已经进入结果页壳层，后端会继续生成评分、逐句建议、亮点与学习路径。";
});
const generatedAtLabel = computed(() => {
  if (!result.value?.meta.generatedAt) return "--";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  }).format(new Date(result.value.meta.generatedAt));
});
const isLoadingState = computed(
  () =>
    !result.value &&
    (assessmentStore.submitState === "creating" || assessmentStore.submitState === "polling" || assessmentStore.submitState === "idle")
);
const isFailureState = computed(() => !result.value && assessmentStore.submitState === "failed");
const statusLabel = computed(() => {
  if (result.value) return "已完成";
  if (assessmentStore.submitState === "failed") return "失败";
  if (assessmentStore.submitState === "creating") return "创建中";
  return "生成中";
});
const statusPillClass = computed(() => ({
  "status-pill--success": Boolean(result.value),
  "status-pill--error": assessmentStore.submitState === "failed",
  "status-pill--warning": !result.value && assessmentStore.submitState === "creating",
  "status-pill--info": !result.value && assessmentStore.submitState !== "failed" && assessmentStore.submitState !== "creating"
}));
const summarySourceMode = computed(() => {
  if (!result.value) return "等待结果";
  return formatSourceMode(result.value.meta.sourceMode);
});
const statusLine = computed(() => {
  if (result.value) {
    return `${assessmentTopic.value || "当前作文"} · ${generatedAtLabel.value}`;
  }
  return assessmentStore.progressMessage || "等待任务状态";
});
const reportCards = computed(() => {
  if (!result.value) return [];
  const report = result.value.report;
  return [
    {
      label: "语法准确性",
      score: report.grammar_accuracy.score,
      reasons: report.grammar_accuracy.reasonBullets
    },
    {
      label: "任务完成度",
      score: report.task_response.score,
      reasons: report.task_response.reasonBullets
    },
    {
      label: "连贯与衔接",
      score: report.coherence_cohesion.score,
      reasons: report.coherence_cohesion.reasonBullets
    },
    {
      label: "词汇资源",
      score: report.lexical_resource.score,
      reasons: report.lexical_resource.reasonBullets
    }
  ];
});
const knowledgeSources = computed(() =>
  getVisibleKnowledgeSources(result.value?.meta.knowledgeSources).map((source) => ({
    ...source,
    type: localizeKnowledgeSourceType(source.type)
  }))
);
const knowledgeStatusLabel = computed(() => getKnowledgeStatusLabel(result.value?.meta.knowledgeStatus));
const knowledgeStatusClass = computed(() => getKnowledgeStatusClass(result.value?.meta.knowledgeStatus));
const knowledgeBodyCopy = computed(() => getKnowledgeBodyCopy(result.value?.meta ?? null));
const nextActionHeadline = computed(() => {
  if (!result.value) return "正在生成下一步动作。";
  return result.value.profile.learningPath[0] ?? "先回看主导问题，再开下一篇。";
});
const nextActionBody = computed(() => {
  if (!result.value) return "生成完成后，这里会收束成单一动作轨道。";
  const firstSuggestion = result.value.suggestions[0];
  return firstSuggestion?.explanation || result.value.profile.summaryNarrative;
});
const actionSteps = computed(() => {
  if (!result.value) return ["等待完整结果生成。"];
  const steps = result.value.profile.learningPath.slice(0, 3);
  if (steps.length) return steps;
  return ["先查看逐句建议。", "再去错题本集中复盘。", "最后重新开一篇作文。"];
});
const profileHeadline = computed(() => {
  if (!result.value) return "正在汇总长期建议。";
  return `${dominantErrorLabel.value} 还没压稳，先把这一类问题收下去。`;
});
const exportButtonLabel = computed(() => (exportState.value === "exporting" ? "导出中..." : "导出 PDF"));

function meterTone(index: number): "error" | "neutral" | "warning" | "success" {
  if (index === 0) return "error";
  if (index === 1) return "neutral";
  if (index === 2) return "warning";
  return "success";
}

const profileMeters = computed(() =>
  (result.value?.profile.dominantErrors ?? []).slice(0, 4).map((item, index) => ({
    label: localizeErrorLabel(item.type),
    value: item.count,
    valueLabel: `${Math.round(item.share * 100)}%`,
    tone: meterTone(index)
  }))
);
const wordCloudItems = computed(() =>
  ((result.value?.chartsData.wordCloud ?? []) as WordCloudPoint[]).map((item) => ({
    word: item.word ?? item.text ?? "",
    weight: item.weight
  }))
);
const radarOption = computed<EChartsOption>(() => buildRadarOption(result.value?.chartsData.radar ?? []));
const comparisonOption = computed<EChartsOption>(() =>
  buildComparisonOption(result.value?.chartsData.comparison ?? [])
);
const heatmapOption = computed<EChartsOption>(() => buildHeatmapOption(result.value?.chartsData.heatmap ?? []));

function clearPollTimer() {
  if (pollTimer) {
    window.clearTimeout(pollTimer);
    pollTimer = null;
  }
}

async function exportPdf() {
  if (!result.value) {
    exportMessageIsError.value = true;
    exportMessage.value = "结果尚未生成，暂时无法导出。";
    return;
  }

  exportState.value = "exporting";
  exportMessage.value = "";
  exportMessageIsError.value = false;

  try {
    await exportAssessmentToPdf(result.value.assessmentId);
    exportMessage.value = "PDF 已开始下载。";
  } catch (error) {
    exportMessageIsError.value = true;
    if (error instanceof AssessmentExportError) {
      exportMessage.value = error.message;
    } else {
      exportMessage.value = "导出 PDF 失败，请稍后重试。";
    }
  } finally {
    exportState.value = "idle";
  }
}

function scheduleNextPoll(targetId: string) {
  clearPollTimer();
  pollTimer = window.setTimeout(() => {
    void refreshResult(targetId);
  }, 1500);
}

async function refreshResult(targetId = props.assessmentId) {
  if (!targetId) return;
  exportMessage.value = "";
  exportMessageIsError.value = false;
  assessmentStore.setCurrentAssessment(targetId);
  const payload = await assessmentStore.fetchAssessmentStatus(targetId);
  if (!payload) return;
  if ("meta" in payload) return;
  const progress = payload as AssessmentProgressResponse;
  if (progress.status !== "failed") {
    scheduleNextPoll(targetId);
  }
}

function formatSourceMode(sourceMode: string): string {
  if (sourceMode === "image") return "图片 OCR 输入";
  if (sourceMode === "mixed") return "文本 + 图片混合";
  return "文本主输入";
}

function buildFocusSentence(label: string): string {
  if (/coherence|cohesion|logic|结构|连贯|衔接/i.test(label)) {
    return "这篇先修结构推进，再谈词汇加分。";
  }
  if (/grammar|语法/i.test(label)) {
    return "这篇先修语法稳定，再谈词汇加分。";
  }
  if (/lexical|vocab|词汇/i.test(label)) {
    return "这篇先修表达精度，再谈词汇加分。";
  }
  return `这篇先修${label}，再谈词汇加分。`;
}

function buildRadarOption(points: RadarPoint[]): EChartsOption {
  return {
    animation: false,
    radar: {
      indicator: points.map((point) => ({ name: localizeDimensionLabel(point.dimension), max: 9 })),
      radius: 72,
      splitNumber: 3,
      axisName: {
        color: "#666666",
        fontSize: 11
      },
      splitArea: {
        areaStyle: {
          color: ["#ffffff"]
        }
      },
      splitLine: {
        lineStyle: {
          color: "#ebebeb"
        }
      },
      axisLine: {
        lineStyle: {
          color: "#ebebeb"
        }
      }
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: points.map((point) => point.score),
            areaStyle: {
              color: "rgba(23, 23, 23, 0.08)"
            },
            lineStyle: {
              color: "#171717"
            },
            itemStyle: {
              color: "#171717"
            }
          }
        ]
      }
    ]
  };
}

function buildComparisonOption(points: ComparisonPoint[]): EChartsOption {
  return {
    animation: false,
    grid: {
      top: 18,
      left: 30,
      right: 12,
      bottom: 24
    },
    xAxis: {
      type: "category",
      data: points.map((point) => localizeDimensionLabel(point.dimension)),
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
        type: "bar",
        barWidth: 18,
        data: points.map((point) => point.score),
        itemStyle: {
          color: "#171717",
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        type: "line",
        data: points.map((point) => point.ieltsTarget),
        symbol: "circle",
        symbolSize: 6,
        lineStyle: {
          color: "#8f4a00"
        },
        itemStyle: {
          color: "#8f4a00"
        }
      }
    ]
  };
}

function buildHeatmapOption(points: HeatmapPoint[]): EChartsOption {
  return {
    animation: false,
    grid: {
      top: 18,
      left: 46,
      right: 14,
      bottom: 18
    },
    xAxis: {
      type: "value",
      min: 0,
      max: 1,
      splitNumber: 2,
      axisLabel: {
        color: "#666666",
        formatter: (value: number) => `${Math.round(value * 100)}%`,
        fontSize: 11
      },
      splitLine: {
        lineStyle: {
          color: "#f0f0f0"
        }
      }
    },
    yAxis: {
      type: "category",
      data: points.map((point) => localizeHeatmapSection(point.section)),
      axisLabel: {
        color: "#666666",
        fontSize: 11
      },
      axisTick: { show: false },
      axisLine: { show: false }
    },
    series: [
      {
        type: "bar",
        data: points.map((point) => point.value),
        barWidth: 14,
        itemStyle: {
          color: "#171717",
          borderRadius: 999
        }
      }
    ]
  };
}

watch(
  () => props.assessmentId,
  (nextId) => {
    clearPollTimer();
    activeTab.value = "report";
    if (nextId) {
      void refreshResult(nextId);
    }
    if (!historyStore.items.length) {
      void historyStore.fetchHistory();
    }
  },
  { immediate: true }
);

watch(
  () => result.value?.assessmentId,
  (current, previous) => {
    if (current && current !== previous) {
      void historyStore.fetchHistory();
    }
  }
);

watch(
  () => assessmentStore.submitState,
  (state) => {
    if (state === "failed" || state === "completed") {
      clearPollTimer();
    }
  }
);

onUnmounted(() => {
  clearPollTimer();
});
</script>

<style scoped>
.result-page {
  align-content: start;
}

.result-summary,
.result-workbench,
.result-panel,
.review-card,
.highlight-card,
.result-essay-panel {
  display: grid;
  gap: 18px;
}

.result-summary {
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  align-items: stretch;
}

.result-summary__lead,
.result-summary__scorecard,
.result-summary__scorebox {
  display: grid;
  gap: 14px;
}

.result-summary__title {
  margin: 0;
  white-space: pre-line;
  font-size: 42px;
  line-height: 0.98;
  letter-spacing: -0.08em;
  font-weight: 600;
}

.result-summary__scorecard {
  align-content: start;
}

.result-summary__scorebox {
  padding: 20px;
  border-radius: var(--radius-card);
  background: var(--muted);
}

.hero-score {
  font-size: 48px;
  line-height: 0.96;
  letter-spacing: -0.08em;
  font-weight: 600;
}

.result-summary__actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.result-summary__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.result-summary__metric {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: var(--radius-card);
  background: var(--card);
  box-shadow: var(--shadow-border);
}

.result-summary__metric span {
  color: var(--muted-foreground);
  font-size: 12px;
}

.result-summary__metric strong {
  color: var(--foreground);
  font-size: 18px;
  line-height: 1.2;
  letter-spacing: -0.04em;
}

.result-state {
  gap: 18px;
}

.result-state__progress {
  display: grid;
  gap: 10px;
}

.result-state__track {
  overflow: hidden;
  width: 100%;
  height: 8px;
  border-radius: var(--radius-pill);
  background: #efefef;
}

.result-state__fill {
  height: 100%;
  border-radius: inherit;
  background: #171717;
}

.result-state__meta,
.review-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.result-workbench {
  gap: 20px;
}

.result-workbench__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.result-layout {
  display: grid;
  grid-template-columns: minmax(340px, 0.94fr) minmax(0, 1.06fr);
  gap: 22px;
}

.result-layout__essay,
.result-layout__analysis {
  display: grid;
  gap: 18px;
  align-content: start;
}

.result-essay-panel {
  padding: 20px;
}

.result-card-grid,
.chart-grid,
.result-profile-grid {
  display: grid;
  gap: 14px;
}

.result-card-grid,
.chart-grid,
.result-profile-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.result-dimension {
  min-height: 208px;
  align-content: start;
}

.result-dimension__notes {
  gap: 8px;
}

.knowledge-panel,
.knowledge-source,
.result-profile-stage {
  display: grid;
  gap: 12px;
}

.knowledge-source-list {
  display: grid;
  gap: 12px;
}

.knowledge-source {
  padding: 16px 18px;
}

.knowledge-source__title,
.chart-panel__title,
.result-path__copy,
.review-card__copy,
.highlight-card .review-card__copy {
  margin: 0;
}

.knowledge-source__title,
.chart-panel__title {
  font-size: 20px;
  line-height: 1.2;
  letter-spacing: -0.04em;
}

.knowledge-warning {
  color: #8f4a00;
}

.result-quick {
  min-height: 280px;
}

.review-card {
  padding: 20px 22px;
}

.review-card__body,
.review-card__block,
.review-card__split,
.chart-panel {
  display: grid;
  gap: 10px;
}

.review-card__split {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.review-card__copy {
  color: var(--foreground);
  font-size: 14px;
  line-height: 1.7;
}

.highlight-card {
  align-content: start;
}

@media (min-width: 1100px) {
  .result-page {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
    overflow-y: scroll;
    overflow-x: hidden;
  }

  .result-summary {
    padding: 14px 16px;
    grid-template-columns: minmax(0, 1.24fr) minmax(300px, 0.76fr);
    gap: 12px;
  }

  .result-summary__lead,
  .result-summary__scorecard,
  .result-summary__scorebox {
    gap: 8px;
  }

  .result-summary__title {
    max-width: 22ch;
    font-size: 28px;
    line-height: 1.02;
  }

  .result-summary .page-subtitle {
    display: -webkit-box;
    overflow: hidden;
    max-width: 80ch;
    font-size: 13px;
    line-height: 1.5;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .result-summary .hero-pill,
  .result-summary .status-pill {
    min-height: 28px;
    font-size: 11px;
  }

  .result-summary__scorebox {
    padding: 12px;
  }

  .hero-score {
    font-size: 34px;
  }

  .result-summary__actions {
    gap: 8px;
  }

  .result-summary__meta {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
  }

  .result-summary__metric {
    gap: 3px;
    padding: 8px 10px;
  }

  .result-summary__metric span {
    font-size: 11px;
  }

  .result-summary__metric strong {
    font-size: 14px;
  }

  .result-workbench {
    flex: 1 1 auto;
    grid-template-rows: auto minmax(0, 1fr);
    min-height: 0;
    overflow: hidden;
    min-height: 520px;
    padding: 16px;
    gap: 12px;
  }

  .result-layout,
  .result-layout__essay,
  .result-layout__analysis,
  .result-essay-panel {
    min-height: 0;
  }

  .result-layout {
    gap: 12px;
    grid-template-columns: minmax(320px, 0.96fr) minmax(0, 1.04fr);
  }

  .result-layout__essay {
    grid-template-rows: minmax(0, 1fr) auto;
    overflow: hidden;
  }

  .result-essay-panel {
    padding: 14px;
  }

  .result-quick {
    min-height: 0;
    gap: 6px;
    padding: 12px;
  }

  .result-quick .card-kicker {
    display: none;
  }

  .result-quick .section-title {
    font-size: 17px;
  }

  .result-quick .card-copy {
    display: -webkit-box;
    overflow: hidden;
    font-size: 12px;
    line-height: 1.45;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .result-quick .list-row {
    padding: 6px 0;
  }

  .result-quick .list-stack .list-row:nth-child(n+3) {
    display: none;
  }

  .result-quick .action-row {
    gap: 8px;
  }

  .result-quick .button-primary,
  .result-quick .button-secondary {
    min-height: 36px;
    padding: 8px 12px;
  }

  .result-panel {
    padding: 18px;
  }
}

@media (max-width: 1100px) {
  .result-summary,
  .result-layout,
  .result-card-grid,
  .chart-grid,
  .result-profile-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .result-summary__title {
    font-size: 34px;
  }

  .hero-score {
    font-size: 38px;
  }

  .result-summary__actions,
  .result-summary__meta,
  .review-card__split {
    grid-template-columns: 1fr;
  }
}
</style>
