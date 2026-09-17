<template>
  <main class="auth-page">
    <section class="auth-stage">
      <aside class="auth-aside">
        <p class="page-eyebrow">Register</p>
        <h1 class="auth-title">先建一个最小账号，再把训练数据收回到你自己名下。</h1>
        <p class="auth-copy">
          注册页只负责建立本地账号和会话，不把你带进额外的身份系统。重点仍然是后面的写作工作台和评估闭环。
        </p>
        <div class="auth-note-list">
          <article class="surface-muted auth-note">
            <p class="card-kicker">Data Ownership</p>
            <h2 class="section-title">assessment、history、notebook 和 profile 都按当前登录用户隔离。</h2>
          </article>
          <article class="surface-muted auth-note">
            <p class="card-kicker">Fast Path</p>
            <h2 class="section-title">注册成功后直接登录，不插入确认邮件或二次验证。</h2>
          </article>
        </div>
      </aside>

      <section class="surface-card auth-card">
        <div class="auth-card__head">
          <p class="card-kicker">YASI Account</p>
          <h2 class="section-title">注册</h2>
          <p class="card-copy">创建一个本地账号，后面的评估记录会全部落到这个账号下面。</p>
        </div>

        <form class="auth-form" @submit.prevent="void onSubmit()">
          <label class="field-stack" for="register-display-name">
            <span class="field-label">昵称</span>
            <input
              id="register-display-name"
              v-model.trim="form.displayName"
              name="displayName"
              class="input-shell"
              type="text"
              autocomplete="nickname"
              placeholder="例如 Lu Hui"
            />
          </label>

          <label class="field-stack" for="register-email">
            <span class="field-label">邮箱</span>
            <input
              id="register-email"
              v-model.trim="form.email"
              name="email"
              class="input-shell"
              type="email"
              autocomplete="email"
              placeholder="you@example.com"
            />
          </label>

          <label class="field-stack" for="register-password">
            <span class="field-label">密码</span>
            <input
              id="register-password"
              v-model="form.password"
              name="password"
              class="input-shell"
              type="password"
              autocomplete="new-password"
              placeholder="至少 8 位"
            />
          </label>

          <label class="field-stack" for="register-password-confirm">
            <span class="field-label">确认密码</span>
            <input
              id="register-password-confirm"
              v-model="confirmPassword"
              name="confirmPassword"
              class="input-shell"
              type="password"
              autocomplete="new-password"
              placeholder="再次输入密码"
            />
          </label>

          <p v-if="inlineError" class="feedback-text feedback-text--error">{{ inlineError }}</p>
          <p v-else-if="authStore.errorMessage" class="feedback-text feedback-text--error">{{ authStore.errorMessage }}</p>

          <button class="button-primary auth-submit" type="submit" :disabled="!canSubmit || authStore.submitting">
            {{ authStore.submitting ? "正在创建账号..." : "注册并进入工作台" }}
          </button>
        </form>

        <div class="auth-card__footer">
          <p class="card-copy">已经有账号？</p>
          <RouterLink class="auth-link" :to="loginLink">返回登录</RouterLink>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
authStore.clearError();
const confirmPassword = ref("");
const form = reactive({
  displayName: "",
  email: "",
  password: ""
});

const redirectTarget = computed(() => {
  const redirect = route.query.redirect;
  return typeof redirect === "string" && redirect.startsWith("/") ? redirect : "/";
});
const loginLink = computed(() => ({
  path: "/login",
  query: redirectTarget.value === "/" ? undefined : { redirect: redirectTarget.value }
}));
const inlineError = computed(() => {
  if (!form.displayName || !form.email || !form.password || !confirmPassword.value) return "";
  if (form.password.length < 8) return "密码至少需要 8 位";
  if (form.password !== confirmPassword.value) return "两次输入的密码不一致";
  return "";
});
const canSubmit = computed(
  () =>
    !!form.displayName &&
    !!form.email &&
    !!form.password &&
    !!confirmPassword.value &&
    !inlineError.value
);

async function onSubmit() {
  if (!canSubmit.value) return;
  const success = await authStore.register({
    displayName: form.displayName,
    email: form.email,
    password: form.password
  });
  if (!success) return;
  await router.replace(redirectTarget.value);
}
</script>
