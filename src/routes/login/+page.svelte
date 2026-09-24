<script>
  import { auth } from '$lib/stores/auth';
  import { fail } from '@sveltejs/kit';

  let email = '';
  let password = '';
  let error = '';

  async function handleLogin(e) {
    e.preventDefault();
    try {
      await auth.login(email, password);
      // Redirect al dashboard después de login exitoso
      throw { redirect: '/dashboard' };
    } catch (err: any) {
      if (err.redirect) throw err;
      error = err.message || 'Error al iniciar sesión';
      // No hacer fail aquí para no borrar los campos; solo mostrar error
    }
  }
</script>

<div class="min-h-screen bg-dark flex items-center justify-center p-6">
  <div class="surface w-full max-w-md rounded-lg p-8 shadow-xl max-width: 400px">
    <h2 class="text-2xl font-bold text-text text-center mb-6">🔑 Iniciar Sesión</h2>
    
    {#if error}
      <div class="rounded-b bg-red-500/10 border-t border-red-500/20 p-3 mb-4 text-sm text-red-400">
        {error}
      </div>
    {/if}
    
    <form on:submit={handleLogin} class="space-y-4">
      <div>
        <label class="block text-sm text-muted mb-2">Correo Electrónico</label>
        <input 
          type="email" 
          placeholder="usuario@ecc-ssa.com.mx" 
          value={email}
          on:input={(e) => email = e.target.value}
          required
          class="w-full bg-none border border-surface/50 rounded px-3 py-2 text-text focus:outline-none focus:border-primary"
        />
      </div>
      
      <div>
        <label class="block text-sm text-muted mb-2">Contraseña</label>
        <input 
          type="password" 
          placeholder="Ingrese su contraseña" 
          value={password}
          on:input={(e) => password = e.target.value}
          required
          class="w-full bg-none border surface/50 rounded px-3 py-2 text-text focus:outline-none focus:border-primary"
        />
      </div>
      
      <button type="submit" 
        class="w-full bg-primary text-white py-2 rounded font-medium hover:bg-secondary/90 transition-colors"
      >
        Entrar
      </button>
    </form>
    
    <p class="text-center text-sm text-muted mt-4">
      ¿No tienes cuenta? <a href="#" class="text-primary hover underline">Regístrate</a>
    </p>
  </div>
</div>