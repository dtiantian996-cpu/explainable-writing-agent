<template>
  <main class="page-shell history-page">
    <section class="page-hero history-hero">
      <p class="page-eyebrow">History</p>
      <h1 class="page-title">最近的总分波动、日期与回看入口，都收在这里。</h1>
      <p class="page-subtitle">
        默认从最新记录开始。标题、题型、时间和结果入口落在同一层里，不让历史页退化成一张没有判断的数据表。
      </p>
      <div class="hero-pills">
        <span class="hero-pill">{{ visibleCountLabel }}</span>
        <span class="hero-pill">{{ completedCountLabel }}</span>
      </div>
    </section>

    <section class="surface-card history-shell">
      <div class="table-controls history-controls">
        <label class="history-search-label" for="history-search">搜索历史记录</label>
        <input
          id="history-search"
          name="historySearch"
          v-model.trim="searchQuery"
          class="search-shell history-search"
          type="search"
          placeholder="Search..."
        />
        <button class="button-secondary" type="button" @click="historyStore.fetchHistory">刷新</button>
        <RouterLink class="button-secondary" to="/submit">+ 新作文</RouterLink>
      </div>

      <p v-if="historyStore.errorMessage && historyStore.items.length" class="feedback-text feedback-text--error">
        {{ historyStore.errorMessage }}
      </p>

      <div v-if="isBootstrapping" class="empty-state">
        <p class="card-kicker">Loading</p>
        <h2 class="empty-state__title">正在加载历史记录。</h2>
        <p class="empty-state__copy">先确认首包数据，再决定是显示正式空态还是历史表格。</p>
      </div>

      <div v-else-if="showErrorState" class="empty-state">
        <p class="card-kicker">History Error</p>
        <h2 class="empty-state__title">历史记录暂时不可用。</h2>
        <p class="empty-state__copy">网络或后端暂时没有响应。恢复连接后再刷新，不要把失败态误渲染成空态。</p>
        <button class="button-secondary" type="button" @click="historyStore.fetchHistory">重新加载</button>
      </div>

      <div v-else-if="showEmptyState" class="empty-state">
        <p class="card-kicker">History Empty</p>
        <h2 class="empty-state__title">还没有评估记录，先交第一篇。</h2>
        <p class="empty-state__copy">
          历史页不应该是一张空白表。没有数据时，至少要告诉用户下一步动作和之后会在这里看到什么。
        </p>
        <RouterLink class="button-primary" to="/submit">去提交作文</RouterLink>
      </div>

      <template v-else>
        <div class="table-shell history-table-shell scroll-pane">
          <table class="table">
            <thead>
              <tr>
                <th>作文标题 / 题型 / 分数 / 日期 / 动作</th>
                <th />
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in filteredItems" :key="item.assessmentId">
                <td>
                  <div class="history-row">
                    <div class="history-row__main">
                      <p class="history-row__title">{{ item.topic }}</p>
                      <p class="history-row__meta">{{ formatTaskType(item.taskType) }} · {{ formatScore(item) }} · {{ formatDate(item.createdAt) }}</p>
                    </div>
                    <RouterLink class="button-link" :to="`/result/${item.assessmentId}`">查看全部</RouterLink>
                  </div>
                </td>
                <td class="history-row__status">
                  <span class="status-pill" :class="statusClass(item.status)">{{ formatScore(item) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="!filteredItems.length" class="empty-state history-empty-search">
          <p class="card-kicker">No Match</p>
          <h2 class="empty-state__title">当前搜索没有命中记录。</h2>
          <p class="empty-state__copy">可以换题目关键词、题型，或者先清空搜索词。</p>
          <button class="button-secondary" type="button" @click="searchQuery = ''">清空搜索</button>
        </div>

        <div v-else class="history-summary-row">
          <p class="feedback-text">Showing {{ filteredItems.length }} records</p>
          <div class="hero-pills">
            <span class="hero-pill">Prev</span>
            <span class="hero-pill">Next</span>
          </div>
        </div>

        <div v-if="previewCards.length" class="history-preview-grid">
          <article
            v-for="(item, index) in previewCards"
            :key="item.assessmentId"
            class="surface-card history-preview"
            :class="{ 'history-preview--dark': index === previewCards.length - 1 }"
          >
            <p class="card-kicker">Preview</p>
            <h3 class="history-preview__title">{{ item.topic }}</h3>
            <p class="card-copy">{{ formatIeltsBandWithScale(item.overallScore) }} · {{ formatDate(item.createdAt) }}</p>
            <p class="history-preview__copy">{{ buildPreviewCopy(item, index) }}</p>
          </article>
        </div>
      </template>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { useHistoryStore } from "@/stores";
import type { HistoryItem } from "@/types/api";
import { formatIeltsBandWithScale } from "@/utils/score";
import { formatTaskType } from "@/utils/taskType";

const historyStore = useHistoryStore();
const searchQuery = ref("");

const filteredItems = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase();
  if (!keyword) return historyStore.items;
  return historyStore.items.filter((item) => {
    const haystack = `${item.topic} ${item.taskType}`.toLowerCase();
    return haystack.includes(keyword);
  });
});
const completedCount = computed(
  () => historyStore.items.filter((item) => item.status === "completed").length
);
const isBootstrapping = computed(() => !historyStore.hasFetched);
const showErrorState = computed(
  () => historyStore.hasFetched && !!historyStore.errorMessage && !historyStore.items.length
);
const showEmptyState = computed(
  () => historyStore.hasFetched && !historyStore.errorMessage && !historyStore.items.length
);
const visibleCountLabel = computed(() =>
  historyStore.hasFetched ? `${filteredItems.value.length} 条记录` : "记录加载中"
);
const completedCountLabel = computed(() =>
  historyStore.hasFetched ? `${completedCount.value} 条已完成` : "完成数加载中"
);
const previewCards = computed(() =>
  historyStore.items.filter((item) => item.status === "completed").slice(0, 3)
);

