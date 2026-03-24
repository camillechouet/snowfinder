// SnowFinder Service Worker
const CACHE_NAME = 'snowfinder-v2';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/recherche.html',
  '/logo.png',
  'https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap',
];

// Installation — mise en cache des ressources statiques
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activation — supprimer les anciens caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch — stratégie Network First (toujours essayer le réseau d'abord)
// Ainsi les mises à jour GitHub sont immédiates
self.addEventListener('fetch', event => {
  // Ignorer les requêtes non-HTTP (chrome-extension://, etc.)
  if(!event.request.url.startsWith('http')) return;

  // Ne pas intercepter les appels API météo
  if(event.request.url.includes('api.open-meteo.com') ||
     event.request.url.includes('openstreetmap.org') ||
     event.request.url.includes('googletagmanager') ||
     event.request.url.includes('analytics.google')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Mettre en cache la nouvelle version
        if(response && response.status === 200 && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        // Fallback sur le cache si hors ligne
        return caches.match(event.request).then(cached => {
          if(cached) return cached;
          // Page offline de secours
          if(event.request.destination === 'document') {
            return caches.match('/index.html');
          }
        });
      })
  );
});

// Message pour forcer la mise à jour
self.addEventListener('message', event => {
  if(event.data === 'skipWaiting') self.skipWaiting();
});
