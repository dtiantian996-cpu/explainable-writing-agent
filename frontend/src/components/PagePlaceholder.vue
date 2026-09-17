<template>
  <main class="page-shell">
    <section class="page-hero">
      <p class="page-kicker">{{ routePath }}</p>
      <h1 class="page-title">{{ title }}</h1>
      <p class="page-description">{{ description }}</p>
    </section>
    <section class="page-content">
      <div class="placeholder-block">
        <h2>页面占位</h2>
        <p>该页面用于后续按 Pencil 原型落地视觉与业务模块。</p>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
defineProps<{
  routePath: string;
  title: string;
  description: string;
}>();
</script>
