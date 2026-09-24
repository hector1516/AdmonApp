<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { online } from '$lib/stores/online.js';
	import { listar } from '$lib/cotizacionesApi.js';
	import { mapEstatus, fmtMXN, folioFmt } from '$lib/cotizaciones.js';

	let cotizaciones = $state([]);
	let loading = $state(true);
	let error = $state('');
	let busqueda = $state('');

	function tieneAcceso() {
		try {
			const u = JSON.parse(localStorage.getItem('admon_user') || 'null');
			return !!(u && u.acceso_cotizaciones);
		} catch {
			return false;
		}
	}

	function estatusBadge(est) {
		const e = mapEstatus(est);
		if (e.includes('FACTURADA')) return 'badge-success';
		if (e.includes('LISTA')) return 'badge-warning';
		return 'badge-info';
	}

	let filtradas = $derived(
		!busqueda.trim()
			? cotizaciones
			: cotizaciones.filter((c) => {
					const q = busqueda.trim().toLowerCase();
					return [c.folio_fmt || folioFmt(c.folio), c.id_cliente, c.cliente, c.contacto, c.autor, c.descripcion, String(c.total ?? '')]
						.map((v) => String(v || '').toLowerCase())
						.some((v) => v.includes(q));
				})
	);

	async function cargar() {
		loading = true;
		error = '';
		try {
			cotizaciones = await listar();
		} catch (e) {
			console.error('Error cargando cotizaciones:', e);
			error = e.message === 'Sesión expirada' ? e.message : 'No se pudo cargar. Revisa tu conexión.';
		} finally {
			loading = false;
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
		await cargar();
	});
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/dashboard')} title="Volver">⬅️</button>
		<h1>📦 Cotizaciones</h1>
		<div style="flex:1"></div>
		<button class="btn btn-sm btn-primary" on:click={() => navigate('/cotizaciones/nueva')} title="Nueva cotización">➕</button>
	</div>

	<div class="field">
		<input
			class="input"
			placeholder="🔍 folio, cliente, contacto, autor, descripción o monto…"
			bind:value={busqueda}
		/>
	</div>

	{#if !$online}
		<div class="card" style="margin-bottom: 0.75rem; border-color: rgba(239,68,68,0.4);">
			<p style="margin: 0; font-size: 0.85rem;">🔴 Sin conexión — mostrando datos guardados.</p>
		</div>
	{/if}

	<p style="color: var(--color-text-muted); font-size: 0.8rem;">
		Mostrando {filtradas.length} de {cotizaciones.length} cotizaciones.
	</p>

	{#if loading}
		<div class="empty">Cargando…</div>
	{:else if error}
		<div class="card"><p style="color: var(--color-danger); margin: 0;">{error}</p></div>
	{:else if filtradas.length === 0}
		<div class="empty">No hay cotizaciones registradas.</div>
	{:else}
		<div class="list">
			{#each filtradas as c (c.idLocal)}
				<button
					class="list-card"
					on:click={() => navigate(`/cotizaciones/${c.folio ?? c.idLocal}`)}
				>
					<div style="flex: 1; min-width: 0;">
						<div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
							<strong>{c.folio != null ? folioFmt(c.folio) : '⏳ Sin folio'}</strong>
							<span class="badge {estatusBadge(c.estatus)}" style="font-size: 0.65rem;">{mapEstatus(c.estatus)}</span>
							{#if c.folio == null || !c.synced}
								<span class="badge badge-warning" style="font-size: 0.65rem;">⏳ pendiente</span>
							{/if}
						</div>
						<div style="font-size: 0.85rem; margin-top: 0.25rem;">{c.cliente || c.id_cliente || 'N/A'}</div>
						<div style="font-size: 0.75rem; color: var(--color-text-muted);">
							{c.contacto || '—'} · {c.fecha || ''} · {c.autor || ''}
						</div>
						<div style="font-size: 0.8rem; color: var(--color-text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
							{c.descripcion || ''}
						</div>
					</div>
					<div style="text-align: right; flex-shrink: 0;">
						<div style="font-weight: 700; color: var(--color-primary-light);">{fmtMXN(c.total)}</div>
						<span style="color: var(--color-text-muted);">›</span>
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>
