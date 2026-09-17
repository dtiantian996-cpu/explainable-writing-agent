const CACHE_NAME = "yasi-app-shell-v2";
const CORE_URLS = [
  "/",
  "/index.html",
  "/offline-shell.html",
  "/fonts/geist/Geist-Variable.woff2",
  "/fonts/geist/GeistMono-Variable.woff2",
];

function toAbsoluteUrl(input) {
  return new URL(input, self.location.origin).toString();
}

async function openCache() {
  return caches.open(CACHE_NAME);
}

async function precacheUrls(urls) {
  const cache = await openCache();
  const normalized = [...new Set(urls.map(toAbsoluteUrl))];
  await Promise.allSettled(
    normalized.map(async (url) => {
      const request = new Request(url, { credentials: "same-origin" });
      const response = await fetch(request);
      if (response.ok) {
        await cache.put(request, response.clone());
      }
    }),
  );
}

function isSameOriginGet(request) {
  return request.method === "GET" && new URL(request.url).origin === self.location.origin;
}

function isStaticAssetRequest(request) {
  if (!isSameOriginGet(request)) return false;
  const url = new URL(request.url);
  if (url.pathname.startsWith("/api/")) return false;
  return ["script", "style", "font", "image"].includes(request.destination);
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      await precacheUrls(CORE_URLS);
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const cacheKeys = await caches.keys();
      await Promise.all(
        cacheKeys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key)),
      );
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("message", (event) => {
  const payload = event.data;
  if (!payload || payload.type !== "PRECACHE_URLS" || !Array.isArray(payload.urls)) return;
  event.waitUntil(
    (async () => {
      await precacheUrls([...CORE_URLS, ...payload.urls]);
      event.source?.postMessage({ type: "PRECACHE_COMPLETE" });
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (!isSameOriginGet(request)) return;

  const url = new URL(request.url);
  if (url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      (async () => {
        const cache = await openCache();
        try {
          const response = await fetch(request);
          if (response.ok) {
            await cache.put(request, response.clone());
            await cache.put(new Request("/index.html"), response.clone());
          }
          return response;
        } catch {
          return (
            (await cache.match(request)) ||
            (await cache.match("/offline-shell.html")) ||
            (await cache.match("/index.html")) ||
            (await cache.match("/"))
          );
        }
      })(),
    );
    return;
  }

  if (!isStaticAssetRequest(request)) return;

  event.respondWith(
    (async () => {
      const cache = await openCache();
      const cached = await cache.match(request);
      if (cached) {
        event.waitUntil(
          (async () => {
            try {
              const fresh = await fetch(request);
              if (fresh.ok) {
                await cache.put(request, fresh.clone());
              }
            } catch {
              // 离线刷新时静默保留缓存壳层
            }
          })(),
        );
        return cached;
      }

      const response = await fetch(request);
      if (response.ok) {
        await cache.put(request, response.clone());
      }
      return response;
    })(),
  );
});
