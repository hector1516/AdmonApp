<script>
  import { auth } from '$lib/stores/auth';
  import { onMount } from 'svelte';
  
  let nuevoTitulo = '';
  let nuevoContacto = '';
  let error = '';
  let success = false;
  let loading = false;
  let cotizaciones = []; // lista vacía por ahora - se cargará del API
  
  onMount(async () => {
    // Cargar índice de cotizaciones desde API
    try {
      const res = await fetch('/api/cotizaciones_materiales/index', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('admon_token')}` }
      });
      if (res.ok) {
        cotizaciones = await res.json();
      }
    } catch (e) {
      console.error('Error cargando cotizaciones:', e);
    }
  });
</script>

<div class="min-h-screen bg-dark">
  <!-- Header -->
  <header class="border-b border-surface/50 backdrop-blur">
    <div class="max-w-7xl mx-auto px-6 py-4">
      <h1 class="text-2xl font-bold text-text">📦 Cotizaciones de Materiales</h1>
      <p class="text-muted text-sm">Modo: Solo Lectura + Creación</p>
    </div>
  </header>

  <main class="max-w-7xl mx-auto p-6">
    <!-- Estadísticas / Métricas -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div class="surface p-4 rounded-lg">
        <p class="text-muted text-xs uppercase">Total Cotizaciones</p>
        <p class="text-2xl font-bold text-text">{#each cotizaciones as c} {/each}</p>
      </div>
      <div class="surface p-4 rounded-lg">
        <p class="text-muted text-xs uppercase">Esta Semana</p>
        <p class="text-2xl font-bold text-text">0</p>
      </div>
      <div class="surface p-4 rounded-lg">
        <p class="text-muted text-xs uppercase">Total Partidas</p>
        <p class="text-2xl font-bold text-text">0</p>
      </div>
      <div class="surface p-4 rounded-lg">
        <p class="text-muted text-xs uppercase">Sincronizado</p>
        <p class="text-2xl font-bold text-text">✅ Al día</p>
      </div>
    </div>

    <!-- Tabla de Cotizaciones -->
    <section class="surface p-6 rounded-lg">
      <h2 class="text-xl font-bold text-text mb-4">Índice de Cotizaciones</h2>
      
      {#if cotizaciones.length === 0}
        <p class="text-muted text-center py-8">No hay cotizaciones registradas.</p>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full bg-white rounded-lg overflow-hidden">
            <thead class="bg-dark">
              <tr>
                <th class="text-left p-3 text-sm text-text">Folio</th>
                <th class="text-left p-3 text-sm text-text">Cliente</th>
                <th class="text-left p-3 text-sm text-text">Contacto</th>
                <th class="text-left p-3 text-sm text-text">Fecha</th>
                <th class="text-left p-3 text-sm text-text">Autor</th>
                <th class="text-right p-3 text-sm text-text">Total</th>
                <th class="text-right p-3 text-sm text-text"></th>
              </tr>
            </thead>
            <tbody>
              {#each cotizaciones as cot (index)}
              <tr class="border-b border-surface/10 cursor-pointer hover:bg-surface/50 transition-colors" 
                  onclick="window.location='/cotizaciones_materiales/{cot.folio}'">
                <td class="p-3 text-sm font-medium">{cot.folio}</td>
                <td class="p-3 text-sm text-muted">{cot.cliente || 'N/A'}</td>
                <td class="p-3 text-sm text-muted">{cot.contacto || 'N/A'}</td>
                <td class="p-3 text-sm">{cot.fecha}</td>
                <td class="p-3 text-sm text-muted">{cot.autor}</td>
                <td class="p-3 text-right text-accent font-medium">$0.00</td>
                <td class="p-3 text-right">
                  <lucide-svelte name="eye" class="h-4 w-4 text-muted" />
                </td>
              </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>

    <!-- Nueva Cotización -->
    <section class="surface p-6 rounded-lg mt-6">
      <h2 class="text-xl font-bold text-text mb-4">📝 Nueva Cotización</h2>
      
      <form class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm text-muted mb-2">Id Cliente</label>
          <input 
            type="text" 
            placeholder="CLI001" 
            value={nuevoTitulo}
            on:input={(e) => nuevoTitulo = e.target.value}
            class="w-full bg-none border border-surface/50 rounded px-3 py-2 text-text focus:outline-none focus:border-primary"
            disabled  {/* Deshabilitado por ahora - modo lectura */}
          />
        </div>
        
        <div>
          <label class="block text-sm text-muted mb-2">Contacto</label>
          <input 
            type="text" 
            placeholder="Nombre Contacto" 
            value={nuevoContacto}
            on:input={(e) => nuevoContacto = e.target.value}
            class="w-full bg-none border surface/50 rounded px-3 py-2 text-text focus:outline-none focus:border-primary"
            disabled
          />
        </div>
        
        <div class="col-span-2">
          <label class="block text-sm text-muted mb-2">Descripción</label>
          <textarea 
            rows="2" 
            placeholder="Descripción de la cotización" 
            disabled
            class="w-full bg-none border surface/50 rounded px-3 py-2 text-text focus:outline-none focus:border-primary resize-none"
          ></textarea>
        </div>
      </form>
      
      <div class="mt-4">
        <button 
          disabled  {/* Por ahora modo solo lectura */}
          class="bg-primary text-white py-2 rounded font-medium hover:bg-secondary/90 transition-colors w-full"
        >
          ⚠️ Modo Solo Lectura - Creación en desarrollo
        </button>
      </div>
    </section>
  </main>
</div>