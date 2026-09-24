import { writable } from 'svelte/store';

interface AuthState {
  token: string | null;
  user: { id: number; nombre: string; email: string } | null;
  expiresAt: number | null; // timestamp en ms
}

/**
 * Store de autenticación JWT simple.
 * - Guarda token + usuario en localStorage
 * - No usa WebAuthn/passkeys (más simple y compatible)
 * - Token expira en 7 días (como Field)
 */
function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>({
    token: null,
    user: null,
    expiresAt: null
  });

  // Restaurar al cargar (lee de localStorage)
  // Ejecutar después de que el DOM esté listo
  function init() {
    const storedToken = localStorage.getItem('admon_token');
    const storedExpires = localStorage.getItem('admon_expires');
    const storedUser = localStorage.getItem('admon_user');

    if (storedToken && storedExpires && Date.now() < parseInt(storedExpires)) {
      set({
        token: storedToken,
        user: JSON.parse(storedUser),
        expiresAt: parseInt(storedExpires)
      });
    } else {
      // Limpiar datos inválidos/expired
      logout();
    }
  }

  return {
    subscribe,

    /**
     * Iniciar sesión con email y contraseña.
     * Llama al API FastPOST /api/auth/login
     */
    async login(email: string, password: string) {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || 'Credenciales incorrectas');
      }

      const data = await res.json(); // { token, user, expiresAt }
      
      // Guardar en localStorage para persistencia
      localStorage.setItem('admon_token', data.token);
      localStorage.setItem('admon_expires', String(data.expiresAt));
      localStorage.setItem('admon_user', JSON.stringify(data.user));

      set({
        token: data.token,
        user: data.user,
        expiresAt: data.expiresAt
      });
    },

    /**
     * Cerrar sesión.
     * Limpia localStorage y el store.
     */
    logout() {
      localStorage.removeItem('admon_token');
      localStorage.removeItem('admon_expires');
      localStorage.removeItem('admon_user');
      set({ token: null, user: null, expiresAt: null });
    },

    /**
     * Verificar si el usuario tiene un permiso específico.
     * Los permisos vienen en el JWT payload o en la BD.
     */
    hasPermission(permiso: string): boolean {
      // Por defecto, si hay token, el usuario está logueado
      // La verificación real se hace en los endpoints API
      return !!this.token;
    },

    /**
     * Obtener el token actual (útil para los headers).
     */
    get token(): string | null {
      return this.token; // compatibilidad - usará el value getter
    }
  };
}

// Inicializar automáticamente cuando se importe
 // Solo si el DOM ya está listo (onMount equivalent en Svelte 5)
 // En Svelte 5 stores se initilan cuando se subscriben, así que el desarrollador
 // debe llamar auth.init() en el onMount del layout principal.

export const auth = createAuthStore();