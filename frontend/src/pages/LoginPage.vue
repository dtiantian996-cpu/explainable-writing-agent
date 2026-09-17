<template>
  <main class="auth-page">
    <section class="auth-stage">
      <aside class="auth-aside">
        <p class="page-eyebrow">Login</p>
        <h1 class="auth-title">先登录，再进入你的写作工作台。</h1>
        <p class="auth-copy">
          登录页不需要做成另一套产品。它只负责把你送回 YASI 的工作台，把评估、历史、错题本和画像收在同一条链里。
        </p>
        <div class="auth-note-list">
          <article class="surface-muted auth-note">
            <p class="card-kicker">Workspace</p>
            <h2 class="section-title">登录后直接进入提交、结果、历史和复盘闭环。</h2>
          </article>
          <article class="surface-muted auth-note">
            <p class="card-kicker">Boundary</p>
            <h2 class="section-title">只做本地最小认证，不做邮箱验证、找回密码和复杂权限。</h2>
          </article>
        </div>
      </aside>

      <section class="surface-card auth-card">
        <div class="auth-card__head">
          <p class="card-kicker">YASI Account</p>
          <h2 class="section-title">登录</h2>
          <p class="card-copy">输入邮箱和密码，继续你的 IELTS 写作训练。</p>
        </div>

        <form class="auth-form" @submit.prevent="void onSubmit()">
          <label class="field-stack" for="login-email">
            <span class="field-label">邮箱</span>
            <input
              id="login-email"
              v-model.trim="form.email"
              name="email"
              class="input-shell"
              type="email"
              autocomplete="email"
              placeholder="you@example.com"
            />
          </label>

          <label class="field-stack" for="login-password">
            <span class="field-label">密码</span>
            <input
              id="login-password"
              v-model="form.password"
              name="password"
              class="input-shell"
              type="password"
              autocomplete="current-password"
              placeholder="至少 8 位"
            />
          </label>

          <p v-if="inlineError" class="feedback-text feedback-text--error">{{ inlineError }}</p>
          <p v-else-if="authStore.errorMessage" class="feedback-text feedback-text--error">{{ authStore.errorMessage }}</p>

          <button class="button-primary auth-submit" type="submit" :disabled="!canSubmit || authStore.submitting">
            {{ authStore.submitting ? "正在登录..." : "登录并进入工作台" }}
          </button>
        </form>

        <div class="auth-card__footer">
          <p class="card-copy">还没有账号？</p>
          <RouterLink class="auth-link" :to="registerLink">创建新账号</RouterLink>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
authStore.clearError();
const form = reactive({
  email: "",
  password: ""
});

const redirectTarget = computed(() => {
  const redirect = route.query.redirect;
  return typeof redirect === "string" && redirect.startsWith("/") ? redirect : "/";
});
const registerLink = computed(() => ({
  path: "/register",
  query: redirectTarget.value === "/" ? undefined : { redirect: redirectTarget.value }
}));
const inlineError = computed(() => {
  if (!form.email || !form.password) return "";
  if (form.password.length < 8) return "密码至少需要 8 位";
  return "";
});
const canSubmit = computed(() => !!form.email && !!form.password && !inlineError.value);

async function onSubmit() {
  if (!canSubmit.value) return;
  const success = await authStore.login({
    email: form.email,
    password: form.password
  });
  if (!success) return;
  await router.replace(redirectTarget.value);
}
</script>
