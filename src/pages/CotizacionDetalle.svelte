<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { header, partidas, borrar, clonar } from '$lib/cotizacionesApi.js';
	import { folioFmt, fmtMXN, totales, mapEstatus, COLOR_LABEL } from '$lib/cotizaciones.js';

	let { clave } = $props();

	let h = $state(null);
	let items = $state([]);
	let loading = $state(true);
	let error = $state('');
	let msg = $state('');
	let busy = $state(false);

	function tieneAcceso() {
		try {
			const u = JSON.parse(localStorage.getItem('admon_user') || 'null');
			return !!(u && u.acceso_cotizaciones);
		} catch {
			return false;
		}
	}

	let tots = $derived(totales(items));
	let bloqueado = $derived((h?.color ?? 0) === 1 || (h?.color ?? 0) === 2);
	let pendiente = $derived(!h || h.folio == null || !h.synced);

	async function cargar() {
		loading = true;
		error = '';
		msg = '';
		try {
			h = await header(clave);
			items = await partidas(h.folio ?? h.idLocal);
		} catch (e) {
			console.error('Error cargando detalle:', e);
			error = e.message === 'Sesión expirada' ? e.message : `No se pudo cargar (${e.message || 'sin conexión'}).`;
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

	async function onClonar() {
		if (!h || h.folio == null) {
			error = 'Primero sincroniza esta cotización para clonarla.';
			return;
		}
		if (!confirm(`¿Clonar ${folioFmt(h.folio)} con todas sus partidas?`)) return;
		busy = true;
		error = '';
		try {
			const r = await clonar(h.folio);
			navigate(`/cotizaciones/${r.folio ?? r.folioKey}`, { replace: true });
			await cargar();
		} catch (e) {
			error = e.message || 'No se pudo clonar.';
		} finally {
			busy = false;
		}
	}

	async function onBorrar() {
		if (!h || h.folio == null) {
			error = 'Solo se puede borrar online con folio asignado.';
			return;
		}
		if (!confirm(`¿Eliminar definitivamente ${folioFmt(h.folio)} y sus partidas? Es irreversible.`)) return;
		busy = true;
		error = '';
		try {
			await borrar(h.folio);
			navigate('/cotizaciones_materiales', { replace: true });
		} catch (e) {
			error = e.message || 'No se pudo eliminar. Revisa tu conexión.';
			busy = false;
		}
	}
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/cotizaciones_materiales')} title="Volver">⬅️</button>
		<h1>📋 {h ? folioFmt(h.folio ?? h.idLocal) : '…'}</h1>
		{#if pendiente}
			<span class="badge badge-warning">⏳ pendiente</span>
		{/if}
	</div>

	{#if loading}
		<div class="empty">Cargando…</div>
	{:else if error && !h}
		<div class="card"><p style="color: var(--color-danger); margin: 0;">{error}</p></div>
	{:else if h}
		<div class="card" style="margin-bottom: 0.75rem;">
			<div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem;">
				<span class="badge {mapEstatus(h.estatus).includes('FACTURADA') ? 'badge-success' : mapEstatus(h.estatus).includes('LISTA') ? 'badge-warning' : 'badge-info'}">
					{COLOR_LABEL[h.color] || mapEstatus(h.estatus)}
				</span>
			</div>
			<p style="margin: 0.2rem 0;"><strong>Cliente:</strong> {h.cliente_nombre || h.cliente || h.id_cliente || 'N/A'}</p>
			<p style="margin: 0.2rem 0;"><strong>Contacto:</strong> {h.contacto || 'N/A'}</p>
			<p style="margin: 0.2rem 0;"><strong>Descripción:</strong> {h.descripcion || '—'}</p>
			<p style="margin: 0.2rem 0; color: var(--color-text-muted); font-size: 0.85rem;">
				Creado por {h.autor || '—'} · {h.fecha || ''}
			</p>
			<p style="margin: 0.4rem 0 0; font-size: 1.2rem; font-weight: 800; color: var(--color-primary-light);">
				Total: {fmtMXN(tots.total)}
			</p>
		</div>

		<div class="card" style="margin-bottom: 0.75rem;">
			<div class="card-title">📝 Nota interna</div>
			{#if (h.nota || '').trim()}
				<p style="margin: 0; font-size: 0.9rem;">{h.nota}</p>
			{:else}
				<p style="margin: 0; font-size: 0.85rem; color: var(--color-text-muted);">Sin notas registradas.</p>
			{/if}
		</div>

		<div class="card" style="margin-bottom: 0.75rem;">
			<div class="card-title">📦 Partidas ({items.length})</div>
			{#if items.length === 0}
				<p style="margin: 0; font-size: 0.85rem; color: var(--color-text-muted);">Sin partidas registradas.</p>
			{:else}
				<div class="list">
					{#each items as p (p.partida)}
						<div class="list-card" style="cursor: default;">
							<div style="flex: 1; min-width: 0;">
								<div style="font-size: 0.75rem; color: var(--color-text-muted);">
									#{p.partida} · cant. {p.cantidad}
									{#if !p.synced}<span class="badge badge-warning" style="font-size: 0.6rem;">⏳</span>{/if}
								</div>
								<div style="font-size: 0.9rem; font-weight: 600;">{p.descripcion}</div>
								<div style="font-size: 0.75rem; color: var(--color-text-muted);">{p.proveedor || 'Sin proveedor'}</div>
							</div>
							<div style="font-weight: 700; color: var(--color-primary-light); flex-shrink: 0;">{fmtMXN(p.total_venta)}</div>
						</div>
					{/each}
				</div>
			{/if}
			<div style="margin-top: 0.75rem; font-size: 0.9rem;">
				<div style="display: flex; justify-content: space-between;"><span style="color: var(--color-text-muted);">Subtotal</span><strong>{fmtMXN(tots.subtotal)}</strong></div>
				<div style="display: flex; justify-content: space-between;"><span style="color: var(--color-text-muted);">IVA 16%</span><strong>{fmtMXN(tots.iva)}</strong></div>
				<div style="display: flex; justify-content: space-between; font-size: 1.05rem;"><span>Total</span><strong style="color: var(--color-primary-light);">{fmtMXN(tots.total)}</strong></div>
			</div>
		</div>

		{#if error}
			<div class="msg err">{error}</div>
		{/if}
		{#if msg}
			<div class="msg ok">{msg}</div>
		{/if}

		<div class="grid-2" style="margin-bottom: 0.5rem;">
			<button class="btn btn-primary btn-block" on:click={() => navigate(`/cotizaciones/${clave}/partidas`)} disabled={bloqueado || busy}>📝 Partidas</button>
			<button class="btn btn-secondary btn-block" on:click={() => navigate(`/cotizaciones/${clave}/editar`)} disabled={bloqueado || busy}>✏️ Modificar</button>
		</div>
		<div class="grid-2" style="margin-bottom: 0.5rem;">
			<button class="btn btn-secondary btn-block" on:click={() => navigate(`/cotizaciones/${clave}/nota`)} disabled={busy}>📝 Nota</button>
			<button class="btn btn-secondary btn-block" on:click={onClonar} disabled={busy}>🐑 Clonar</button>
		</div>
		<button class="btn btn-danger btn-block" on:click={onBorrar} disabled={bloqueado || busy}>🚨 Borrar cotización</button>
		{#if bloqueado}
			<p class="hint" style="margin-top: 0.5rem;">🔒 Bloqueada (lista para facturar / facturada).</p>
		{/if}
	{/if}
</div>

<style>
	.card-title { font-weight: 700; font-size: 1rem; margin-bottom: 0.25rem; }
	.msg { padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 0.75rem; }
	.msg.err { background: rgba(239,68,68,0.1); color: #EF4444; }
	.msg.ok { background: rgba(34,197,94,0.1); color: #22C55E; }
	.hint { font-size: 0.8rem; color: var(--color-text-muted); }
	.card { margin-bottom: 0.75rem; }
</style>
