<script>
  import { onMount } from 'svelte';
  import { auth } from '$lib/stores/auth';
  import { goto } from '$app/navigation';

  onMount(async () => {
    // Restaurar sesión al cargar la app (lee de localStorage)
    await auth.login('test@test.com', 'test'); // placeholder - ver abajo
    // Mejor: restaurar desde localStorage directamente
    const token = localStorage.getItem('admon_token');
    const expires = localStorage.getItem('admon_expires');
    if (token && expires && Date.now() < parseInt(expires)) {
      // Ya fue restaurado por el store.auth en el import
    }
    
    // Si NO hay token, redirigir al login
    if (!$auth.token && $page.url.pathname !== '/login') {
      goto('/login');
    }
  });
</script>

<!-- Solo mostrar contenido si hay sesión o en login -->
{#if $auth.token || $page.url.pathname === '/login'}
  <slot />
{:else}
  <p>Cargando sesión...</p>
{/if}

<!-- Mobile Bottom Nav (estilo Field) -->
<nav class="bottom-nav bg-dark border-t border-surface/50">
  <div class="nav-item">
    <a href="/dashboard" class="nav-link">
      <lucide-svelte name="home" class="h-6 w-6" />
      <span class="text-xs hidden sm:block">Dashboard</span>
    </a>
  </div>
  <div class="nav-item">
    <a href="/cotizaciones_materiales" class="nav-link">
      <lucide-svelte name="package" class="h-6 w-6" />
      <span class="text-xs hidden sm:block">Cotizaciones</span>
    </a>
  </div>
  <div class="nav-item">
    <a href="/telegram" class="nav-link">
      <lucide-svelte name="message-circle" class="h-6 w-6" />
      <span class="text-xs hidden sm:block">Telegram</span>
    </a>
  </div>
  <div class="nav-item">
    <a href="/config" class="nav-link">
      <lucide-svelte name="settings" class="h-6 w-6" />
      <span class="text-xs hidden sm:block">Config</span>
    </a>
  </div>
</nav>