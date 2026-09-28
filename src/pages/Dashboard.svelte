<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { api } from '$lib/api.js';
	import ActionsBar from '../components/ActionsBar.svelte';

	// Menú de módulos estilo home de Field: icon/title/desc/path/perm.
	// Solo módulos funcionales; cada tarjeta requiere su permiso activo.
	// ECCSA IA va PRIMERO y sin permiso: en el HUB Jarvis está disponible para
	// todos los usuarios logueados (el backend no exige ningún Acceso).
	const modules = [
		{ icon: '🤖', title: 'ECCSA IA', desc: 'Asistente inteligente', path: '/ia' },
		{ icon: '📝', title: 'Notas', desc: 'Notas del equipo', path: '/notas' },
		{ icon: '📦', title: 'Cotizaciones Materiales', desc: 'Crear y gestionar', path: '/cotizaciones_materiales', perm: 'acceso_cotizaciones' },
		{ icon: '📋', title: 'Registro de Reportes', desc: 'Visualización global admin', path: '/registro_reportes', perm: 'acceso_registro_reportes' },
		{ icon: '👥', title: 'Administrador de Usuarios', desc: 'Usuarios y permisos', path: '/usuarios', perm: 'acceso_usuarios' },
		{ icon: '📇', title: 'Clientes', desc: 'Catálogo general', path: '/clientes', perm: 'acceso_cotizaciones' },
		{ icon: '⛽', title: 'Tickets de OxxoGas', desc: 'Tickets y facturas', path: '/tickets_oxxogas', perm: 'acceso_vales_oxxogas' },
		{ icon: '🛣️', title: 'Kilómetros', desc: 'Consumo semanal y captura', path: '/kilometros', perm: 'acceso_registro_kilometros' },
		// Legends: visible para todos los usuarios logueados (en Field la gatea el
		// permiso de kilómetros; aquí los datos son de la empresa y el ranking lo
		// calcula el worker de workersadmon para las dos apps).
		{ icon: '🏆', title: 'ECCSA Legends', desc: 'Ranking y puntos', path: '/legends' }
	];

	let user = $state(null);

	// Panel de notas en el Dashboard (las más recientes; el módulo completo
	// está en /notas). Si falla la carga, simplemente no se muestra el panel.
	let notas = $state([]);

	// La BD guarda hora de México sin offset → se renderiza tal cual.
	function fmtFecha(iso) {
		if (!iso) return '—';
		const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
		if (m) return `${m[3]}/${m[2]} ${m[4]}:${m[5]}`;
		return '—';
	}

	async function cargarNotas() {
		try {
			notas = ((await api.get('/notas')) || []).slice(0, 6);
		} catch {
			notas = [];
		}
	}

	function visible(mod) {
		return !mod.perm || (user && user[mod.perm]);
	}

	function go(mod) {
		navigate(mod.path);
	}

	function handleLogout() {
		auth.logout();
		navigate('/login', { replace: true });
	}

	onMount(async () => {
		if (!auth.isLoggedIn()) {
			navigate('/login', { replace: true });
			return;
		}
		try {
			const raw = localStorage.getItem('admon_user');
			user = raw ? JSON.parse(raw) : null;
		} catch {
			user = null;
		}
		await cargarNotas();
	});
</script>

