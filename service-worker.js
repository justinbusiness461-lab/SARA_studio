/* SongForge PWA — 2.20.0 M043 candidate */
const CACHE_NAME = 'sara-studio-sanitized-offline-v2';
const ASSETS = [
  './platform-ui.js',
  './studio-shell.css',
  './app-core.js',
  './scorecore.js',
  './app-ui.js',
  './app-cinema.js',
  './manifest.json',
  './icons/icon.svg',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

// A locally compiled ScoreCore remains available offline, but never a
// session/capability-bearing entry page. Authenticated platform mode does
// not register this worker and is never cached as an offline login shell.
self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(ASSETS.map(url => new Request(url, { cache: 'reload' })));
    const response = await fetch(new Request('./index.html', { cache: 'reload' }));
    if (!response.ok) throw new Error('OFFLINE_SHELL_SOURCE_UNAVAILABLE');
    const source = await response.text();
    if (!source.includes('window.__SARA_PLATFORM_MODE__=true')) {
      const safe = source.replace(
        /<script>window\.__STUDIO_CAPABILITY__=.*?window\.__STUDIO_SESSION__=.*?<\/script>/s,
        '<script>window.__SARA_OFFLINE_SHELL__=true;</script>'
      );
      if (safe === source || safe.includes('window.__STUDIO_SESSION__') ||
          safe.includes('window.__STUDIO_CAPABILITY__')) {
        throw new Error('UNSAFE_OFFLINE_SHELL_BOOTSTRAP');
      }
      await cache.put('./index.html', new Response(safe, {
        status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' }
      }));
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET' || new URL(e.request.url).pathname.startsWith('/api/')) return;
  if (e.request.mode === 'navigate') {
    // Online navigations always fetch fresh session state. Offline only a
    // credential-free local ScoreCore shell can load; no authenticated page.
    e.respondWith(fetch(e.request).catch(async () =>
      (await caches.match('./index.html')) || Response.error()
    )); return;
  }
  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request).then((res) => {
        if (!res || res.status !== 200 || res.type !== 'basic') return res;
        const clone = res.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        return res;
      });
    })
  );
});