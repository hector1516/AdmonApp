// Helper de API estilo Field (src/lib/api): fetch con Bearer token del store,
// base '/api', errores tipados y logout en 401. Usado por Legends.svelte.
import { auth } from './stores/auth.js';
import { navigate } from './router.js';

const BASE = '/api';

async function request(path, options = {}) {
	const headers = { ...(options.headers || {}) };
	const token = localStorage.getItem('admon_token');
	if (token) headers['Authorization'] = `Bearer ${token}`;
	if (!(options.body instanceof FormData)) {
		headers['Content-Type'] = 'application/json';
	} else {
		delete headers['Content-Type'];
	}
	const res = await fetch(`${BASE}${path}`, { ...options, headers });

	if (res.status === 401) {
		auth.logout();
		navigate('/login', { replace: true });
		throw new Error('Sesión expirada');
	}
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		let detail = err.detail || err.message || 'Error del servidor';
		// FastAPI 422 devuelve detail como array de objetos {loc, msg, type}
		if (Array.isArray(detail)) {
			detail = detail.map((d) => d?.msg || JSON.stringify(d)).join('; ');
		}
		throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
	}
	return res.json();
}

export const api = {
	get: (path) => request(path),
	post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
	put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
	delete: (path) => request(path, { method: 'DELETE' })
};