<div class="page">
	<div class="header">
		<div class="brand-col">
			<h1 class="brand"><img class="brand-logo" src="/admon_logo.png" alt="Admon" /> Admon</h1>
		</div>
		<!-- Barra de acciones del shell (⚙️ config · 🚪 salir). Admon no pasa
		     onnotif/ononline: no tiene cola de avisos ni usuarios en línea.
		     El componente los oculta si el manejador no está. -->
		<ActionsBar
			onconfig={() => navigate('/config')}
			onlogout={handleLogout}
		/>
	</div>

	<div class="menu-grid">
		{#each modules as mod}
			{#if visible(mod)}
				<button class="module-card" on:click={() => go(mod)}>
					<span class="module-icon">{mod.icon}</span>
					<span class="module-title">{mod.title}</span>
					<span class="module-desc">{mod.desc}</span>
				</button>
			{/if}
		{/each}
	</div>

	<!-- Panel de notas: las más recientes, con autor. Toca → módulo Notas. -->
	{#if notas.length > 0}
		<div class="notas-panel">
			<div class="notas-panel-head">
				<span class="notas-panel-title">📝 Notas del equipo</span>
				<button class="notas-ver" on:click={() => navigate('/notas')}>Ver todas →</button>
			</div>
			<div class="notas-mini-grid">
				{#each notas as n (n.id)}
					<button class="nota-mini" on:click={() => navigate('/notas')} title={n.titulo}>
						<span class="nota-mini-titulo">{n.titulo}</span>
						<span class="nota-mini-texto">{n.contenido}</span>
						<span class="nota-mini-meta">👤 {n.autor} · 🕒 {fmtFecha(n.fecha_creacion)}</span>
					</button>
				{/each}
			</div>
		</div>
	{/if}
</div>

<style>
	.brand-col { display: flex; flex-direction: column; gap: 0; }
	.brand { display: flex; align-items: center; gap: 0.5rem; margin: 0; font-size: 1.2rem; }
	.brand-logo { width: 34px; height: 34px; object-fit: cover; border-radius: 8px; }
	.menu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
	.module-card {
		position: relative;
		display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem;
		min-height: 176px; height: 100%; padding: 1.25rem 0.75rem;
		background: var(--color-surface);
		border: 1px solid rgba(255,255,255,0.05); border-radius: 16px;
		cursor: pointer; transition: all 0.15s; text-align: center;
		color: var(--color-text); font-family: inherit;
	}
	.module-card:active { transform: scale(0.97); background: var(--color-surface-2); }
	.module-icon { font-size: 2.5rem; line-height: 1; height: 2.5rem; display: flex; align-items: center; }
	.module-title { font-weight: 700; font-size: 0.95rem; line-height: 1.25; min-height: 2.4em; display: flex; align-items: center; }
	.module-desc { font-size: 0.75rem; color: var(--color-text-muted); line-height: 1.3; min-height: 2.6em; }

	/* Panel de notas del Dashboard */
	.notas-panel {
		margin-top: 1.25rem;
		background: var(--color-surface);
		border: 1px solid rgba(255, 255, 255, 0.05);
		border-radius: 16px;
		padding: 0.9rem 1rem 1rem;
	}
	.notas-panel-head { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.7rem; }
	.notas-panel-title { font-weight: 700; font-size: 0.95rem; }
	.notas-ver {
		background: transparent;
		border: none;
		color: var(--color-primary);
		font-size: 0.78rem;
		font-weight: 600;
		cursor: pointer;
		font-family: inherit;
		padding: 0.2rem 0.3rem;
	}
	.notas-mini-grid { display: grid; grid-template-columns: 1fr; gap: 0.55rem; }
	.nota-mini {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		text-align: left;
		background: var(--color-background);
		border: 1px solid rgba(255, 255, 255, 0.06);
		border-radius: 10px;
		padding: 0.6rem 0.75rem;
		cursor: pointer;
		font-family: inherit;
		color: var(--color-text);
		transition: border-color 0.12s;
	}
	.nota-mini:hover { border-color: var(--color-primary); }
	.nota-mini-titulo { font-weight: 700; font-size: 0.85rem; line-height: 1.3; }
	.nota-mini-texto {
		font-size: 0.76rem;
		color: var(--color-text-muted);
		line-height: 1.4;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		white-space: pre-wrap;
		word-wrap: break-word;
	}
	.nota-mini-meta { font-size: 0.68rem; color: var(--color-text-muted); margin-top: 0.15rem; }
	@media (min-width: 700px) {
		.notas-mini-grid { grid-template-columns: 1fr 1fr; }
	}
</style>
