import { writable } from 'svelte/store';
import db from './db/admonDb.js';

// Caché offline genérica de lecturas (IndexedDB, tabla offlineCache).
// - La alimenta api.get (red -> guarda) y el prefetch de arranque
//   (src/lib/offlinePrefetch.js) que precarga los últimos 10 registros
//   de cada módulo con sus detalles.
// - Al servir desde caché se marca el store `servingFromCache` para que la
//   UI pueda avisar "datos guardados" (el banner de offline ya existe en
//   SyncHeader cuando no hay red).

// Error tipado de RED: api.js lo lanza cuando fetch falla a nivel de
// conexión (offline, DNS, cortes). Los errores HTTP/dominio (404, 403…)
// NO lo usan, para que el fallback a caché solo ocurra ante falta real
// de conexión y no enlace errores del servidor con datos viejos.
export class NetworkError extends Error {
	constructor(msg = 'Sin conexión') {
		super(msg);
		this.code = 'NETWORK';
	}
}

export function isNetworkError(e) {
	return !!(e && e.code === 'NETWORK');
}

// True cuando la última lectura GET se sirvió desde la caché local.
export const servingFromCache = writable(false);

// Normaliza la llave: `/api/reportes?` (URLSearchParams vacío) y
// `/api/reportes` deben colisionar en la misma entrada.
function norm(key) {
	return String(key || '').replace(/\?$/, '');
}

export async function cachePut(key, data) {
	try {
		await db.offlineCache.put({ key: norm(key), data, ts: Date.now() });
	} catch {
		// IndexedDB lleno o bloqueado: la app sigue funcionando online.
	}
}

export async function cacheGet(key) {
	try {
		const row = await db.offlineCache.get(norm(key));
		return row ? row.data : null;
	} catch {
		return null;
	}
}

// Poda defensiva: entradas con más de `days` días se eliminan al arrancar.
export async function pruneOldEntries(days = 60) {
	try {
		const cut = Date.now() - days * 24 * 3600 * 1000;
		await db.offlineCache.where('ts').below(cut).delete();
	} catch {}
}
