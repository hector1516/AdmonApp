<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';

	// Menú de módulos estilo Field: icon/title/desc/path/perm.
	// listo=true navega; listo=false muestra badge PRONTO (aún no funciona).
	const modules = [
		{ icon: '📦', title: 'Cotizaciones Materiales', desc: 'Crear y gestionar', path: '/cotizaciones_materiales', perm: 'acceso_cotizaciones', listo: true },
		{ icon: '👥', title: 'Administrador de Usuarios', desc: 'Usuarios y permisos', path: '/usuarios', perm: 'acceso_usuarios', listo: true },
		{ icon: '📱', title: 'Telegram', desc: 'Bot y alertas', path: '/telegram', perm: 'acceso_telegram', listo: true },
		{ icon: '🧮', title: 'Cálculos de Cotización', desc: 'Motor de cálculo', path: '', perm: 'acceso_calculo', listo: false },
		{ icon: '🏗️', title: 'Cotiz. Servicios y Proyectos', desc: 'Folio CSP', path: '', perm: 'acceso_cotizaciones', listo: false },
		{ icon: '📋', title: 'Inventario', desc: 'Stock y categorías', path: '', perm: 'acceso_inventario', listo: false },
		{ icon: '💰', title: 'Nóminas', desc: 'Sueldos semanales', path: '', perm: 'acceso_nominas', listo: false },
		{ icon: '🏭', title: 'Proveedores', desc: 'Catálogo PROV', path: '', perm: 'acceso_proveedores', listo: false },
		{ icon: '🧾', title: 'Órdenes de Compra', desc: 'Folio OC', path: '', perm: 'acceso_oc', listo: false },
		{ icon: '⚙️', title: 'Configuración', desc: 'Sistema y PWA', path: '/config', perm: null, listo: true }
	];

	let kpis = [];
	let user = null;

	function visible(mod) {
		return !mod.perm || (user && user[mod.perm]);
	}

	function go(mod) {
		if (mod.listo && mod.path) navigate(mod.path);
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
		try {
			const res = await fetch('/dashboard/kpis', { headers: auth.authHeader() });
			if (res.ok) {
				const data = await res.json();
				kpis = data.kpis || [];
			} else if (res.status === 401 || res.status === 403) {
				auth.logout();
				navigate('/login', { replace: true });
			}
		} catch (e) {
			console.error('Error cargando KPIs:', e);
		}
	});
</script>

<div class="page">
	<div class="header">
		<div class="brand-col">
			<h1 class="brand"><img class="brand-logo" src="/admon_logo.png" alt="Admon" /> Admon</h1>
		</div>
	</div>

	{#if kpis.length > 0}
		<div class="grid-2" style="margin-bottom: 0.75rem;">
			{#each kpis as kpi}
				<div class="card">
					<p style="color: var(--color-text-muted); font-size: 0.7rem; text-transform: uppercase; margin: 0 0 0.25rem;">{kpi.etiqueta}</p>
					<p style="font-size: 1.5rem; font-weight: 700; margin: 0;">{kpi.valor}</p>
				</div>
			{/each}
		</div>
	{/if}

	<div class="menu-grid">
		{#each modules as mod}
			{#if visible(mod)}
				<button
					class="module-card"
					class:pronto={!mod.listo}
					on:click={() => go(mod)}
					disabled={!mod.listo}
				>
					<span class="module-icon">{mod.icon}</span>
					<span class="module-title">{mod.title}</span>
					<span class="module-desc">{mod.desc}</span>
					{#if !mod.listo}
						<span class="module-badge">PRONTO</span>
					{/if}
				</button>
			{/if}
		{/each}
	</div>
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
	.module-card.pronto { opacity: 0.75; cursor: default; }
	.module-card.pronto:active { transform: none; }
	.module-icon { font-size: 2.5rem; line-height: 1; height: 2.5rem; display: flex; align-items: center; }
	.module-title { font-weight: 700; font-size: 0.95rem; line-height: 1.25; min-height: 2.4em; display: flex; align-items: center; }
	.module-desc { font-size: 0.75rem; color: var(--color-text-muted); line-height: 1.3; min-height: 2.6em; }
	.module-badge {
		position: absolute; top: 10px; right: 10px;
		background: var(--color-warning); color: #000;
		border-radius: 999px; font-size: 0.65rem; font-weight: 700;
		padding: 0.15rem 0.5rem;
	}
</style>
