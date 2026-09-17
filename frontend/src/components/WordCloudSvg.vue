<template>
  <svg class="word-cloud" viewBox="0 0 360 220" role="img" aria-label="关键词云">
    <text
      v-for="item in positionedItems"
      :key="item.word"
      :x="item.x"
      :y="item.y"
      :font-size="item.fontSize"
      :class="`word-cloud__word word-cloud__word--${item.tone}`"
    >
      {{ item.word }}
    </text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  items: Array<{
    word?: string;
    text?: string;
    weight: number;
  }>;
}>();

const anchorPoints = [
  { x: 44, y: 58, tone: "neutral" },
  { x: 184, y: 52, tone: "info" },
  { x: 96, y: 112, tone: "warning" },
  { x: 220, y: 106, tone: "neutral" },
  { x: 56, y: 170, tone: "success" },
  { x: 214, y: 164, tone: "error" },
  { x: 132, y: 204, tone: "neutral" }
] as const;

const positionedItems = computed(() => {
  const sorted = [...props.items]
    .map((item) => ({
      ...item,
      word: item.word ?? item.text ?? ""
    }))
    .filter((item) => item.word)
    .sort((left, right) => right.weight - left.weight)
    .slice(0, anchorPoints.length);
  const maxWeight = Math.max(1, ...sorted.map((item) => item.weight));

  return sorted.map((item, index) => {
    const anchor = anchorPoints[index];
    return {
      ...item,
      ...anchor,
      fontSize: 15 + Math.round((item.weight / maxWeight) * 18)
    };
  });
});
</script>

<style scoped>
.word-cloud {
  width: 100%;
  height: 220px;
  display: block;
}

.word-cloud__word {
  font-family: var(--font-secondary);
  font-weight: 500;
}

.word-cloud__word--neutral {
  fill: #171717;
}

.word-cloud__word--info {
  fill: #0a72ef;
}

.word-cloud__word--warning {
  fill: #8f4a00;
}

.word-cloud__word--success {
  fill: #1f8a4c;
}

.word-cloud__word--error {
  fill: #c84a4a;
}
</style>
