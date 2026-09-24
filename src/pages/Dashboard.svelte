<script>
  import { onMount } from 'svelte';
  import { navigate } from 'svelte-routing';
  import { auth } from '$lib/stores/auth.js';

  let kpis = [];
  let userName = '';

  onMount(async () => {
    if (!auth.isLoggedIn()) {
      navigate('/login', { replace: true });
      return;
    }
    try {
      const raw = localStorage.getItem('admon_user');
      userName = raw ? (JSON.parse(raw).nombre || '') : '';
    } catch {
      userName = '';
    }
    try {
      const res = await fetch('/dashboard/kpis', { headers: auth.authHeader() });
      if (res.ok) {
        const data = await res.json();
        kpis = data.kpis || [];
      }
    } catch (e) {
      console.error('Error cargando KPIs:', e);
    }
  });
</script>

<div class="p-6 pb-24">
  <h1 class="text-3xl font-bold text-text mb-2">📊 Panel de Administración</h1>
  {#if userName}
    <p class="text-muted mb-6">Bienvenido, {userName}</p>
  {:else}
    <p class="text-muted mb-6">Bienvenido al panel de admon.</p>
  {/if}

  {#if kpis.length > 0}
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {#each kpis as kpi}
        <div class="surface p-4 rounded-lg">
          <p class="text-muted text-xs uppercase">{kpi.etiqueta}</p>
          <p class="text-2xl font-bold text-text">{kpi.valor}</p>
        </div>
      {/each}
    </div>
  {/if}

  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <div class="surface p-4 rounded-lg">
      <h3 class="font-semibold text-text mb-2">Sistema</h3>
      <p class="text-muted">Modo: Administrativo</p>
      <p class="text-accent font-medium">HUB v1.1.0</p>
    </div>

    <div class="surface p-4 rounded-lg">
      <h3 class="font-semibold text-text mb-2">Autenticación</h3>
      <p class="text-muted">JWT simple</p>
      <p class="text-accent font-medium">Sin passkeys</p>
    </div>
  </div>

  <div class="mt-6 pt-6 border-t border-surface">
    <h3 class="font-semibold text-text mb-4">Accesos Rápidos</h3>
    <div class="grid grid-cols-2 gap-2">
      <a href="/cotizaciones_materiales" class="block surface p-3 rounded">
        <span class="text-sm text-text">📦 Cotizaciones Materiales</span>
      </a>
      <a href="/telegram" class="block surface p-3 rounded">
        <span class="text-sm text-text">📱 Telegram</span>
      </a>
    </div>
  </div>
</div>
