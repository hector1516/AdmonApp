<script>
  import { onMount } from 'svelte';
  import { navigate } from 'svelte-routing';
  import { auth } from '$lib/stores/auth.js';

  onMount(() => {
    if (!auth.isLoggedIn()) navigate('/login', { replace: true });
  });
</script>

<div class="p-6 pb-24">
  <h1 class="text-2xl font-bold text-text mb-4">⚙️ Configuración del Sistema</h1>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
    <div class="surface p-4 rounded-lg">
      <h3 class="font-semibold text-text mb-3">Base de Datos</h3>
      <ul class="space-y-2 text-muted">
        <li><strong>Servidor:</strong> 10.188.141.15</li>
        <li><strong>Base de Datos:</strong> ECCSA_Admon</li>
        <li><strong>Usuario:</strong> sa</li>
      </ul>
    </div>

    <div class="surface p-4 rounded-lg">
      <h3 class="font-semibold text-text mb-3">SMTP (Correo)</h3>
      <ul class="space-y-2 text-muted">
        <li><strong>Servidor:</strong> smtpout.secureserver.net</li>
        <li><strong>Puerto:</strong> 465 (SSL)</li>
        <li><strong>Usuario:</strong> robot@ecc-sa.com.mx</li>
      </ul>
    </div>
  </div>

  <div class="surface p-4 rounded-lg">
    <h3 class="font-semibold text-text mb-3">App</h3>
    <ul class="space-y-2 text-muted">
      <li>Versión: 1.0.0 (desarrollo)</li>
      <li>Stack: Svelte 5 + FastAPI</li>
      <li>Base de datos: SQL Server via pymssql</li>
      <li>Autenticación: JWT simple (sin passkeys WebAuthn)</li>
    </ul>
  </div>
</div>
