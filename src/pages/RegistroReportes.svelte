<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { online } from '$lib/stores/online.js';

	// REGISTRO DE REPORTES (Admin) — clon del HUB views/registro_reportes.py
	// Lista global de TODOS los reportes, busca, ve detalle, PDF, elimina, sube fotos (máx 6).
	// Permiso: acceso_registro_reportes

	let lista = $state([]);
	let loading = $state(true);
	let error = $state('');
	let msg = $state('');
	let busqueda = $state('');
	let busy = $state(false);

	function tieneAcceso() {
		try {
			const u = JSON.parse(localStorage.getItem('admon_user') || 'null');
			return !!(u && u.acceso_registro_reportes);
		} catch {
			return false;
		}
	}

	function apiHeaders() {
		return { 'Content-Type': 'application/json', ...auth.authHeader() };
	}

	let filtrados = $derived(
		lista.filter((r) => {
			const q = busqueda.trim().toLowerCase();
			if (!q) return true;
			return String(r.Folio || '').toLowerCase().includes(q) ||
				   String(r.Cliente || '').toLowerCase().includes(q) ||
				   String(r.Tecnico || '').toLowerCase().includes(q) ||
				   String(r.Contacto || '').toLowerCase().includes(q) ||
				   String(r.Cotizacion || '').toLowerCase().includes(q);
		})
	);

	// Solo firmados (como el HUB)
	let firmados = $derived(filtrados.filter(r => r.FirmaConformidad && String(r.FirmaConformidad).trim() !== ''));

	async function cargar() {
		loading = true;
		error = '';
		try {
			const res = await fetch('/api/reportes', { headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al cargar.');
			lista = data || [];
		} catch (e) {
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

	function formatearFecha(val) {
		if (!val) return 'Sin registrar';
		const d = new Date(val);
		if (isNaN(d)) return String(val);
		return d.toLocaleString('es-MX', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
	}

	function estatusHtml(est) {
		const v = String(est || 'Borrador');
		if (v === 'Borrador') return `<span class="badge" style="background:#475569;">📝 Borrador</span>`;
		if (v === 'Completado') return `<span class="badge" style="background:#0EA5E9;">🔵 Completado</span>`;
		if (v === 'Firmado') return `<span class="badge" style="background:#10B981;">🟢 Firmado</span>`;
		return `<span class="badge">${v}</span>`;
	}

	function verDetalle(r) {
		navigate(`/registro_reportes/${r.IdReporte}`);
	}
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/dashboard')} title="Volver">⬅️</button>
		<h1>📋 Registro de Reportes</h1>
		<p class="subtitle">Visualización global de reportes de servicio técnico de todos los ingenieros.</p>
		<div style="flex:1"></div>
		<button class="btn btn-sm btn-secondary" on:click={cargar} title="Sincronizar">🔄</button>
	</div>

	<input class="input" placeholder="Buscar por cliente, folio, técnico, contacto, cotización…" bind:value={busqueda} style="margin-bottom: 0.75rem;" />

	{#if !$online}
		<div class="card" style="margin-bottom: 0.75rem; border-color: rgba(239,68,68,0.4);">
			<p style="margin: 0; font-size: 0.85rem;">🔴 Lista maestra: requiere conexión.</p>
		</div>
	{/if}

	{#if loading}
		<div class="empty">Cargando…</div>
	{:else if firmados.length === 0}
		<div class="empty">No hay reportes firmados registrados.</div>
	{:else}
		<p style="color: var(--color-text-muted); font-size: 0.8rem; margin-bottom: 0.5rem;">
			Mostrando <strong>{firmados.length}</strong> de <strong>{lista.length}</strong> reportes globales (solo firmados).
		</p>

		<div class="list">
			{#each firmados as r (r.IdReporte)}
				<button class="list-card" on:click={() => verDetalle(r)}>
					<div style="flex: 1;">
						<div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
							<span style="font-weight: 800; color: var(--color-primary-light);">{r.Folio}</span>
							{@html estatusHtml(r.Estatus)}
						</div>
						<div style="font-size: 0.9rem; margin-top: 0.15rem;">{r.Cliente}</div>
						<div style="font-size: 0.75rem; color: var(--color-text-muted);">
							{r.Tecnico} · {formatearFecha(r.FechaHoraInicio)} · {r.MaquinaLinea || '—'}
						</div>
					</div>
					<div style="text-align: right; font-size: 0.75rem; color: var(--color-text-muted);">
						Cot: {r.Cotizacion || '—'}
					</div>
				</button>
			{/each}
		</div>
	{/if}

	{#if error}
		<div class="msg err">{error}</div>
	{/if}
	{#if msg}
		<div class="msg ok">{msg}</div>
	{/if}
</div>

<style>
	.subtitle { color: #94A3B8; font-size: 0.9rem; font-weight: 400; margin: 0; }
	.msg { padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 0.75rem; }
	.msg.err { background: rgba(239,68,68,0.1); color: #EF4444; }
	.msg.ok { background: rgba(34,197,94,0.1); color: #22C55E; }
	.badge { padding: 0.1rem 0.5rem; border-radius: 12px; font-weight: 600; font-size: 0.7rem; color: #fff; }
</style>