<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';

	let usuarios = $state([]);
	let loading = $state(true);
	let error = $state('');

	function tieneAcceso() {
		try {
			const raw = localStorage.getItem('admon_user');
			const u = raw ? JSON.parse(raw) : null;
			return !!(u && u.acceso_usuarios);
		} catch {
			return false;
		}
	}

	onMount(async () => {
		if (!auth.isLoggedIn()) {
			navigate('/login', { replace: true });
			return;
		}
		if (!tieneAcceso()) {
			navigate('/dashboard', { replace: true });
			return;
		}
		try {
			const res = await fetch('/users', { headers: auth.authHeader() });
			if (res.ok) {
				usuarios = await res.json();
			} else if (res.status === 401 || res.status === 403) {
				auth.logout();
				navigate('/login', { replace: true });
			} else {
				error = `Error del servidor (${res.status})`;
			}
		} catch (e) {
			console.error('Error cargando usuarios:', e);
			error = 'No se pudo conectar con el servidor.';
		} finally {
			loading = false;
		}
	});
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/dashboard')} title="Volver">⬅️</button>
		<h1>👥 Administrador de usuarios</h1>
	</div>

	<div class="card" style="margin-bottom: 0.75rem;">
		<p style="color: var(--color-text-muted); font-size: 0.8rem; text-transform: uppercase; margin: 0 0 0.25rem;">Total usuarios</p>
		<p style="font-size: 1.5rem; font-weight: 700; margin: 0;">{usuarios.length}</p>
	</div>

	{#if loading}
		<div class="empty">Cargando…</div>
	{:else if error}
		<div class="card"><p style="color: var(--color-danger); margin: 0;">{error}</p></div>
	{:else if usuarios.length === 0}
		<div class="empty">No hay usuarios registrados.</div>
	{:else}
		<div class="list">
			{#each usuarios as u (u.id)}
				<div class="list-card" style="cursor: default;">
					<div>
						<div style="font-weight: 600;">{u.nombre}</div>
						<div style="font-size: 0.8rem; color: var(--color-text-muted);">{u.email}</div>
					</div>
					<div>
						{#if u.acceso_usuarios}
							<span class="badge badge-warning">admin</span>
						{:else}
							<span class="badge badge-info">usuario</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
