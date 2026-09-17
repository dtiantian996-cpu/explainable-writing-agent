<template>
  <main class="page-shell submit-page">
    <section class="page-hero submit-hero">
      <p class="page-eyebrow">New Essay</p>
      <h1 class="page-title">上传作文，排队后直接进入结果页。</h1>
      <p class="page-subtitle">
        文本优先，图片补充。全流程先进入一次 Submit Loading，再进入结果页轮询，不把输入流拆成两套系统。
      </p>
      <div class="hero-pills">
        <span class="hero-pill">TEXT FIRST · OCR AS SUPPORT · SINGLE ASSESSMENT PIPELINE</span>
      </div>
    </section>

    <section class="surface-card submit-shell">
      <template v-if="assessmentStore.submitState === 'creating'">
        <div class="submit-loading">
          <p class="card-kicker">Submit Loading</p>
          <h2 class="section-title">题目、正文和上传素材已经排队入链。</h2>
          <p class="card-copy">
            当前仍停留在提交页。等 assessment 创建完成后，页面会自动进入结果页继续轮询，而不是在这里假装完成。
          </p>
          <div class="submit-progress">
            <div class="submit-progress__track">
              <div class="submit-progress__fill" />
            </div>
            <div class="result-state__meta">
              <span>正在创建 assessment</span>
              <strong>5%</strong>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="submit-shell__top">
          <div class="tab-strip">
            <button
              type="button"
              class="tab-button"
              :class="{ 'is-active': primaryMode === 'text' }"
              @click="switchPrimaryMode('text')"
            >
              文本输入
            </button>
            <button
              type="button"
              class="tab-button"
              :class="{ 'is-active': primaryMode === 'image' }"
              @click="switchPrimaryMode('image')"
            >
              图片上传
            </button>
          </div>
          <span class="hero-pill" :class="{ 'hero-pill--warm': assessmentStore.draft.images.length }">{{ modeSummary }}</span>
        </div>

        <div class="submit-editor scroll-pane">
          <label class="field-stack" for="essay-topic">
            <span class="field-label">作文题目</span>
            <input
              id="essay-topic"
              name="topic"
              :value="assessmentStore.draft.topic"
              class="input-shell"
              type="text"
              placeholder="请输入作文题目"
              @input="onTopicInput"
            />
          </label>

          <label v-if="primaryMode === 'text'" class="field-stack submit-editor__body" for="essay-body">
            <span class="field-label">作文正文</span>
            <textarea
              id="essay-body"
              name="essayText"
              :value="assessmentStore.draft.essayText"
              class="textarea-shell submit-editor__textarea scroll-pane"
              rows="10"
              placeholder="在这里粘贴你的作文正文。"
              @input="onEssayInput"
            />
          </label>

          <div class="submit-meta-row" :class="{ 'submit-meta-row--compact': primaryMode === 'image' }">
            <article v-if="showTaskTypeControls" class="surface-muted submit-meta-card">
              <p class="card-kicker">作文题型</p>
              <div class="chip-row">
                <button
                  v-for="task in taskOptions"
                  :key="task.value"
                  type="button"
                  class="filter-pill"
                  :class="{ 'filter-pill--active': assessmentStore.draft.taskType === task.value }"
                  @click="assessmentStore.updateDraft({ taskType: task.value })"
                >
                  {{ task.label }}
                </button>
              </div>
            </article>

            <article class="surface-muted submit-meta-card">
              <p class="card-kicker">Words</p>
              <h3 class="submit-meta__value">{{ assessmentStore.wordCount }}</h3>
              <p class="feedback-text">默认按任务二口径提示字数，建议保持 250+ 词</p>
            </article>

            <article class="surface-muted submit-meta-card">
              <p class="card-kicker">{{ primaryMode === "text" ? "Mode" : "OCR" }}</p>
              <h3 class="submit-meta__value">{{ primaryMode === "text" ? "文本" : fileCountLabel }}</h3>
              <p class="feedback-text">{{ primaryMode === "text" ? "当前只提交正文内容" : uploadHint }}</p>
            </article>
          </div>

          <label v-if="primaryMode === 'image'" class="surface-muted submit-upload" for="essay-upload">
            <div class="submit-upload__head">
              <div>
                <p class="card-kicker">Upload OCR</p>
                <h3 class="submit-upload__title">{{ uploadTitle }}</h3>
              </div>
              <span class="hero-pill" :class="{ 'hero-pill--warm': assessmentStore.draft.images.length }">
                {{ assessmentStore.draft.images.length ? "OCR Ready" : "Image Optional" }}
              </span>
            </div>
            <input
              id="essay-upload"
              name="images"
              class="submit-upload__input"
              multiple
              accept="image/*,.pdf"
              type="file"
              @change="onImageChange"
            />
            <p class="card-copy">{{ uploadCopy }}</p>
            <div v-if="fileNames.length" class="list-stack submit-upload__files">
              <div v-for="name in fileNames" :key="name" class="list-row">
                <p class="list-row__title">{{ name }}</p>
                <p class="list-row__meta">已就绪</p>
              </div>
            </div>
          </label>

          <article class="surface-muted submit-progress-panel">
            <div class="section-head">
              <div>
                <p class="card-kicker">Progress</p>
                <h3 class="submit-upload__title">提交前状态</h3>
              </div>
              <span class="hero-pill">{{ progressStateLabel }}</span>
            </div>
            <p class="card-copy">{{ progressCopy }}</p>
            <div class="submit-progress">
              <div class="submit-progress__track">
                <div class="submit-progress__fill" :class="{ 'submit-progress__fill--image': assessmentStore.draft.images.length > 0 }" />
              </div>
            </div>
          </article>

          <div class="submit-shell__footer">
            <button class="button-primary submit-shell__cta" type="button" :disabled="!canSubmit" @click="onCreateAssessment">
              全部批改
            </button>
            <p class="feedback-text">四维评分 / 逐句建议 / 亮点分析 / 学习建议</p>
            <p v-if="assessmentStore.errorMessage" class="feedback-text feedback-text--error">
              {{ assessmentStore.errorMessage }}
            </p>
          </div>
        </div>
      </template>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useAssessmentStore } from "@/stores";
