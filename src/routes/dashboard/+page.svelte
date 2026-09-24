<script>
  import { auth } from '$lib/stores/auth';
</script>

<div class="p-6">
  <h1 class="text-3xl font-bold text-text mb-6">📊 Panel de Administración</h1>
  
  <p class="text-muted mb-6">
    Bienvenido al panel de admon. Esta vista es solo lectura.
  </p>
  
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <div class="surface p-4 rounded-lg">
      <h3 class="text-semibold text-text mb-2">Sistema</h3>
      <p class="text-muted">Modo: Administrativo</p>
      <p class="text-accent font-medium">HUB v1.1.0</p>
    </div>
    
    <div class="surface p-4 rounded-lg">
      <h3 class="text-semibold text-text mb-2">Autenticación</h3>
      <p class="text-muted">JWT RS256</p>
      <p class="text-accent font-medium">Sin passkeys</p>
    </div>
    
    <div class="surface p-4 rounded-lg">
      <h3 class="text-semibold text-text mb-2">Estado</h3>
      <p class="text-muted">App: Online</p>
      <p class="text-accent font-medium">PWA activa</p>
    </div>
  </div>
  
  <div class="mt-6 pt-6 border-t border-surface/50">
    <h3 class="text-semibold text-text mb-4">Accesos Rápidos</h3>
    <div class="grid grid-cols-2 gap-2">
      <a href="/cotizaciones_materiales" class="block surface p-3 rounded hover:bg-surface/50 transition-colors">
        <lucide-svelte name="package" class="h-5 w-5 mb-2 inline-block" />
        <span class="text-sm text-text">Cotizaciones Materiales</span>
      </a>
      <a href="/telegram" class="block surface p-3 rounded hover:bg-surface/50 transition-colors">
        <lucide-svelte name="message-circle" class="h-5 w-5 mb-2 inline-block" />
        <span class="text-sm text-text">Telegram</span>
      </a>
    </div>
  </div>
</div>