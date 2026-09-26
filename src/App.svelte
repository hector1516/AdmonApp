<script>
	import { onMount } from 'svelte';
	import { path, navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { onlinePing } from '$lib/stores/online.js';
	import SyncHeader from './components/SyncHeader.svelte';
	import { syncPull, syncPush } from '$lib/sync.js';
	import { prefetchOffline } from '$lib/offlinePrefetch.js';
	import Login from './pages/Login.svelte';
	import Dashboard from './pages/Dashboard.svelte';
	import Cotizaciones from './pages/Cotizaciones.svelte';
	import CotizacionDetalle from './pages/CotizacionDetalle.svelte';
	import CotizacionNueva from './pages/CotizacionNueva.svelte';
	import CotizacionEditar from './pages/CotizacionEditar.svelte';
	import CotizacionNota from './pages/CotizacionNota.svelte';
	import PartidasAdmin from './pages/PartidasAdmin.svelte';
	import CotizacionPdf from './pages/CotizacionPdf.svelte';
	import CotizacionEnviar from './pages/CotizacionEnviar.svelte';
	import CotizacionEstatus from './pages/CotizacionEstatus.svelte';
	import Usuarios from './pages/Usuarios.svelte';
	import UsuarioDetalle from './pages/UsuarioDetalle.svelte';
	import Clientes from './pages/Clientes.svelte';
	import ClienteDetalle from './pages/ClienteDetalle.svelte';
	import RegistroReportes from './pages/RegistroReportes.svelte';
	import RegistroReporteDetalle from './pages/RegistroReporteDetalle.svelte';
	import RegistroReportePreview from './pages/RegistroReportePreview.svelte';
	import EccsaIa from './pages/EccsaIa.svelte';
	import Telegram from './pages/Telegram.svelte';
	import Config from './pages/Config.svelte';
	import Legends from './pages/Legends.svelte';
	import TicketsOxxoGas from './pages/TicketsOxxoGas.svelte';
	import TicketOxxoGasDetalle from './pages/TicketOxxoGasDetalle.svelte';

	let ready = $state(false);
	let splashDone = $state(false);
	let splashMsg = $state('');
	let splashProgress = $state(0);

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
		if (auth.isLoggedIn()) {
			syncPull().then(() => syncPush()).catch(() => {});
		}
	});

	// Prefetch offline: en cuanto hay sesión (login por contraseña/passkey o
	// restauración al cargar) se precargan los últimos 10 registros + detalles
	// de cada módulo a IndexedDB. Throttle interno de 5 min + disparo propio
	// al recuperar la conexión (ver offlinePrefetch.js).
	$effect(() => {
		if ($auth.user) prefetchOffline();
	});

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
			{:else if $path === '/cotizaciones/nueva'}
				<CotizacionNueva />
			{:else if $path.startsWith('/cotizaciones/') && $path.endsWith('/partidas')}
				<PartidasAdmin clave={$path.split('/')[2]} />
			{:else if $path.startsWith('/cotizaciones/') && $path.endsWith('/editar')}
				<CotizacionEditar clave={$path.split('/')[2]} />
			{:else if $path.startsWith('/cotizaciones/') && $path.endsWith('/nota')}
				<CotizacionNota clave={$path.split('/')[2]} />
			{:else if $path.startsWith('/cotizaciones/') && $path.endsWith('/pdf')}
				<CotizacionPdf clave={$path.split('/')[2]} />
			{:else if $path.startsWith('/cotizaciones/') && $path.endsWith('/enviar')}
				<CotizacionEnviar clave={$path.split('/')[2]} />
			{:else if $path.startsWith('/cotizaciones/') && $path.endsWith('/estatus')}
				<CotizacionEstatus clave={$path.split('/')[2]} />
			{:else if $path.startsWith('/cotizaciones/')}
				<CotizacionDetalle clave={$path.split('/')[2]} />
			{:else if $path === '/usuarios'}
				<Usuarios />
			{:else if $path.startsWith('/usuarios/')}
				<UsuarioDetalle id={$path.split('/')[2]} />
			{:else if $path === '/telegram'}
				<Telegram />
			{:else if $path === '/ia'}
				<EccsaIa />
{:else if $path === '/clientes'}
				<Clientes />
			{:else if $path.startsWith('/clientes/')}
				<ClienteDetalle id={$path.split('/')[2]} />
			{:else if $path === '/registro_reportes'}
				<RegistroReportes />
			{:else if $path.startsWith('/registro_reportes/') && $path.endsWith('/preview')}
				<RegistroReportePreview id={$path.split('/')[2]} />
			{:else if $path.startsWith('/registro_reportes/')}
				<RegistroReporteDetalle id={$path.split('/')[2]} />
			{:else if $path === '/config'}
				<Config />
			{:else if $path === '/legends'}
				<Legends />
			{:else if $path === '/tickets_oxxogas'}
				<TicketsOxxoGas />
			{:else if $path.startsWith('/tickets_oxxogas/')}
				<TicketOxxoGasDetalle id={$path.split('/')[2]} />
		{:else}
			<Dashboard />
		{/if}
		<div class="version-badge">Admon v1.0.1</div>
	</div>
{:else}
	<div class="splash">
		<img class="splash-logo-img" src="/admon_logo.png" alt="Admon ECCSA" />
		<div class="splash-title">Admon</div>
	</div>
{/if}
