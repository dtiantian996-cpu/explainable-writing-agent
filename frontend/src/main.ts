import { createApp } from "vue";
import { createDiscreteApi } from "naive-ui";
import App from "./App.vue";
import { router } from "./router";
import { setupStore } from "./stores";
import "./styles/tokens.css";
import "./styles/global.css";

declare global {
  interface Window {
    __YASI_SW_READY__?: boolean;
  }
}

const app = createApp(App);
app.use(setupStore());
app.use(router);
app.mount("#app");

export const { message, notification, dialog, loadingBar } = createDiscreteApi([
  "message",
  "notification",
  "dialog",
  "loadingBar"
]);

function markServiceWorkerReady() {
  window.__YASI_SW_READY__ = true;
  document.documentElement.dataset.yasiSwReady = "true";
}

function waitForServiceWorkerController(): Promise<void> {
  if (navigator.serviceWorker.controller) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const onControllerChange = () => {
      if (!navigator.serviceWorker.controller) return;
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
      resolve();
    };

    navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);
  });
}

function waitForPrecacheComplete(): Promise<void> {
  return new Promise((resolve) => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.type !== "PRECACHE_COMPLETE") return;
      navigator.serviceWorker.removeEventListener("message", onMessage);
      resolve();
    };

    navigator.serviceWorker.addEventListener("message", onMessage);
  });
}

function collectPrecacheUrls(): string[] {
  const urls = new Set<string>([
    "/",
    "/index.html",
    `${window.location.pathname}${window.location.search}`,
    "/fonts/geist/Geist-Variable.woff2",
    "/fonts/geist/GeistMono-Variable.woff2"
  ]);

  for (const entry of performance.getEntriesByType("resource")) {
    if (!(entry instanceof PerformanceResourceTiming)) continue;
    const resourceUrl = new URL(entry.name, window.location.href);
    if (resourceUrl.origin !== window.location.origin) continue;
    if (resourceUrl.pathname.startsWith("/api/")) continue;
    urls.add(`${resourceUrl.pathname}${resourceUrl.search}`);
  }

  return [...urls];
}

async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;

  try {
    const registration = await navigator.serviceWorker.register("/sw.js");
    const readyRegistration = await navigator.serviceWorker.ready;
    const precacheDone = waitForPrecacheComplete();

    const activeWorker =
      readyRegistration.active ??
      readyRegistration.waiting ??
      readyRegistration.installing ??
      registration.active ??
      registration.waiting ??
      registration.installing;

    activeWorker?.postMessage({
      type: "PRECACHE_URLS",
      urls: collectPrecacheUrls()
    });

    await Promise.all([waitForServiceWorkerController(), precacheDone]);
    markServiceWorkerReady();
  } catch (error) {
    console.warn("YASI service worker registration failed", error);
  }
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void registerServiceWorker();
  });
}
