<script>
  import { auth } from '$lib/stores/auth';
</script>

<div class="p-6">
  <h1 class="text-2xl font-bold text-text mb-4">⚙️ Configuración del Sistema</h1>
  
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
    <div class="surface p-4 rounded-lg">
      <h3 class="text-semibold text-text mb-3">Base de Datos</h3>
      <ul class="space-y-2 text-muted">
        <li><strong>Servidor:</strong> 10.188.141.15</li>
        <li><strong>Base de Datos:</strong> ECCSA_Admon_Pruebas</li>
        <li><strong>Usuario:</strong> sa</li>
      </ul>
    </div>
    
    <div class="surface p-4 rounded-lg">
      <h3 class="text-semibold text-text mb-3">SMTP (Correo)</h3>
      <ul class="space-y-2 text-muted">
        <li><strong>Servidor:</strong> smtpout.secureserver.net</li>
        <li><strong>Puerto:</strong> 465 (SSL)</li>
        <li><strong>Usuario:</strong> robot@ecc-sa.com.mx</li>
      </ul>
    </div>
  </div>
  
  <div class="surface p-4 rounded-lg">
    <h3 class="text-semibold text-text mb-3">PWA y Push</h3>
    <ul class="space-y-2 text-muted">
      <li><strong>Modo Offline:</strong> Svelte 5 + IndexedDB</li>
      <li><strong>Push Notifications:</strong> VAPID keys configuradas</li>
      <li><strong>Service Worker:</strong> registrado y activo</li>
    </ul>
  </div>
  
  <div class="mt-6 pt-6 border-t border-surface/50">
    <h3 class="text-semibold text-text mb-3">Información de la App</h3>
    <ul class="space-y-2 text-muted">
      <li>Versión: 1.0.0 (desarrollo)</li>
      <li>Stack: Svelte 5 + FastAPI + PWA</li>
      <li>Base de datos: SQL Server via pymssql</li>
      <li>Autenticación: JWT RS256 (sin passkeys WebAuthn)</li>
    </ul>
  </div>
</div>