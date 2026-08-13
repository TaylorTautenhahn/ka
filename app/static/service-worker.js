const CACHE_NAME = "bidboard-offline-v9";

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || event.request.mode !== "navigate") {
    return;
  }
  // Authenticated HTML remains network-only. Static files and APIs bypass the
  // worker entirely so the browser can use normal HTTP caching without overhead.
  event.respondWith(
    fetch(event.request)
      .catch(() => new Response("BidBoard is offline. Reconnect to continue.", {
        status: 503,
        headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" }
      }))
  );
});
