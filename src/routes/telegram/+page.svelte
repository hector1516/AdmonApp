<script>
  import { auth } from '$lib/stores/auth';
</script>

<div class="p-6">
  <h1 class="text-2xl font-bold text-text mb-4">📱 Telegram - Alertas</h1>
  
  <div class="surface p-4 rounded-lg mb-6">
    <h3 class="text-semibold text-text mb-2">Configuración del Bot</h3>
    <p class="text-muted">
      El bot de Telegram está configurado y enviará alertas automáticas.
    </p>
    
    <div class="grid grid-cols-2 gap-2 mt-4">
      <div>
        <span class="text-muted">Token: </span>
        <span class="text-xs text-primary break-all">configured</span>
      </div>
      <div>
        <span class="text-muted">Chat ID: </span>
        <span class="text-xs text-primary break-all">configured</span>
      </div>
    </div>
  </div>
  
  <div class="surface p-4 rounded-lg">
    <h3 class="text-semibold text-text mb-2">Alertas Activas</h3>
    <ul class="space-y-2 text-muted">
      <li>
        <lucide-svelte name="trending-up" class="h-4 w-4 mr-2 inline-block" />
        <span>Tipo de cambio USD/MXN - Diario 6:00 AM</span>
      </li>
      <li>
        <lucide-svelte name="gift" class="h-4 w-4 mr-2 inline-block" />
        <span>Vales OxxoGas - Sincronización hora</span>
      </li>
      <li>
        <lucide-svelte name="bing" class="h-4 w-4 mr-2 inline-block" />
        <span>Wallpapers Bing - Cada 6 horas</span>
      </li>
    </ul>
  </div>
  
  <p class="text-center text-sm text-muted mt-6">
    Workers corriendo en segundo plano. Sin módulos operativos en esta vista.
  </div>
</div>