import { buildPrimaryModeDraftPatch, shouldShowTaskTypeControls } from "./submitMode";
import { buildTaskTypeOptions } from "@/utils/taskType";

const router = useRouter();
const assessmentStore = useAssessmentStore();
const primaryMode = ref<"text" | "image">("text");

const taskOptions = buildTaskTypeOptions();
const showTaskTypeControls = computed(() => shouldShowTaskTypeControls(primaryMode.value));

const canSubmit = computed(
  () =>
    assessmentStore.submitState !== "creating" &&
    assessmentStore.draft.topic.trim().length > 0 &&
    (primaryMode.value === "text"
      ? assessmentStore.draft.essayText.trim().length > 0
      : assessmentStore.draft.images.length > 0)
);
const fileNames = computed(() => assessmentStore.draft.images.map((file) => file.name));
const fileCountLabel = computed(() => {
  if (!assessmentStore.draft.images.length) return "未上传";
  return `${assessmentStore.draft.images.length} 份待识别`;
});
const modeSummary = computed(() => {
  if (primaryMode.value === "text") {
    return "当前只提交正文，不再附带图片";
  }
  if (assessmentStore.draft.images.length) {
    return "图片 OCR 只识别正文，直接进入统一评估链路";
  }
  return "请选择图片或 PDF，系统会先识别正文再进入评估";
});
const uploadTitle = computed(() =>
  assessmentStore.draft.images.length
    ? "图片已加入 OCR 队列，识别完成后直接进入评估。"
    : "支持图片与 PDF，OCR 只负责识别题目和正文"
);
const uploadCopy = computed(() =>
  assessmentStore.draft.images.length
    ? "支持 JPG / PNG / PDF。系统会先做 OCR，再进入统一评估。"
    : "支持 JPG / PNG / PDF。上传后会先做 OCR，再进入统一评估。"
);
const uploadHint = computed(() =>
  assessmentStore.draft.images.length ? "已加入 OCR 队列" : "OCR 先识别正文，再进入评估"
);
const progressStateLabel = computed(() =>
  primaryMode.value === "text" ? "默认态 / 文本优先" : "上传态 / OCR 中"
);
const progressCopy = computed(() => {
  if (primaryMode.value === "image") {
    return assessmentStore.draft.images.length
      ? "上传图片后，系统会先识别题目与正文，再送进统一评估链路。"
      : "当前是图片模式。先选择图片或 PDF，然后触发 OCR 和后续评估。";
  }
  return "当前是文本模式。提交时只使用正文内容，不再附带 OCR 图片。";
});

