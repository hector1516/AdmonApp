<script>
  import { onMount } from 'svelte';
  import { navigate } from 'svelte-routing';
  import { auth } from '$lib/stores/auth.js';

  onMount(() => {
    if (!auth.isLoggedIn()) navigate('/login', { replace: true });
  });
</script>

<div class="p-6 pb-24">
  <h1 class="text-2xl font-bold text-text mb-4">📱 Telegram - Alertas</h1>

  <div class="surface p-4 rounded-lg mb-6">
    <h3 class="font-semibold text-text mb-2">Configuración del Bot</h3>
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
    <h3 class="font-semibold text-text mb-2">Alertas Activas</h3>
    <ul class="space-y-2 text-muted">
      <li>📈 Tipo de cambio USD/MXN - Diario 6:00 AM</li>
      <li>🎁 Vales OxxoGas - Sincronización hora</li>
      <li>🖼️ Wallpapers Bing - Cada 6 horas</li>
    </ul>
  </div>

  <p class="text-center text-sm text-muted mt-6">
    Workers corriendo en segundo plano. Sin módulos operativos en esta vista.
  </p>
</div>
