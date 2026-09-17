<template>
  <main class="page-shell notebook-page">
    <section class="page-hero notebook-hero">
      <p class="page-eyebrow">Notebook</p>
      <h1 class="page-title">这里沉淀的是最值得复盘、也最该回流到下一篇里的错误。</h1>
      <p class="page-subtitle">
        它不是历史页的换皮，也不是画像页的附属模块。目标很直接：筛选、选中、复盘、标记已练。
      </p>
      <div class="hero-pills">
        <span class="hero-pill">{{ visibleItemsLabel }}</span>
        <span class="hero-pill">{{ reviewRateLabel }}</span>
      </div>
    </section>

    <section class="metric-grid metric-grid--4">
      <article class="metric-card">
        <p class="metric-label">累计错题数</p>
        <p class="metric-value">{{ totalItemsLabel }}</p>
        <p class="metric-caption">沉淀进错题本的总条目</p>
      </article>
      <article class="metric-card">
        <p class="metric-label">主导错误</p>
        <p class="metric-value">{{ dominantErrorTypeLabel }}</p>
        <p class="metric-caption">先处理重复最多的一类</p>
      </article>
      <article class="metric-card">
        <p class="metric-label">复习率</p>
        <p class="metric-value">{{ reviewRateLabel }}</p>
        <p class="metric-caption">已复习 / 累计错题</p>
      </article>
      <article class="metric-card">
        <p class="metric-label">下一步</p>
        <p class="metric-value notebook-metric-note">先刷语法，再冲逻辑</p>
        <p class="metric-caption">先把高频错误压下去</p>
      </article>
    </section>

    <section class="surface-card notebook-filters">
      <div class="chip-row">
        <button
          v-for="pill in errorTypePills"
          :key="pill.value"
          type="button"
          class="filter-pill"
          :class="{ 'filter-pill--active': activeErrorType === pill.value }"
          @click="activeErrorType = pill.value"
        >
          {{ pill.label }}
        </button>
      </div>
      <div class="chip-row">
        <button
          v-for="pill in taskTypePills"
          :key="pill.value"
          type="button"
          class="filter-pill"
          :class="{ 'filter-pill--active': activeTaskType === pill.value }"
          @click="activeTaskType = pill.value"
        >
          {{ pill.label }}
        </button>
      </div>
      <div class="chip-row">
        <button
          v-for="pill in reviewStatusPills"
          :key="pill.value"
          type="button"
          class="filter-pill"
          :class="{ 'filter-pill--active': activeReviewStatus === pill.value }"
          @click="activeReviewStatus = pill.value"
        >
          {{ pill.label }}
        </button>
      </div>
    </section>

    <section class="notebook-layout">
      <aside class="surface-card notebook-list">
        <div class="section-head">
          <div>
            <p class="card-kicker">Notebook Queue</p>
            <h2 class="section-title">错题列表</h2>
          </div>
          <button class="button-secondary" type="button" @click="notebookStore.fetchNotebook">刷新</button>
        </div>
        <p class="card-copy">默认按最近新增排序。左侧像待处理队列，右侧像当前复盘卡。</p>
        <div class="notebook-list__viewport scroll-pane">
          <div v-if="isNotebookBootstrapping" class="empty-state notebook-empty">
            <p class="card-kicker">Loading</p>
            <h3 class="empty-state__title">正在加载错题本。</h3>
            <p class="empty-state__copy">先拿到首包数据，再决定显示正式空态还是复盘列表。</p>
          </div>
          <div v-else-if="showNotebookErrorState" class="empty-state notebook-empty">
            <p class="card-kicker">Notebook Error</p>
            <h3 class="empty-state__title">错题本暂时不可用。</h3>
            <p class="empty-state__copy">如果只是网络短暂中断，不应该把失败渲染成“当前没有错题”。</p>
            <button class="button-secondary" type="button" @click="notebookStore.fetchNotebook">重新加载</button>
          </div>
          <template v-else>
            <button
              v-for="item in filteredItems"
              :key="item.id"
              type="button"
              class="notebook-item"
              :class="{ 'is-active': selectedItem?.id === item.id }"
              @click="notebookStore.selectItem(item.id)"
            >
              <div class="notebook-item__head">
                <span class="status-pill" :class="item.status === 'reviewed' ? 'status-pill--success' : 'status-pill--warning'">
                  {{ localizeErrorLabel(item.errorType) }}
                </span>
                <span class="metric-label">{{ formatTaskType(item.taskType) }}</span>
              </div>
              <p class="notebook-item__title">{{ truncate(item.sourceText, 72) }}</p>
            </button>
          </template>
          <div v-if="showNotebookFilterEmpty" class="empty-state notebook-empty">
            <p class="card-kicker">Notebook Empty</p>
            <h3 class="empty-state__title">当前筛选下没有可复盘条目。</h3>
            <p class="empty-state__copy">换一个错误类型、Task 或复习状态，或者先写新的作文让系统继续沉淀。</p>
          </div>
        </div>
      </aside>

      <article class="surface-card notebook-detail">
        <div class="notebook-detail__viewport scroll-pane">
          <div v-if="isNotebookBootstrapping" class="empty-state notebook-empty-detail">
            <p class="card-kicker">Loading</p>
            <h3 class="empty-state__title">正在装配当前复盘卡。</h3>
            <p class="empty-state__copy">详情区只有在首包完成后才应该决定显示哪条错题。</p>
          </div>
          <div v-else-if="selectedItem" class="notebook-detail__content">
            <div class="section-head">
              <div>
                <p class="card-kicker">Error Detail</p>
                <h2 class="section-title">错题详情</h2>
              </div>
              <span class="status-pill" :class="selectedItem.status === 'reviewed' ? 'status-pill--success' : 'status-pill--warning'">
                {{ selectedItem.status === "reviewed" ? "已复习" : "待复习" }}
              </span>
            </div>

            <div class="notebook-detail__sections">
              <section class="surface-muted">
                <p class="card-kicker">主导问题</p>
                <p class="notebook-detail__copy">{{ localizeErrorLabel(selectedItem.errorType) }}</p>
              </section>
              <section class="surface-muted">
                <p class="card-kicker">原句</p>
                <p class="notebook-detail__copy">{{ selectedItem.sourceText }}</p>
              </section>
              <section class="surface-muted">
                <p class="card-kicker">问题解释</p>
                <p class="notebook-detail__copy">{{ selectedItem.explanation }}</p>
              </section>
              <section class="surface-muted">
                <p class="card-kicker">推荐改写</p>
                <p class="notebook-detail__copy">{{ selectedItem.revision }}</p>
              </section>
              <section class="surface-muted notebook-detail__wide">
                <p class="card-kicker">重写句子</p>
                <p class="notebook-detail__copy">{{ selectedItem.revisedSentence }}</p>
              </section>
            </div>

            <div class="notebook-detail__meta">
              <div class="list-row">
                <p class="list-row__title">作文题型</p>
                <p class="list-row__meta">{{ formatTaskType(selectedItem.taskType) }}</p>
              </div>
            </div>
          </div>
          <div v-else-if="showNotebookErrorState" class="empty-state notebook-empty-detail">
            <p class="card-kicker">Retry</p>
            <h3 class="empty-state__title">当前没有可读的错题详情。</h3>
            <p class="empty-state__copy">先把数据重新拉回来，再决定复盘哪一条。</p>
          </div>
          <div v-else class="empty-state notebook-empty-detail">
            <p class="card-kicker">Select One</p>
            <h3 class="empty-state__title">先从左边选一条错题。</h3>
            <p class="empty-state__copy">这页的价值不在于列很多卡，而在于把当前要复盘的错误卡住不放。</p>
          </div>
        </div>

        <div class="action-row">
          <button
            class="button-primary"
            type="button"
            :disabled="!selectedItem || selectedItem.status === 'reviewed' || notebookStore.reviewActionState === 'submitting'"
            @click="markCurrentReviewed"
          >
            标记已复习
          </button>
          <RouterLink class="button-secondary" to="/history">查看来源结果</RouterLink>
          <span class="feedback-text">动作状态：{{ notebookStore.reviewActionState }}</span>
        </div>
        <p v-if="showNotebookInlineError" class="feedback-text feedback-text--error">{{ notebookStore.errorMessage }}</p>
      </article>
    </section>

    <section class="notebook-bottom-grid">
      <article class="surface-card notebook-advice">
        <p class="card-kicker">复习建议 1</p>
        <h3 class="section-title">把同类错误放到一起复盘。</h3>
        <p class="card-copy">先看一组同类问题，效率会比按作文顺序散看更高。</p>
      </article>
      <article class="surface-card notebook-advice">
        <p class="card-kicker">复习建议 2</p>
        <h3 class="section-title">解释和改写必须一起记。</h3>
        <p class="card-copy">只记“错了什么”不够，还要记住“为什么错”和“正确怎么写”。</p>
      </article>
      <article class="action-rail notebook-advice notebook-advice--dark">
        <p class="card-kicker">下一步</p>
        <h3 class="section-title">先复习，再开下一篇。</h3>
        <p class="card-copy">先复盘，再开新作文。让这些错题真正回流到下一篇里。</p>
        <RouterLink class="button-primary notebook-advice__cta" to="/submit">去写新作文</RouterLink>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useNotebookStore } from "@/stores";
