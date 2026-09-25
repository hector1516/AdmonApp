import { writable } from 'svelte/store';

// Store de autenticación JWT simple.
// - Guarda token + usuario en localStorage (7 días, como Field)
// - Passkeys (WebAuthn): login con huella/Face ID vía lib/passkey.js → saveSession
// - El backend valida el token contra HUB_Users en cada request
function createAuthStore() {
  const { subscribe, set } = writable({
    token: null,
    user: null,
    expiresAt: null
  });

  function getToken() {
    return localStorage.getItem('admon_token');
  }

  function isLoggedIn() {
    const token = localStorage.getItem('admon_token');
    const expires = localStorage.getItem('admon_expires');
    return !!(token && expires && Date.now() < parseInt(expires, 10));
  }

  // Restaurar sesión al arrancar la app (llamar en onMount del App)
  function init() {
    const storedToken = localStorage.getItem('admon_token');
    const storedExpires = localStorage.getItem('admon_expires');
    const storedUser = localStorage.getItem('admon_user');
    if (storedToken && storedExpires && Date.now() < parseInt(storedExpires, 10)) {
      let user = null;
      try {
        user = storedUser ? JSON.parse(storedUser) : null;
      } catch {
        user = null;
      }
      set({ token: storedToken, user, expiresAt: parseInt(storedExpires, 10) });
    } else {
      logout();
    }
  }

  // Guarda la sesión devuelta por el backend: { token, user, expiresAt }.
  // La usan el login por contraseña y el login/registro por passkey.
  function saveSession(data) {
    localStorage.setItem('admon_token', data.token);
    localStorage.setItem('admon_expires', String(data.expiresAt));
    localStorage.setItem('admon_user', JSON.stringify(data.user));
    set({ token: data.token, user: data.user, expiresAt: data.expiresAt });
  }

  // Login contra POST /api/auth/login -> { token, user, expiresAt }
  async function login(email, password) {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      let msg = 'Credenciales incorrectas';
      try {
        const err = await res.json();
        msg = err.detail || msg;
      } catch {
        /* mantener mensaje por defecto */
      }
      throw new Error(msg);
    }
    const data = await res.json();
    saveSession(data);
  }

  function logout() {
    localStorage.removeItem('admon_token');
    localStorage.removeItem('admon_expires');
    localStorage.removeItem('admon_user');
    set({ token: null, user: null, expiresAt: null });
  }

  function authHeader() {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  return { subscribe, init, login, logout, getToken, isLoggedIn, authHeader, saveSession };
}

export const auth = createAuthStore();
