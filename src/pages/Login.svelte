<script>
  import { navigate } from 'svelte-routing';
  import { auth } from '$lib/stores/auth.js';

  let email = '';
  let password = '';
  let error = '';
  let loading = false;

  async function handleLogin(e) {
    e.preventDefault();
    error = '';
    loading = true;
    try {
      await auth.login(email, password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      error = err.message || 'Error al iniciar sesión';
    } finally {
      loading = false;
    }
  }
</script>

<div class="min-h-screen bg-dark flex items-center justify-center p-6">
  <div class="surface w-full rounded-lg p-8 shadow-xl" style="max-width: 400px;">
    <div class="flex justify-center mb-4">
      <img src="/admon_logo.png" alt="Admon ECCSA" class="rounded-2xl" style="height: 96px; width: 96px; object-fit: cover;" />
    </div>
    <h2 class="text-2xl font-bold text-text text-center mb-6">🔑 Iniciar Sesión</h2>

    {#if error}
      <div class="rounded bg-red-500/10 border border-red-500/20 p-3 mb-4 text-sm text-red-400">
        {error}
      </div>
    {/if}

    <form on:submit={handleLogin} class="space-y-4">
      <div>
        <label class="block text-sm text-muted mb-2" for="email">Correo Electrónico</label>
        <input
          id="email"
          type="email"
          placeholder="usuario@ecc-ssa.com.mx"
          bind:value={email}
          required
          class="w-full bg-dark border border-surface rounded px-3 py-2 text-text focus:outline-none"
        />
      </div>

      <div>
        <label class="block text-sm text-muted mb-2" for="password">Contraseña</label>
        <input
          id="password"
          type="password"
          placeholder="Ingrese su contraseña"
          bind:value={password}
          required
          class="w-full bg-dark border border-surface rounded px-3 py-2 text-text focus:outline-none"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        class="w-full bg-primary text-white py-2 rounded font-medium"
      >
        {loading ? 'Verificando…' : 'Entrar'}
      </button>
    </form>
  </div>
</div>