function formatDate(value: string): string {
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function formatScore(item: HistoryItem): string {
  if (item.status === "completed") {
    return formatIeltsBandWithScale(item.overallScore);
  }
  if (item.status === "failed") {
    return "失败";
  }
  return "进行中";
}

function statusClass(status: HistoryItem["status"]) {
  return {
    "status-pill--success": status === "completed",
    "status-pill--error": status === "failed",
    "status-pill--info": status === "queued" || status === "processing"
  };
}

function buildPreviewCopy(item: HistoryItem, index: number): string {
  if (index === previewCards.value.length - 1) {
    return "把这一篇当成当前回看锚点，先判断它离目标差在哪里。";
  }
  return "亮点、扣分点和回看入口都集中收在这一行。";
}

onMounted(() => {
  if (!historyStore.hasFetched && !historyStore.loading) {
    void historyStore.fetchHistory();
  }
});
</script>

<style scoped>
.history-page {
  align-content: start;
}

.history-hero {
  max-width: 980px;
}

.history-shell {
  display: grid;
  gap: 18px;
}

.history-controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 10px;
}

.history-search {
  max-width: 360px;
}

.history-search-label {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.history-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.history-row__main {
  display: grid;
  gap: 4px;
}

.history-row__title,
.history-preview__title,
.history-preview__copy {
  margin: 0;
}

.history-row__title {
  color: var(--foreground);
  font-size: 14px;
}

.history-row__meta {
  margin: 0;
  color: var(--muted-foreground);
  font-size: 12px;
}

.history-row__status {
  width: 140px;
}

.history-summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-preview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.history-preview {
  display: grid;
  gap: 10px;
  min-height: 170px;
}

.history-preview--dark {
  background: #171717;
  color: #ffffff;
  box-shadow:
    0 0 0 1px rgba(0, 0, 0, 0.08),
    0 20px 32px -24px rgba(0, 0, 0, 0.4);
}

.history-preview--dark .card-kicker,
.history-preview--dark .card-copy {
  color: rgba(255, 255, 255, 0.72);
}

.history-preview__title {
  font-size: 18px;
  line-height: 1.3;
  letter-spacing: -0.04em;
}

.history-preview__copy {
  color: inherit;
  font-size: 13px;
  line-height: 1.65;
}

.history-empty-search {
  margin-top: 4px;
}

@media (min-width: 1100px) {
  .history-page {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
    overflow-y: scroll;
    overflow-x: hidden;
  }

  .history-hero {
    padding: 18px 20px;
    gap: 8px;
  }

  .history-hero .page-title {
    max-width: 24ch;
    font-size: 30px;
  }

  .history-hero .page-subtitle {
    max-width: 90ch;
    font-size: 13px;
    line-height: 1.5;
  }

  .history-shell {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
    min-height: 500px;
    gap: 10px;
    padding: 14px;
  }

  .history-table-shell {
    flex: 1 1 auto;
    min-height: 260px;
    overflow-y: auto;
  }

  .history-summary-row {
    gap: 8px;
  }

  .history-preview-grid {
    gap: 10px;
  }

  .history-preview {
    min-height: 112px;
    gap: 6px;
    padding: 14px;
  }

  .history-preview__title {
    font-size: 15px;
  }

  .history-preview__copy {
    display: -webkit-box;
    overflow: hidden;
    font-size: 12px;
    line-height: 1.45;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }
}

@media (max-width: 980px) {
  .history-controls,
  .history-preview-grid {
    grid-template-columns: 1fr;
  }

  .history-search {
    max-width: none;
  }
}
</style>
