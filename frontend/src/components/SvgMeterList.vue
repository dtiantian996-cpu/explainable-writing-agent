<template>
  <div class="meter-list">
    <div v-for="item in normalizedItems" :key="item.label" class="meter-row">
      <div class="meter-row__text">
        <span>{{ item.label }}</span>
        <strong>{{ item.valueLabel }}</strong>
      </div>
      <svg class="meter-row__bar" viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden="true">
        <rect class="meter-row__track" x="0" y="3" width="100" height="4" rx="2" />
        <rect
          class="meter-row__fill"
          :class="`meter-row__fill--${item.tone}`"
          x="0"
          y="3"
          :width="item.width"
          height="4"
          rx="2"
        />
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

type Tone = "neutral" | "error" | "warning" | "success" | "info";

const props = defineProps<{
  items: Array<{
    label: string;
    value: number;
    valueLabel: string;
    tone?: Tone;
  }>;
}>();

const normalizedItems = computed(() => {
  const maxValue = Math.max(1, ...props.items.map((item) => item.value));

  return props.items.map((item) => ({
    ...item,
    tone: item.tone ?? "neutral",
    width: Math.max(10, Math.round((item.value / maxValue) * 100))
  }));
});
</script>

<style scoped>
.meter-list {
  display: grid;
  gap: 14px;
}

.meter-row {
  display: grid;
  gap: 8px;
}

.meter-row__text {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.meter-row__text span {
  color: var(--muted-foreground);
}

.meter-row__text strong {
  color: var(--foreground);
  font-size: 12px;
  font-weight: 600;
}

.meter-row__bar {
  width: 100%;
  height: 10px;
}

.meter-row__track {
  fill: #f3f3f3;
}

.meter-row__fill--neutral {
  fill: #171717;
}

.meter-row__fill--error {
  fill: #c84a4a;
}

.meter-row__fill--warning {
  fill: #8f4a00;
}

.meter-row__fill--success {
  fill: #1f8a4c;
}

.meter-row__fill--info {
  fill: #0a72ef;
}
</style>
