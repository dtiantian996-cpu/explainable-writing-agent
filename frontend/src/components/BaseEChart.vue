<template>
  <div ref="containerRef" class="chart-canvas" :class="`chart-canvas--${size}`" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import type { ECharts, EChartsOption } from "echarts";

const props = withDefaults(
  defineProps<{
    option: EChartsOption;
    size?: "compact" | "panel" | "tall";
  }>(),
  {
    size: "panel"
  }
);

const containerRef = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;

function renderChart() {
  if (!containerRef.value) return;

  if (!chart) {
    chart = echarts.init(containerRef.value, undefined, {
      renderer: "svg"
    });
  }

  chart.setOption(props.option, true);
}

onMounted(() => {
  renderChart();

  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      chart?.resize();
    });
    resizeObserver.observe(containerRef.value);
  }
});

watch(
  () => props.option,
  () => {
    renderChart();
  },
  { deep: true }
);

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<style scoped>
.chart-canvas {
  width: 100%;
}

.chart-canvas--compact {
  height: 176px;
}

.chart-canvas--panel {
  height: 220px;
}

.chart-canvas--tall {
  height: 260px;
}
</style>
