<script>
  import { onMount } from 'svelte';
  import { navigate } from 'svelte-routing';
  import { auth } from '$lib/stores/auth.js';

  let cotizaciones = [];
  let loading = true;
  let error = '';

  onMount(async () => {
    if (!auth.isLoggedIn()) {
      navigate('/login', { replace: true });
      return;
    }
    try {
      const res = await fetch('/cotizaciones/materiales', { headers: auth.authHeader() });
      if (res.ok) {
        cotizaciones = await res.json();
      } else if (res.status === 401 || res.status === 403) {
        auth.logout();
        navigate('/login', { replace: true });
      } else {
        error = `Error del servidor (${res.status})`;
      }
    } catch (e) {
      console.error('Error cargando cotizaciones:', e);
      error = 'No se pudo conectar con el servidor.';
    } finally {
      loading = false;
    }
  });
</script>

<div class="min-h-screen bg-dark pb-24">
  <header class="border-b border-surface">
    <div class="max-w-7xl mx-auto px-6 py-4">
      <h1 class="text-2xl font-bold text-text">📦 Cotizaciones de Materiales</h1>
      <p class="text-muted text-sm">Índice desde la API</p>
    </div>
  </header>

  <main class="max-w-7xl mx-auto p-6">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div class="surface p-4 rounded-lg">
        <p class="text-muted text-xs uppercase">Total Cotizaciones</p>
        <p class="text-2xl font-bold text-text">{cotizaciones.length}</p>
      </div>
      <div class="surface p-4 rounded-lg">
        <p class="text-muted text-xs uppercase">Sincronizado</p>
        <p class="text-2xl font-bold text-text">✅ Al día</p>
      </div>
    </div>

    <section class="surface p-6 rounded-lg">
      <h2 class="text-xl font-bold text-text mb-4">Índice de Cotizaciones</h2>

      {#if loading}
        <p class="text-muted text-center py-8">Cargando…</p>
      {:else if error}
        <p class="text-center py-8 text-red-400">{error}</p>
      {:else if cotizaciones.length === 0}
        <p class="text-muted text-center py-8">No hay cotizaciones registradas.</p>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full rounded-lg overflow-hidden">
            <thead class="bg-dark">
              <tr>
                <th class="text-left p-3 text-sm text-text">Folio</th>
                <th class="text-left p-3 text-sm text-text">Cliente</th>
                <th class="text-left p-3 text-sm text-text">Contacto</th>
                <th class="text-left p-3 text-sm text-text">Estatus</th>
                <th class="text-right p-3 text-sm text-text">Total</th>
              </tr>
            </thead>
            <tbody>
              {#each cotizaciones as cot (cot.folio)}
                <tr class="border-b border-surface">
                  <td class="p-3 text-sm font-medium">{cot.folio}</td>
                  <td class="p-3 text-sm text-muted">{cot.id_cliente || 'N/A'}</td>
                  <td class="p-3 text-sm text-muted">{cot.contacto || 'N/A'}</td>
                  <td class="p-3 text-sm">{cot.estatus}</td>
                  <td class="p-3 text-right text-accent font-medium">
                    ${Number(cot.total || 0).toFixed(2)}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>
  </main>
</div>