import { localizeErrorLabel } from "@/utils/localization";
import { buildTaskTypeOptions, formatTaskType } from "@/utils/taskType";

const notebookStore = useNotebookStore();
const activeErrorType = ref("all");
const activeTaskType = ref("all");
const activeReviewStatus = ref("all");

const selectedItem = computed(() => notebookStore.selectedItem);
const isNotebookBootstrapping = computed(() => !notebookStore.hasFetched);
const reviewRateLabel = computed(() => {
  if (!notebookStore.hasFetched) return "加载中";
  if (!notebookStore.summary.totalItems) return "0%";
  return `${Math.round((notebookStore.summary.reviewedItems / notebookStore.summary.totalItems) * 100)}%`;
});
const totalItemsLabel = computed(() =>
  notebookStore.hasFetched ? String(notebookStore.summary.totalItems) : "--"
);
const dominantErrorTypeLabel = computed(() => {
  if (!notebookStore.hasFetched) return "--";
  if (!notebookStore.summary.totalItems) return "暂无";
  return localizeErrorLabel(notebookStore.summary.dominantErrorType);
});
const errorTypePills = computed(() => [
  { label: "全部", value: "all" },
  ...Array.from(new Set(notebookStore.items.map((item) => item.errorType))).slice(0, 4).map((value) => ({
    label: localizeErrorLabel(value),
    value
  }))
]);
const taskTypePills = [
  { label: "全部", value: "all" },
  ...buildTaskTypeOptions()
];
const reviewStatusPills = [
  { label: "全部", value: "all" },
  { label: "待复习", value: "pending" },
  { label: "已复习", value: "reviewed" }
];
const filteredItems = computed(() =>
  notebookStore.items.filter((item) => {
    const matchError = activeErrorType.value === "all" || item.errorType === activeErrorType.value;
    const matchTask = activeTaskType.value === "all" || item.taskType === activeTaskType.value;
    const matchReview =
      activeReviewStatus.value === "all" ||
      (activeReviewStatus.value === "reviewed" ? item.status === "reviewed" : item.status !== "reviewed");
    return matchError && matchTask && matchReview;
  })
);
const visibleItemsLabel = computed(() =>
  notebookStore.hasFetched ? `${filteredItems.value.length} 条当前可见错题` : "错题加载中"
);
const showNotebookErrorState = computed(
  () => notebookStore.hasFetched && !!notebookStore.errorMessage && !notebookStore.items.length
);
const showNotebookFilterEmpty = computed(
  () => notebookStore.hasFetched && !notebookStore.errorMessage && !filteredItems.value.length
);
const showNotebookInlineError = computed(
  () => !!notebookStore.errorMessage && (!showNotebookErrorState.value || notebookStore.reviewActionState === "error")
);

