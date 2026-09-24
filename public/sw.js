/* Admon Service Worker — espejo del de Field, alcance "/" servido por FastAPI.
 * REGLA DURA (lección Field): solo interceptar GET. Nunca responder POST/PUT
 * con FormData: el SW perdería el body y el backend recibiría size=0 (422).
 */
const CACHE = 'admon-v1.0.1';
const APP_SHELL = [
	'/',
	'/index.html',
	'/manifest.webmanifest',
	'/admon_logo.png',
	'/engrane.png',
	'/icons/icon-192x192.png',
	'/icons/icon-512x512.png'
];

// Prefijos que son API (network-only, jamás cachear: llevan auth y POSTs).
// La API vive bajo /api/*; la SPA es dueña de la raíz (sin colisiones).
const API_PREFIXES = ['/api', '/docs', '/openapi.json', '/redoc'];

self.addEventListener('install', (e) => {
	e.waitUntil(
		caches.open(CACHE).then((c) =>
			Promise.all(APP_SHELL.map((u) => c.add(u).catch(() => {})))
		).then(() => self.skipWaiting())
	);
});

self.addEventListener('activate', (e) => {
	e.waitUntil(
		caches.keys()
			.then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
			.then(() => self.clients.claim())
	);
});

self.addEventListener('message', (e) => {
	if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
	if (e.data && e.data.type === 'FORCE_RELOAD') {
		self.clients.matchAll({ type: 'window' }).then((clients) => {
			clients.forEach((c) => c.postMessage({ type: 'FORCE_RELOAD' }));
		});
	}
});

self.addEventListener('fetch', (e) => {
	const { request } = e;
	// Solo GET: el resto pasa directo a red (ver regla dura arriba)
	if (request.method !== 'GET') return;
	const url = new URL(request.url);
	if (url.origin !== self.location.origin) return;

	// API -> siempre red, sin cache
	if (API_PREFIXES.some((p) => url.pathname === p || url.pathname.startsWith(p + '/'))) {
		return;
	}

	// Navegaciones (rutas SPA) -> red primero, fallback al shell cacheado.
	// Solo se cachea el shell si la red respondió OK (un 403/404 no debe
	// quedar guardado como index.html para el modo offline).
	if (request.mode === 'navigate') {
		e.respondWith(
			fetch(request)
				.then((res) => {
					if (res && res.ok) {
						const copy = res.clone();
						caches.open(CACHE).then((c) => c.put('/index.html', copy)).catch(() => {});
					}
					return res;
				})
				.catch(() => caches.match('/index.html').then((r) => r || caches.match('/')))
		);
		return;
	}

	// Estáticos (assets, iconos, imágenes) -> cache primero, actualiza en fondo
	e.respondWith(
		caches.match(request).then((cached) => {
			const network = fetch(request).then((res) => {
				if (res && res.ok) {
					const copy = res.clone();
					caches.open(CACHE).then((c) => c.put(request, copy)).catch(() => {});
				}
				return res;
			}).catch(() => cached);
			return cached || network;
		})
	);
});
