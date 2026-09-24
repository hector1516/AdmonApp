<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';

	let cotizaciones = $state([]);
	let loading = $state(true);
	let error = $state('');

	onMount(async () => {
		if (!auth.isLoggedIn()) {
			navigate('/login', { replace: true });
			return;
		}
		try {
			const res = await fetch('/cotizaciones/materiales', { headers: auth.authHeader() });
			if (res.ok) {
				cotizaciones = await res.json();
			} else if (res.status === 401 || res.status === 403) {
				auth.logout();
				navigate('/login', { replace: true });
			} else {
				error = `Error del servidor (${res.status})`;
			}
		} catch (e) {
			console.error('Error cargando cotizaciones:', e);
			error = 'No se pudo conectar con el servidor.';
		} finally {
			loading = false;
		}
	});
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/dashboard')} title="Volver">⬅️</button>
		<h1>📦 Cotizaciones de Materiales</h1>
	</div>

	<div class="grid-2" style="margin-bottom: 0.75rem;">
		<div class="card">
			<p style="color: var(--color-text-muted); font-size: 0.7rem; text-transform: uppercase; margin: 0 0 0.25rem;">Total</p>
			<p style="font-size: 1.5rem; font-weight: 700; margin: 0;">{cotizaciones.length}</p>
		</div>
		<div class="card">
			<p style="color: var(--color-text-muted); font-size: 0.7rem; text-transform: uppercase; margin: 0 0 0.25rem;">Estado</p>
			<p style="font-size: 1.5rem; font-weight: 700; margin: 0;">✅</p>
		</div>
	</div>

	<div class="card">
		<h3 style="margin: 0 0 0.75rem; font-size: 0.95rem;">Índice de cotizaciones</h3>

		{#if loading}
			<div class="empty">Cargando…</div>
		{:else if error}
			<p style="color: var(--color-danger); text-align: center;">{error}</p>
		{:else if cotizaciones.length === 0}
			<div class="empty">No hay cotizaciones registradas.</div>
		{:else}
			<div class="list">
				{#each cotizaciones as cot (cot.folio)}
					<div class="list-card" style="cursor: default;">
						<div>
							<div style="font-weight: 600;">{cot.folio}</div>
							<div style="font-size: 0.8rem; color: var(--color-text-muted);">
								{cot.id_cliente || 'N/A'} · {cot.contacto || 'N/A'} · {cot.estatus}
							</div>
						</div>
						<div style="font-weight: 700; color: var(--color-primary-light);">
							${Number(cot.total || 0).toFixed(2)}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
