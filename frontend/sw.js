/**
 * HerGlory — Service Worker
 *
 * Minimal, deliberately simple cache strategy:
 *  - App shell (HTML/CSS/JS/icons/logo) is pre-cached on install
 *    so the PWA loads instantly and works offline.
 *  - Anything else (future API calls to FastAPI, uploaded media,
 *    etc.) goes straight to the network — NEVER cached here, so
 *    you won't fight stale data once the backend is wired up.
 *
 * Bump CACHE_VERSION whenever app.js / style.css / index.html change
 * so returning users get the fresh files instead of the old cache.
 */

const CACHE_VERSION = 'herglory-v1';

const APP_SHELL = [
  '/',
  '/static/style.css',
  '/static/app.js',
  '/static/manifest.json',
  '/static/assets/logo.webp',
  '/static/assets/icon-192.png',
  '/static/assets/icon-512.png',
];

// ---- Install: pre-cache the app shell ----
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

// ---- Activate: clean up old cache versions ----
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_VERSION)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// ---- Fetch: cache-first for app shell, network-first for everything else ----
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Only handle GET requests — let POST/PUT (future API calls) pass through untouched
  if (request.method !== 'GET') return;

  // Only handle same-origin requests (skip fonts CDN, external APIs, etc.)
  if (!request.url.startsWith(self.location.origin)) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).catch(() => {
        // Offline fallback for navigations — serve the app shell
        if (request.mode === 'navigate') {
          return caches.match('./index.html');
        }
      });
    })
  );
});
