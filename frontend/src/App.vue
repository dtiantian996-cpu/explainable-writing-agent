<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-global-style />
    <router-view v-slot="{ Component }">
      <AppShell v-if="route.meta.appShell !== false">
        <component :is="Component" />
      </AppShell>
      <component :is="Component" v-else />
    </router-view>
  </n-config-provider>
</template>

<script setup lang="ts">
import { NConfigProvider, NGlobalStyle, type GlobalThemeOverrides } from "naive-ui";
import { useRoute } from "vue-router";
import AppShell from "@/app/AppShell.vue";

const route = useRoute();

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: "var(--primary)",
    primaryColorHover: "var(--foreground)",
    primaryColorPressed: "var(--foreground)",
    successColor: "var(--color-success-foreground)",
    warningColor: "var(--color-warning-foreground)",
    errorColor: "var(--color-error-foreground)",
    infoColor: "var(--color-info-foreground)"
  }
};
</script>
