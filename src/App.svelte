<script>
	import { onMount } from 'svelte';
	import { path, navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { onlinePing } from '$lib/stores/online.js';
	import SyncHeader from './components/SyncHeader.svelte';
	import Login from './pages/Login.svelte';
	import Dashboard from './pages/Dashboard.svelte';
	import Cotizaciones from './pages/Cotizaciones.svelte';
	import Usuarios from './pages/Usuarios.svelte';
	import Telegram from './pages/Telegram.svelte';
	import Config from './pages/Config.svelte';

	let ready = false;
	let splashDone = false;
	let splashMsg = '';
	let splashProgress = 0;

	const splashMessages = [
		'💻 Inicializando matriz de datos cuánticos...',
		'🚀 Calibrando condensadores de flujo...',
		'☕ Convirtiendo café en líneas de código...',
		'🤖 Entrenando a los duendes del servidor...',
		'📡 Alineando satélites geosíncronos de ECCSA...',
		'🔑 Desencriptando algoritmos de acceso...',
		'⚙️ Alineando los engranes del servidor de bases de datos...'
	];

	onMount(async () => {
		// Splash corto con logo Admon
		const msgs = [...splashMessages].sort(() => Math.random() - 0.5).slice(0, 2);
		for (let i = 0; i < msgs.length; i++) {
			splashMsg = msgs[i];
			splashProgress = ((i + 1) / msgs.length) * 100;
			await new Promise((r) => setTimeout(r, 800));
		}
		splashDone = true;

		auth.init();
		if (!auth.isLoggedIn() && window.location.pathname !== '/login') {
			navigate('/login', { replace: true });
		}
		ready = true;
		onlinePing().catch(() => {});
	});

	function logout() {
		auth.logout();
		navigate('/login', { replace: true });
	}

	function navClass(p) {
		return 'nav-item' + ($path === p ? ' active' : '');
	}
</script>

{#if !splashDone}
	<div class="splash">
		<img class="splash-logo-img" src="/admon_logo.png" alt="Admon ECCSA" />
		<div class="splash-title">Admon</div>
		<div class="splash-msg">{splashMsg}</div>
		<div class="splash-bar">
			<div class="splash-bar-fill" style="width:{splashProgress}%"></div>
		</div>
	</div>
{:else if ready}
	{#if $auth.user}
		<SyncHeader />
	{/if}

	<div style="padding-top: {$auth.user ? 'calc(3.8rem + env(safe-area-inset-top))' : '0'}">
		{#if $path === '/login'}
			<Login />
		{:else if $path === '/dashboard' || $path === '/'}
			<Dashboard />
		{:else if $path === '/cotizaciones_materiales'}
			<Cotizaciones />
		{:else if $path === '/usuarios'}
			<Usuarios />
		{:else if $path === '/telegram'}
			<Telegram />
		{:else if $path === '/config'}
			<Config />
		{:else}
			<Dashboard />
		{/if}
		<div class="version-badge">Admon v1.0.0</div>
	</div>

	{#if $auth.user}
		<nav class="bottom-nav">
			<a href="/dashboard" class={navClass('/dashboard')}><span class="nav-icon">📊</span><span>Panel</span></a>
			<a href="/cotizaciones_materiales" class={navClass('/cotizaciones_materiales')}><span class="nav-icon">📦</span><span>Cotiz.</span></a>
			{#if $auth.user.acceso_usuarios}
				<a href="/usuarios" class={navClass('/usuarios')}><span class="nav-icon">👥</span><span>Usuarios</span></a>
			{/if}
			<a href="/telegram" class={navClass('/telegram')}><span class="nav-icon">📱</span><span>Telegram</span></a>
			<a href="/config" class={navClass('/config')}><span class="nav-icon">⚙️</span><span>Config</span></a>
			<button on:click={logout} class="nav-item" title="Cerrar sesión"><span class="nav-icon">🚪</span><span>Salir</span></button>
		</nav>
	{/if}
{:else}
	<div class="splash">
		<img class="splash-logo-img" src="/admon_logo.png" alt="Admon ECCSA" />
		<div class="splash-title">Admon</div>
	</div>
{/if}
