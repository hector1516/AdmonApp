<script>
  import { onMount } from 'svelte';
  import { Router, Route, Link, navigate } from 'svelte-routing';
  import { auth } from '$lib/stores/auth.js';
  import Login from './pages/Login.svelte';
  import Dashboard from './pages/Dashboard.svelte';
  import Cotizaciones from './pages/Cotizaciones.svelte';
  import Telegram from './pages/Telegram.svelte';
  import Config from './pages/Config.svelte';

  onMount(() => {
    auth.init();
    // Sin sesión y fuera de /login -> redirigir al login
    if (!auth.isLoggedIn() && window.location.pathname !== '/login') {
      navigate('/login', { replace: true });
    }
  });

  function logout() {
    auth.logout();
    navigate('/login', { replace: true });
  }
</script>

<div class="min-h-screen bg-dark text-text">
  <!-- Barra superior con logo -->
  <header class="flex items-center gap-3 px-4 py-2 border-b border-surface sticky top-0 bg-dark z-10">
    <img src="/admon_logo.png" alt="Admon" class="rounded-lg" style="height: 32px; width: 32px; object-fit: cover;" />
    <span class="font-bold text-text">Admon <span class="text-muted font-normal">· ECCSA</span></span>
  </header>

  <Router>
    <Route path="/login" component={Login} />
    <Route path="/">
      {#if auth.isLoggedIn()}
        <Dashboard />
      {:else}
        <Login />
      {/if}
    </Route>
    <Route path="/dashboard" component={Dashboard} />
    <Route path="/cotizaciones_materiales" component={Cotizaciones} />
    <Route path="/telegram" component={Telegram} />
    <Route path="/config" component={Config} />
  </Router>

  <!-- Nav inferior estilo Field -->
  <nav class="fixed bottom-0 left-0 right-0 bg-dark border-t border-surface/50 flex justify-around py-2">
    <Link to="/dashboard" class="nav-link">📊<span class="nav-label">Panel</span></Link>
    <Link to="/cotizaciones_materiales" class="nav-link">📦<span class="nav-label">Cotiz.</span></Link>
    <Link to="/telegram" class="nav-link">📱<span class="nav-label">Telegram</span></Link>
    <Link to="/config" class="nav-link">⚙️<span class="nav-label">Config</span></Link>
    <button on:click={logout} class="nav-link" title="Cerrar sesión">🚪<span class="nav-label">Salir</span></button>
  </nav>
</div>

<style>
  .nav-link {
    display: flex;
    flex-direction: column;
    align-items: center;
    font-size: 1.1rem;
    color: #F8FAFC;
    text-decoration: none;
    background: none;
    border: none;
    cursor: pointer;
  }
  .nav-label {
    font-size: 0.65rem;
    color: #64748B;
  }
</style>