function switchPrimaryMode(mode: "text" | "image") {
  primaryMode.value = mode;
  assessmentStore.updateDraft(buildPrimaryModeDraftPatch(mode));
}

function onTopicInput(event: Event) {
  const target = event.target as HTMLInputElement;
  assessmentStore.updateDraft({ topic: target.value });
}

function onEssayInput(event: Event) {
  const target = event.target as HTMLTextAreaElement;
  assessmentStore.updateDraft({ essayText: target.value });
}

function onImageChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const images = Array.from(target.files ?? []);
  assessmentStore.updateDraft({ images, ...buildPrimaryModeDraftPatch("image") });
  if (images.length) {
    primaryMode.value = "image";
  }
}

async function onCreateAssessment() {
  const id = await assessmentStore.createAssessment();
  if (id) {
    void router.push(`/result/${id}`);
  }
}
</script>

<style scoped>
.submit-page {
  justify-items: start;
}

.submit-hero {
  max-width: 920px;
}

.submit-shell {
  max-width: 920px;
  width: 100%;
  gap: 20px;
}

.submit-shell__top,
.submit-editor,
.submit-progress-panel,
.submit-shell__footer {
  display: grid;
  gap: 18px;
}

.submit-shell__top {
  align-items: center;
}

.submit-editor__body {
  grid-column: 1 / -1;
}

.submit-editor__textarea {
  min-height: 240px;
}

.submit-meta-row {
  display: grid;
  grid-template-columns: 1.2fr 0.7fr 0.7fr;
  gap: 14px;
}

.submit-meta-row--compact {
  grid-template-columns: 1fr 1fr;
}

.submit-meta-card {
  gap: 12px;
}

.submit-meta__value {
  margin: 0;
  font-size: 32px;
  line-height: 1;
  letter-spacing: -0.07em;
}

.submit-upload {
  display: grid;
  gap: 14px;
}

.submit-upload__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.submit-upload__input {
  font-size: 13px;
}

.submit-upload__title {
  margin: 0;
  font-size: 22px;
  line-height: 1.16;
  letter-spacing: -0.05em;
}

.submit-upload__files {
  gap: 0;
}

.submit-progress {
  display: grid;
  gap: 8px;
}

.submit-progress__track {
  height: 8px;
  border-radius: var(--radius-pill);
  background: #efefef;
  overflow: hidden;
}

.submit-progress__fill {
  width: 34%;
  height: 100%;
  background: #171717;
}

.submit-progress__fill--image {
  width: 68%;
}

.submit-shell__cta {
  width: 100%;
}

.submit-loading {
  display: grid;
  gap: 18px;
  min-height: 520px;
  align-content: center;
}

@media (min-width: 1100px) {
  .submit-page {
    grid-template-rows: auto minmax(0, 1fr);
    min-height: 0;
    overflow-y: scroll;
    overflow-x: hidden;
  }

  .submit-shell {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    min-height: 520px;
  }

  .submit-editor {
    flex: 1 1 auto;
    min-height: 300px;
    padding-right: 4px;
  }

  .submit-editor__textarea {
    min-height: 320px;
    max-height: min(42vh, 420px);
    overflow-y: auto;
    resize: none;
  }

  .submit-loading {
    flex: 1 1 auto;
    min-height: 0;
  }
}

@media (max-width: 900px) {
  .submit-meta-row {
    grid-template-columns: 1fr;
  }
}

@media (max-height: 819px) {
  .submit-hero,
  .submit-shell {
    max-width: none;
  }

  .submit-shell {
    gap: 16px;
  }

  .submit-shell__top,
  .submit-editor,
  .submit-progress-panel,
  .submit-shell__footer {
    gap: 14px;
  }

  .submit-editor__textarea {
    min-height: 200px;
  }

  .submit-meta-row {
    gap: 10px;
  }

  .submit-meta-card {
    gap: 8px;
  }

  .submit-meta__value {
    font-size: 26px;
  }

  .submit-upload {
    gap: 10px;
  }

  .submit-upload__title {
    font-size: 18px;
  }
}
</style>