async function markCurrentReviewed() {
  if (!selectedItem.value) return;
  await notebookStore.markReviewed(selectedItem.value.id);
}

function truncate(value: string, maxLength: number): string {
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
}

onMounted(() => {
  if (!notebookStore.hasFetched && !notebookStore.loading) {
    void notebookStore.fetchNotebook();
  }
});

watch(
  filteredItems,
  (items) => {
    const currentId = notebookStore.selectedItemId;
    if (!items.length) {
      if (currentId) {
        notebookStore.selectItem("");
      }
      return;
    }
    if (!items.some((item) => item.id === currentId)) {
      notebookStore.selectItem(items[0].id);
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.notebook-page {
  align-content: start;
}

.notebook-hero {
  max-width: 980px;
}

.notebook-metric-note {
  font-size: 24px;
  line-height: 1.12;
}

.notebook-filters,
.notebook-detail__content,
.notebook-advice {
  display: grid;
  gap: 16px;
}

.notebook-layout,
.notebook-bottom-grid,
.notebook-detail__sections {
  display: grid;
  gap: 22px;
}

.notebook-layout {
  grid-template-columns: minmax(320px, 0.92fr) minmax(0, 1.08fr);
}

.notebook-bottom-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.notebook-list,
.notebook-detail {
  align-content: start;
}

.notebook-list__viewport,
.notebook-detail__viewport {
  min-height: 0;
}

.notebook-item {
  display: grid;
  gap: 10px;
  width: 100%;
  padding: 16px;
  border-radius: var(--radius-card);
  background: var(--card);
  box-shadow: var(--shadow-border);
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    box-shadow 0.16s ease,
    background-color 0.16s ease;
}

.notebook-item:hover,
.notebook-item.is-active {
  transform: translateY(-1px);
  background: var(--muted);
  box-shadow: var(--shadow-card);
}

.notebook-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.notebook-item__title,
.notebook-detail__copy {
  margin: 0;
}

.notebook-item__title {
  color: var(--foreground);
  font-size: 15px;
  line-height: 1.6;
}

.notebook-detail__sections {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.notebook-detail__wide {
  grid-column: 1 / -1;
}

.notebook-detail__copy {
  color: var(--foreground);
  font-size: 14px;
  line-height: 1.7;
}

.notebook-empty,
.notebook-empty-detail {
  margin-top: 8px;
}

.notebook-advice__cta {
  margin-top: auto;
}

@media (min-width: 1100px) {
  .notebook-page {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
    overflow-y: scroll;
    overflow-x: hidden;
  }

  .notebook-hero {
    padding: 16px 18px;
    gap: 8px;
  }

  .notebook-hero .page-title {
    max-width: 30ch;
    font-size: 28px;
  }

  .notebook-hero .page-subtitle {
    max-width: 92ch;
    font-size: 13px;
    line-height: 1.45;
  }

  .notebook-page .metric-grid {
    gap: 10px;
  }

  .notebook-page .metric-card {
    gap: 6px;
    padding: 12px 14px;
  }

  .notebook-page .metric-value {
    font-size: 24px;
  }

  .notebook-page .metric-caption {
    display: none;
  }

  .notebook-metric-note {
    font-size: 18px;
  }

  .notebook-filters {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    padding: 12px;
  }

  .notebook-filters .chip-row {
    flex-wrap: nowrap;
    gap: 6px;
    min-height: 32px;
    overflow-x: auto;
    overflow-y: hidden;
    align-content: center;
    overscroll-behavior-x: contain;
    scrollbar-width: thin;
  }

  .notebook-filters .chip-row::-webkit-scrollbar {
    height: 8px;
  }

  .notebook-filters .chip-row::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: rgba(23, 23, 23, 0.2);
  }

  .notebook-filters .filter-pill {
    min-height: 30px;
    padding: 0 10px;
    font-size: 11px;
  }

  .notebook-layout {
    flex: 1 1 auto;
    min-height: 440px;
    overflow: hidden;
  }

  .notebook-list {
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr);
    min-height: 0;
    overflow: hidden;
    gap: 10px;
    padding: 18px;
  }

  .notebook-detail {
    display: grid;
    grid-template-rows: minmax(0, 1fr) auto auto;
    min-height: 0;
    overflow: hidden;
    gap: 10px;
    padding: 18px;
  }

  .notebook-list .section-title,
  .notebook-detail .section-title {
    font-size: 20px;
  }

  .notebook-list .card-copy,
  .notebook-detail .card-copy {
    font-size: 12px;
    line-height: 1.45;
  }

  .notebook-item {
    gap: 8px;
    padding: 12px;
  }

  .notebook-item__title {
    display: -webkit-box;
    overflow: hidden;
    font-size: 13px;
    line-height: 1.45;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .notebook-detail__sections {
    gap: 12px;
  }

  .notebook-list__viewport,
  .notebook-detail__viewport {
    min-height: 220px;
  }

  .notebook-detail__copy {
    font-size: 13px;
    line-height: 1.55;
  }

  .notebook-bottom-grid {
    gap: 10px;
  }

  .notebook-advice {
    gap: 8px;
    padding: 12px;
  }

  .notebook-advice .section-title {
    font-size: 17px;
  }

  .notebook-advice .card-copy {
    display: -webkit-box;
    overflow: hidden;
    font-size: 12px;
    line-height: 1.4;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 1;
  }

  .notebook-advice .card-kicker {
    font-size: 10px;
  }
}

@media (max-width: 1100px) {
  .notebook-layout,
  .notebook-bottom-grid,
  .notebook-detail__sections {
    grid-template-columns: 1fr;
  }
}
</style>
