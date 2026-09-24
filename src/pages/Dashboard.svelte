<script>
	import { onMount } from 'svelte';
	import { navigate } from 'svelte-routing';
	import { auth } from '$lib/stores/auth.js';

	let kpis = [];
	let canAdminUsers = false;

	onMount(async () => {
		if (!auth.isLoggedIn()) {
			navigate('/login', { replace: true });
			return;
		}
		try {
			const raw = localStorage.getItem('admon_user');
			const u = raw ? JSON.parse(raw) : null;
			canAdminUsers = !!(u && u.acceso_usuarios);
		} catch {
			canAdminUsers = false;
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

	function go(path) {
		navigate(path);
	}
</script>

<div class="page">
	<div class="header">
		<h1>📊 Panel de Administración</h1>
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

	{#if canAdminUsers}
		<div class="card" style="margin-bottom: 0.75rem; border-color: rgba(255, 107, 0, 0.35);">
			<h3 style="margin: 0 0 0.5rem; font-size: 0.95rem;">👥 Administración</h3>
			<button type="button" class="btn btn-primary btn-block" on:click={() => go('/usuarios')}>
				👥 Administrador de usuarios
			</button>
		</div>
	{/if}

	<div class="card" style="margin-bottom: 0.75rem;">
		<h3 style="margin: 0 0 0.75rem; font-size: 0.95rem;">Accesos rápidos</h3>
		<div class="list">
			<button type="button" class="list-card" on:click={() => go('/cotizaciones_materiales')}>
				<span>📦 Cotizaciones Materiales</span><span>›</span>
			</button>
			<button type="button" class="list-card" on:click={() => go('/telegram')}>
				<span>📱 Telegram</span><span>›</span>
			</button>
			<button type="button" class="list-card" on:click={() => go('/config')}>
				<span>⚙️ Configuración</span><span>›</span>
			</button>
		</div>
	</div>

	<div class="grid-2">
		<div class="card">
			<h3 style="margin: 0 0 0.5rem; font-size: 0.9rem;">Sistema</h3>
			<p style="color: var(--color-text-muted); margin: 0; font-size: 0.85rem;">Modo: Administrativo</p>
		</div>
		<div class="card">
			<h3 style="margin: 0 0 0.5rem; font-size: 0.9rem;">Autenticación</h3>
			<p style="color: var(--color-text-muted); margin: 0; font-size: 0.85rem;">JWT simple · sin passkeys</p>
		</div>
	</div>
</div>
