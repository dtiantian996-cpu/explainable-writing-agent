<template>
  <div class="essay-viewer">
    <div class="essay-viewer__head">
      <p class="essay-viewer__eyebrow">Essay / Original</p>
      <p class="essay-viewer__meta">{{ summaryLine }}</p>
    </div>
    <EditorContent v-if="editor" :editor="editor" class="essay-viewer__content scroll-pane" />
    <div v-else class="essay-viewer__empty scroll-pane">原文还在加载。</div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import {
  EditorContent,
  Mark,
  Node,
  mergeAttributes,
  useEditor
} from "@tiptap/vue-3";
import type { SuggestionItem } from "@/types/api";

const props = defineProps<{
  text: string;
  suggestions: SuggestionItem[];
}>();

const Doc = Node.create({
  name: "doc",
  topNode: true,
  content: "block+"
});

const Paragraph = Node.create({
  name: "paragraph",
  group: "block",
  content: "inline*",
  parseHTML() {
    return [{ tag: "p" }];
  },
  renderHTML({ HTMLAttributes }) {
    return ["p", HTMLAttributes, 0];
  }
});

const Text = Node.create({
  name: "text",
  group: "inline"
});

const HardBreak = Node.create({
  name: "hardBreak",
  inline: true,
  group: "inline",
  selectable: false,
  parseHTML() {
    return [{ tag: "br" }];
  },
  renderHTML() {
    return ["br"];
  }
});

const ErrorMark = Mark.create({
  name: "errorMark",
  inclusive: false,
  addAttributes() {
    return {
      errorType: {
        default: "error"
      }
    };
  },
  parseHTML() {
    return [{ tag: "mark[data-error-type]" }];
  },
  renderHTML({ HTMLAttributes }) {
    return [
      "mark",
      mergeAttributes(HTMLAttributes, {
        class: "essay-error-mark"
      }),
      0
    ];
  }
});

type ContentNode =
  | { type: "text"; text: string; marks?: Array<{ type: "errorMark"; attrs: { errorType: string } }> }
  | { type: "hardBreak" };

function toInlineNodes(text: string, errorType?: string): ContentNode[] {
  const parts = text.split("\n");
  const nodes: ContentNode[] = [];

  parts.forEach((part, index) => {
    if (part) {
      nodes.push(
        errorType
          ? {
              type: "text",
              text: part,
              marks: [{ type: "errorMark", attrs: { errorType } }]
            }
          : {
              type: "text",
              text: part
            }
      );
    }

    if (index < parts.length - 1) {
      nodes.push({ type: "hardBreak" });
    }
  });

  return nodes;
}

function buildParagraphContent(text: string, suggestions: SuggestionItem[]): ContentNode[] {
  const ordered = [...suggestions]
    .filter((item) => item.positionEnd > item.positionStart)
    .sort((left, right) => left.positionStart - right.positionStart);

  const nodes: ContentNode[] = [];
  let cursor = 0;

  for (const item of ordered) {
    const start = Math.max(cursor, Math.max(0, item.positionStart));
    const end = Math.min(text.length, Math.max(start, item.positionEnd));

    if (start > cursor) {
      nodes.push(...toInlineNodes(text.slice(cursor, start)));
    }

    if (end > start) {
      nodes.push(...toInlineNodes(text.slice(start, end), item.errorType));
      cursor = end;
    }
  }

  if (cursor < text.length) {
    nodes.push(...toInlineNodes(text.slice(cursor)));
  }

  return nodes.length ? nodes : [{ type: "text", text }];
}

function buildDocContent(text: string, suggestions: SuggestionItem[]) {
  const safeText = text.trim() || "当前结果没有可展示的原文内容。";
  const paragraphs = safeText.split(/\n{2,}/).filter(Boolean);

  return {
    type: "doc",
    content: paragraphs.map((paragraph) => ({
      type: "paragraph",
      content: buildParagraphContent(paragraph, suggestions)
    }))
  };
}

const summaryLine = computed(() => {
  const wordCount = props.text.trim().split(/\s+/).filter(Boolean).length;
  return `${wordCount || 0} 词 / ${props.suggestions.length} 处重点问题`;
});

const editor = useEditor({
  editable: false,
  extensions: [Doc, Paragraph, Text, HardBreak, ErrorMark],
  content: buildDocContent(props.text, props.suggestions),
  editorProps: {
    attributes: {
      class: "essay-editor"
    }
  }
});

watch(
  () => [props.text, props.suggestions] as const,
  ([nextText, nextSuggestions]) => {
    editor.value?.commands.setContent(buildDocContent(nextText, nextSuggestions), {
      emitUpdate: false
    });
  },
  { deep: true }
);
</script>

<style scoped>
.essay-viewer {
  display: grid;
  gap: 18px;
  min-height: 0;
}

.essay-viewer__head {
  display: grid;
  gap: 8px;
}

.essay-viewer__eyebrow,
.essay-viewer__meta {
  margin: 0;
}

.essay-viewer__eyebrow {
  color: var(--muted-foreground);
  font-family: var(--font-secondary);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.essay-viewer__meta {
  color: var(--muted-foreground);
  font-size: 13px;
}

.essay-viewer__content,
.essay-viewer__empty {
  min-height: 420px;
  border-radius: 12px;
  box-shadow: var(--shadow-border);
  background: var(--card);
}

.essay-viewer__empty {
  display: grid;
  place-items: center;
  color: var(--muted-foreground);
  padding: 24px;
}

:deep(.essay-editor) {
  min-height: 420px;
  padding: 24px;
  color: var(--foreground);
  font-size: 15px;
  line-height: 1.9;
  white-space: normal;
}

:deep(.essay-editor p) {
  margin: 0 0 1.15rem;
}

:deep(.essay-editor p:last-child) {
  margin-bottom: 0;
}

:deep(.essay-editor .essay-error-mark) {
  padding: 0.05rem 0.18rem;
  border-radius: 4px;
  background: #fdf1f1;
  color: #b73d3d;
  box-shadow: inset 0 0 0 1px rgba(183, 61, 61, 0.12);
}

@media (min-width: 1100px) {
  .essay-viewer {
    grid-template-rows: auto minmax(0, 1fr);
    height: 100%;
  }

  .essay-viewer__content,
  .essay-viewer__empty {
    min-height: 0;
    height: 100%;
    overflow-y: auto;
  }

  :deep(.essay-editor) {
    min-height: 100%;
  }
}
</style>
