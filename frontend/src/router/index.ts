import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { pinia, useAuthStore } from "@/stores";
import DashboardPage from "@/pages/DashboardPage.vue";
import LoginPage from "@/pages/LoginPage.vue";
import RegisterPage from "@/pages/RegisterPage.vue";
import SubmitPage from "@/pages/SubmitPage.vue";
import ResultPage from "@/pages/ResultPage.vue";
import HistoryPage from "@/pages/HistoryPage.vue";
import NotebookPage from "@/pages/NotebookPage.vue";
import ProfilePage from "@/pages/ProfilePage.vue";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: LoginPage,
    meta: {
      publicOnly: true,
      appShell: false
    }
  },
  {
    path: "/register",
    name: "register",
    component: RegisterPage,
    meta: {
      publicOnly: true,
      appShell: false
    }
  },
  {
    path: "/",
    name: "dashboard",
    component: DashboardPage,
    meta: { requiresAuth: true }
  },
  {
    path: "/submit",
    name: "submit",
    component: SubmitPage,
    meta: { requiresAuth: true }
  },
  {
    path: "/result/:assessmentId",
    name: "result",
    component: ResultPage,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: "/history",
    name: "history",
    component: HistoryPage,
    meta: { requiresAuth: true }
  },
  {
    path: "/notebook",
    name: "notebook",
    component: NotebookPage,
    meta: { requiresAuth: true }
  },
  {
    path: "/profile",
    name: "profile",
    component: ProfilePage,
    meta: { requiresAuth: true }
  }
];

export const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia);
  await authStore.ensureSession();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    const redirect = to.fullPath && to.fullPath !== "/" ? to.fullPath : undefined;
    return {
      path: "/login",
      query: redirect ? { redirect } : undefined
    };
  }

  if (to.meta.publicOnly && authStore.isAuthenticated) {
    const redirect =
      typeof to.query.redirect === "string" && to.query.redirect.startsWith("/")
        ? to.query.redirect
        : "/";
    return redirect;
  }

  return true;
});
