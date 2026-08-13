const CACHE_NAME = "kao-rush-shell-v8";
const APP_SHELL = [
  "/static/css/styles.css",
  "/static/css/tokens.css",
  "/static/css/layout.css",
  "/static/css/components.css",
  "/static/css/pages.css",
  "/static/css/product.css",
  "/static/css/landing.css",
  "/static/js/app.js",
  "/static/js/pwa_shell.js",
  "/static/js/member_portal.js",
  "/static/js/meeting.js",
  "/static/js/mobile.js",
  "/static/js/demo.js",
  "/static/js/platform_admin.js",
  "/static/js/landing.js",
  "/static/manifest.webmanifest",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }
  const url = new URL(event.request.url);
  const pathSegments = url.pathname.split("/").filter(Boolean);
  if (pathSegments.includes("api")) {
    event.respondWith(fetch(event.request));
    return;
  }
  // Never persist authenticated HTML or tenant-prefixed API navigations.
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .catch(() => new Response("BidBoard is offline. Reconnect to continue.", {
          status: 503,
          headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" }
        }))
    );
    return;
  }

  // For static assets, use network-first with cache fallback.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(fetch(event.request));
});
