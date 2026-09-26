<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { api } from '$lib/api.js';

	// Tickets de OxxoGas: lectura de HUB_OxxoGasTickets (captura en Field/HUB)
	// con factura CFDI enlazada y estación. Orden: más reciente arriba.
	// Identificador principal: folio del ticket impreso (FolioTicket).

	let tickets = $state([]);
	let loading = $state(true);
	let error = $state('');
	let busqueda = $state('');
	let sel = $state(null); // ticket abierto en el modal

	function tieneAcceso() {
		try {
			const u = JSON.parse(localStorage.getItem('admon_user') || 'null');
			return !!(u && u.acceso_vales_oxxogas);
		} catch {
			return false;
		}
	}

	function token() {
		return localStorage.getItem('admon_token') || '';
	}

	// Las imágenes requieren auth: se manda ?token= (mismo patrón que los PDFs)
	function imgUrl(t, w) {
		return `/api/tickets-oxxogas/${t.id}/imagen?w=${w}&token=${encodeURIComponent(token())}`;
	}

	function fmtFecha(iso) {
		if (!iso) return '—';
		const d = new Date(iso);
		const p = (n) => String(n).padStart(2, '0');
		return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
	}

	function fmtMonto(m) {
		return m != null ? `$${Number(m).toFixed(2)}` : null;
	}

	// Búsqueda por folio, cliente, estación, vehículo, capturó, descripción y
	// factura; "pendiente" encuentra tickets sin factura o sin estación.
	let filtrados = $derived.by(() => {
		const q = busqueda.trim().toLowerCase();
		if (!q) return tickets;
		return tickets.filter((t) => {
			const texto = [t.folio, t.cliente, t.estacion, t.marca_modelo, t.placas, t.capturo, t.descripcion, t.factura, t.concepto]
				.filter(Boolean)
				.join(' ')
				.toLowerCase();
			if (texto.includes(q)) return true;
			if (q.includes('pendiente')) return !t.factura || !t.estacion;
			return false;
		});
	});

	async function cargar() {
		loading = true;
		error = '';
		try {
			tickets = await api.get('/tickets-oxxogas');
		} catch (e) {
			error = e.message === 'Sesión expirada' ? e.message : e.message || 'No se pudo cargar.';
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

	function cerrarModal() {
		sel = null;
	}
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" onclick={() => navigate('/dashboard')} title="Volver">⬅️</button>
		<h1>⛽ Tickets de OxxoGas</h1>
		<div style="flex:1"></div>
		<span class="count">{filtrados.length} ticket{filtrados.length === 1 ? '' : 's'}</span>
	</div>

	<div class="field">
		<input class="input" placeholder="🔍 Buscar por folio, cliente, estación, vehículo, factura…" bind:value={busqueda} />
	</div>

	<p class="hint">Tickets capturados desde Field/HUB · orden por fecha y hora de captura (más reciente arriba) · escribe <strong>pendiente</strong> para filtrar los que faltan</p>

	{#if loading}
		<div class="state">⏳ Cargando tickets…</div>
	{:else if error}
		<div class="state err">⚠️ {error}</div>
	{:else if filtrados.length === 0}
		<div class="state">🎫 No hay tickets{busqueda.trim() ? ` que coincidan con “${busqueda.trim()}”` : ''}.</div>
	{:else}
		<div class="grid">
			{#each filtrados as t (t.id)}
				<button class="card-ticket" onclick={() => (sel = t)} title="Ver detalle">
					<div class="thumb">
						{#if t.tiene_foto}
							<img src={imgUrl(t, 400)} alt="Ticket {t.folio}" loading="lazy" decoding="async" />
						{:else}
							<div class="no-photo">🎫<span>Sin foto</span></div>
						{/if}
					</div>
					<div class="body">
						<div class="folio">#{t.folio}</div>
						<div class="fecha">🕐 {fmtFecha(t.fecha)}</div>
						<div class="chips">
							{#if t.factura}
								<span class="chip ok" title="Factura enlazada">🧾 {t.factura}</span>
							{:else}
								<span class="chip pend" title="Sin factura">⏳ Factura: Pendiente</span>
							{/if}
							{#if t.estacion}
								<span class="chip ok" title="Estación capturada">⛽ {t.estacion}</span>
							{:else}
								<span class="chip pend" title="Sin estación">⏳ Estación: Pendiente</span>
							{/if}
						</div>
						{#if t.cliente}<div class="row">🏢 {t.cliente}</div>{/if}
						{#if t.marca_modelo || t.placas}
							<div class="row">🚗 {[t.marca_modelo, t.placas].filter(Boolean).join(' · ')}</div>
						{/if}
						{#if t.capturo}<div class="row">👤 Capturó: {t.capturo}</div>{/if}
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>

<!-- Modal detalle -->
{#if sel}
	<div class="overlay" onclick={cerrarModal}>
		<div class="modal" onclick={(e) => e.stopPropagation()}>
			<div class="modal-header">
				<div>
					<div class="modal-folio">#{sel.folio}</div>
					<div class="modal-sub">🎫 Ticket de OxxoGas · capturado {fmtFecha(sel.fecha)}</div>
				</div>
				<button class="btn btn-sm btn-secondary" onclick={cerrarModal} title="Cerrar">✖️</button>
			</div>

			<div class="modal-grid">
				<div class="modal-img">
					{#if sel.tiene_foto}
						<img src={imgUrl(sel, 0)} alt="Ticket {sel.folio}" />
					{:else}
						<div class="no-photo big">🎫<span>Sin foto registrada</span></div>
					{/if}
				</div>
				<div class="modal-info">
					<div class="info-box">
						<div class="info-label">Relación factura ↔ estación</div>
						{#if sel.factura}
							<div class="info-line"><span>🧾 Factura</span><strong>{sel.factura}</strong></div>
							{#if sel.monto != null}<div class="info-line"><span>Monto</span><strong>{fmtMonto(sel.monto)}</strong></div>{/if}
							{#if sel.litros != null}<div class="info-line"><span>Litros</span><strong>{Number(sel.litros).toFixed(2)} L</strong></div>{/if}
							{#if sel.concepto}<div class="info-line"><span>Concepto</span><strong>{sel.concepto}</strong></div>{/if}
						{:else}
							<div class="pend-row">⏳ Factura: <strong>Pendiente</strong></div>
						{/if}
						{#if sel.estacion}
							<div class="info-line"><span>⛽ Estación</span><strong>{sel.estacion}</strong></div>
						{:else}
							<div class="pend-row">⏳ Estación: <strong>Pendiente</strong></div>
						{/if}
					</div>
					<div class="info-box">
						<div class="info-label">Datos del ticket</div>
						<div class="info-line"><span>🎫 Folio</span><strong>#{sel.folio}</strong></div>
						<div class="info-line"><span>🕐 Capturado</span><strong>{fmtFecha(sel.fecha)}</strong></div>
						{#if sel.cliente}<div class="info-line"><span>🏢 Cliente</span><strong>{sel.cliente}</strong></div>{/if}
						{#if sel.marca_modelo || sel.placas}
							<div class="info-line"><span>🚗 Vehículo</span><strong>{[sel.marca_modelo, sel.placas].filter(Boolean).join(' · ')}</strong></div>
						{/if}
						{#if sel.capturo}<div class="info-line"><span>👤 Capturó</span><strong>{sel.capturo}</strong></div>{/if}
						{#if sel.descripcion}<div class="info-line"><span>📝 Descripción</span><strong>{sel.descripcion}</strong></div>{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.page { max-width: 1200px; margin: 0 auto; padding: 1rem; }
	.header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
	.header h1 { font-size: 1.25rem; margin: 0; color: #f1f5f9; }
	.count { font-size: 0.8rem; color: #94a3b8; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 999px; padding: 0.25rem 0.7rem; }
	.hint { font-size: 0.75rem; color: #64748b; margin: 0 0 0.9rem; }
	.hint strong { color: #FFAE00; }
	.state { text-align: center; color: #94a3b8; padding: 3rem 1rem; font-size: 0.9rem; }
	.state.err { color: #f87171; }

	.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 0.9rem; }

	.card-ticket { text-align: left; background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 14px; overflow: hidden; padding: 0; cursor: pointer; transition: transform 0.15s, border-color 0.15s; color: inherit; font: inherit; }
	.card-ticket:hover { transform: translateY(-3px); border-color: rgba(255, 107, 0, 0.5); }
	.thumb { aspect-ratio: 4 / 3; background: #0f172a; display: flex; align-items: center; justify-content: center; overflow: hidden; }
	.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
	.no-photo { display: flex; flex-direction: column; align-items: center; gap: 0.3rem; color: #475569; font-size: 2rem; }
	.no-photo span { font-size: 0.7rem; }
	.no-photo.big { font-size: 3.5rem; padding: 3rem 0; }

	.body { padding: 0.75rem 0.85rem 0.9rem; }
	.folio { font-family: ui-monospace, 'Cascadia Mono', monospace; font-weight: 800; font-size: 1.05rem; color: #FFAE00; letter-spacing: 0.5px; }
	.fecha { font-size: 0.72rem; color: #94a3b8; margin-top: 0.15rem; }
	.chips { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.55rem; }
	.chip { font-size: 0.68rem; font-weight: 700; border-radius: 999px; padding: 0.22rem 0.6rem; border: 1px solid transparent; }
	.chip.ok { color: #4ade80; background: rgba(74, 222, 128, 0.1); border-color: rgba(74, 222, 128, 0.25); }
	.chip.pend { color: #fbbf24; background: rgba(251, 191, 36, 0.1); border-color: rgba(251, 191, 36, 0.3); }
	.row { font-size: 0.75rem; color: #cbd5e1; margin-top: 0.4rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

	/* Modal */
	.overlay { position: fixed; inset: 0; background: rgba(2, 6, 23, 0.8); backdrop-filter: blur(3px); display: flex; align-items: center; justify-content: center; z-index: 60; padding: 1rem; }
	.modal { background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; max-width: 980px; width: 100%; max-height: 92vh; overflow-y: auto; padding: 1rem 1.1rem 1.2rem; }
	.modal-header { display: flex; align-items: flex-start; gap: 1rem; margin-bottom: 0.9rem; }
	.modal-folio { font-family: ui-monospace, 'Cascadia Mono', monospace; font-weight: 800; font-size: 1.4rem; color: #FFAE00; }
	.modal-sub { font-size: 0.78rem; color: #94a3b8; }
	.modal-header > button { margin-left: auto; }
	.modal-grid { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 1rem; }
	@media (max-width: 760px) { .modal-grid { grid-template-columns: 1fr; } }
	.modal-img { background: #0f172a; border-radius: 12px; overflow: hidden; display: flex; align-items: center; justify-content: center; }
	.modal-img img { width: 100%; max-height: 70vh; object-fit: contain; display: block; }
	.modal-info { display: flex; flex-direction: column; gap: 0.75rem; }
	.info-box { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 12px; padding: 0.7rem 0.85rem; }
	.info-label { font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.6px; color: #FFAE00; margin-bottom: 0.5rem; }
	.info-line { display: flex; justify-content: space-between; gap: 1rem; font-size: 0.8rem; padding: 0.22rem 0; border-bottom: 1px dashed rgba(255, 255, 255, 0.05); }
	.info-line:last-child { border-bottom: none; }
	.info-line span { color: #94a3b8; flex-shrink: 0; }
	.info-line strong { color: #f1f5f9; text-align: right; font-weight: 600; overflow-wrap: anywhere; }
	.pend-row { font-size: 0.82rem; color: #fbbf24; background: rgba(251, 191, 36, 0.08); border: 1px dashed rgba(251, 191, 36, 0.35); border-radius: 8px; padding: 0.45rem 0.6rem; margin-top: 0.3rem; }
</style>
