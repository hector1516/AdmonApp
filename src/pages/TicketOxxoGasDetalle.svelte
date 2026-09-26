<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { api } from '$lib/api.js';

	// Detalle de un ticket de OxxoGas como PÁGINA COMPLETA
	// (ruta /tickets_oxxogas/:id, deep-link soportado por el fallback SPA).
	// Los datos vienen del índice (GET /api/tickets-oxxogas) y se filtran por id.

	let { id } = $props();

	let t = $state(null);
	let loading = $state(true);
	let error = $state('');
	let imgError = $state(false); // offline o imagen no disponible

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

	// w=0 => imagen original (el backend solo hace thumbnail si w>0)
	function imgUrl(ticket, w) {
		return `/api/tickets-oxxogas/${ticket.id}/imagen?w=${w}&token=${encodeURIComponent(token())}`;
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
			const lista = await api.get('/tickets-oxxogas');
			t = (lista || []).find((x) => String(x.id) === String(id)) || null;
			if (!t) error = 'No se encontró el ticket.';
		} catch (e) {
			error = e.message === 'Sesión expirada' ? e.message : e.message || 'No se pudo cargar el ticket.';
		} finally {
			loading = false;
		}
	});
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" onclick={() => navigate('/tickets_oxxogas')} title="Volver al listado">⬅️</button>
		<h1>🎫 Ticket {t ? `#${t.folio}` : ''}</h1>
		<div style="flex:1"></div>
		{#if t}<span class="fecha-head">🕐 {fmtFecha(t.fecha)}</span>{/if}
	</div>

	{#if loading}
		<div class="state">⏳ Cargando ticket…</div>
	{:else if error}
		<div class="state err">⚠️ {error}</div>
	{:else if t}
		<div class="grid">
			<div class="img-box">
				{#if t.tiene_foto && !imgError}
					<img src={imgUrl(t, 0)} alt="Ticket {t.folio}" onerror={() => (imgError = true)} />
				{:else if t.tiene_foto}
					<div class="no-photo">📴<span>Foto no disponible sin conexión</span></div>
				{:else}
					<div class="no-photo">🎫<span>Sin foto registrada</span></div>
				{/if}
			</div>

			<div class="col">
				<div class="info-box folio-box">
					<div class="folio-big">#{t.folio}</div>
					<div class="folio-sub">🎫 Ticket de OxxoGas · capturado {fmtFecha(t.fecha)}</div>
				</div>

				<div class="info-box">
					<div class="info-label">Relación factura ↔ estación</div>
					{#if t.factura}
						<div class="info-line"><span>🧾 Factura</span><strong>{t.factura}</strong></div>
						{#if t.monto != null}<div class="info-line"><span>Monto</span><strong>{fmtMonto(t.monto)}</strong></div>{/if}
						{#if t.litros != null}<div class="info-line"><span>Litros</span><strong>{Number(t.litros).toFixed(2)} L</strong></div>{/if}
						{#if t.concepto}<div class="info-line"><span>Concepto</span><strong>{t.concepto}</strong></div>{/if}
					{:else}
						<div class="pend-row">⏳ Factura: <strong>Pendiente</strong></div>
					{/if}
					{#if t.estacion}
						<div class="info-line"><span>⛽ Estación</span><strong>{t.estacion}</strong></div>
					{:else}
						<div class="pend-row">⏳ Estación: <strong>Pendiente</strong></div>
					{/if}
				</div>

				<div class="info-box">
					<div class="info-label">Datos del ticket</div>
					{#if t.cliente}<div class="info-line"><span>🏢 Cliente</span><strong>{t.cliente}</strong></div>{/if}
					{#if t.marca_modelo || t.placas}
						<div class="info-line"><span>🚗 Vehículo</span><strong>{[t.marca_modelo, t.placas].filter(Boolean).join(' · ')}</strong></div>
					{/if}
					{#if t.capturo}<div class="info-line"><span>👤 Capturó</span><strong>{t.capturo}</strong></div>{/if}
					{#if t.descripcion}<div class="info-line"><span>📝 Descripción</span><strong>{t.descripcion}</strong></div>{/if}
				</div>

				<button class="btn btn-secondary btn-back" onclick={() => navigate('/tickets_oxxogas')}>⬅️ Volver al listado de tickets</button>
			</div>
		</div>
	{/if}
</div>

<style>
	.page { max-width: 1200px; margin: 0 auto; padding: 1rem; }
	.header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
	.header h1 { font-size: 1.25rem; margin: 0; color: #f1f5f9; }
	.fecha-head { font-size: 0.78rem; color: #94a3b8; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 999px; padding: 0.25rem 0.7rem; }
	.state { text-align: center; color: #94a3b8; padding: 3rem 1rem; font-size: 0.9rem; }
	.state.err { color: #f87171; }

	.grid { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 1.1rem; align-items: start; }
	@media (max-width: 860px) { .grid { grid-template-columns: 1fr; } }

	.img-box { background: #0f172a; border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 14px; overflow: hidden; display: flex; align-items: center; justify-content: center; }
	.img-box img { width: 100%; max-height: 82vh; object-fit: contain; display: block; }
	.no-photo { display: flex; flex-direction: column; align-items: center; gap: 0.4rem; color: #475569; font-size: 3.5rem; padding: 4rem 0; }
	.no-photo span { font-size: 0.8rem; }

	.col { display: flex; flex-direction: column; gap: 0.8rem; }
	.folio-box { background: rgba(255, 174, 0, 0.06); border-color: rgba(255, 174, 0, 0.25); }
	.folio-big { font-family: ui-monospace, 'Cascadia Mono', monospace; font-weight: 800; font-size: 1.7rem; color: #FFAE00; letter-spacing: 1px; }
	.folio-sub { font-size: 0.78rem; color: #94a3b8; margin-top: 0.2rem; }

	.info-box { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 12px; padding: 0.8rem 0.95rem; }
	.info-label { font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.6px; color: #FFAE00; margin-bottom: 0.5rem; }
	.info-line { display: flex; justify-content: space-between; gap: 1rem; font-size: 0.85rem; padding: 0.3rem 0; border-bottom: 1px dashed rgba(255, 255, 255, 0.05); }
	.info-line:last-child { border-bottom: none; }
	.info-line span { color: #94a3b8; flex-shrink: 0; }
	.info-line strong { color: #f1f5f9; text-align: right; font-weight: 600; overflow-wrap: anywhere; }
	.pend-row { font-size: 0.85rem; color: #fbbf24; background: rgba(251, 191, 36, 0.08); border: 1px dashed rgba(251, 191, 36, 0.35); border-radius: 8px; padding: 0.5rem 0.65rem; margin: 0.3rem 0; }
	.btn-back { width: 100%; }
</style>
