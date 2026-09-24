<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { online } from '$lib/stores/online.js';

	// REGISTRO DE REPORTES (Admin) — clon del HUB views/registro_reportes.py
	// Lista global con pestañas: Firmados / Papelera (eliminados)
	// Permiso: acceso_registro_reportes

	let lista = $state([]);
	let loading = $state(true);
	let error = $state('');
	let msg = $state('');
	let busqueda = $state('');
	let busy = $state(false);
	let tab = $state('firmados'); // 'firmados' | 'papelera'

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

	// Tab firmados: solo firmados (FirmaConformidad no vacío) y no eliminados
	let firmados = $derived(filtrados.filter(r => 
		r.FirmaConformidad && String(r.FirmaConformidad).trim() !== '' && 
		(r.Eliminado === 0 || r.Eliminado === false || r.Eliminado === null || r.Eliminado === undefined)
	));

	// Tab papelera: eliminados (Eliminado = 1)
	let papelera = $derived(filtrados.filter(r => r.Eliminado === 1 || r.Eliminado === true));

	async function cargar() {
		loading = true;
		error = '';
		try {
			const params = new URLSearchParams();
			if (tab === 'papelera') params.set('eliminados', 'true');
			const res = await fetch(`/api/reportes?${params}`, { headers: auth.authHeader() });
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
		if (v === 'Cancelado') return `<span class="badge" style="background:#EF4444;">🔴 Cancelado</span>`;
		return `<span class="badge">${v}</span>`;
	}

	function verDetalle(r) {
		navigate(`/registro_reportes/${r.IdReporte}`);
	}

	async function moverAPapelera(r) {
		const folio = r.Folio;
		if (!confirm(`¿Mover a PAPELERA el reporte ${folio}?\n\nSe ocultará de la lista principal pero se podrá restaurar desde la pestaña "Papelera".\n\n¿Continuar?`)) return;
		error = '';
		msg = '';
		busy = true;
		try {
			const res = await fetch(`/api/reportes/${r.IdReporte}`, { method: 'DELETE', headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al mover a papelera.');
			msg = `🗑️ ${folio} movido a papelera.`;
			await cargar();
		} catch (e) {
			error = e.message || 'Error al mover a papelera.';
		} finally {
			busy = false;
		}
	}

	async function restaurar(r) {
		const folio = r.Folio;
		if (!confirm(`¿RESTAURAR el reporte ${folio}?\n\nVolverá a la lista de "Firmados".`)) return;
		error = '';
		msg = '';
		busy = true;
		try {
			const res = await fetch(`/api/reportes/${r.IdReporte}/restaurar`, { method: 'POST', headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al restaurar.');
			msg = `✅ ${folio} restaurado.`;
			await cargar();
		} catch (e) {
			error = e.message || 'Error al restaurar.';
		} finally {
			busy = false;
		}
	}

	async function eliminarDefinitivo(r) {
		const folio = r.Folio;
		if (!confirm(`⚠️ ELIMINACIÓN PERMANENTE ⚠️\n\n¿Borrar DEFINITIVAMENTE el reporte ${folio}?\n\n❌ NO SE PUEDE DESHACER\n❌ Se borran fotos, técnicos y todo el historial\n\nEscribe "ELIMINAR" para confirmar:`)) return;
		const input = prompt('Escribe "ELIMINAR" para confirmar borrado permanente:');
		if (input !== 'ELIMINAR') return;
		error = '';
		msg = '';
		busy = true;
		try {
			const res = await fetch(`/api/reportes/${r.IdReporte}/purge`, { method: 'DELETE', headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al eliminar permanentemente.');
			msg = `💀 ${folio} eliminado permanentemente.`;
			await cargar();
		} catch (e) {
			error = e.message || 'Error al eliminar permanentemente.';
		} finally {
			busy = false;
		}
	}

	function cambiarTab(nuevoTab) {
		tab = nuevoTab;
		cargar();
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

	<!-- Tabs -->
	<div class="tabs" style="margin-bottom: 0.75rem; display: flex; gap: 0.25rem; border-bottom: 1px solid var(--color-border);">
		<button 
			class="tab-btn" 
			class:active={tab === 'firmados'}
			on:click={() => cambiarTab('firmados')}
			style="padding: 0.5rem 1rem; border: none; background: transparent; color: var(--color-text); font-weight: 600; border-bottom: 2px solid transparent; cursor: pointer;"
		>
			🟢 Firmados ({firmados.length})
		</button>
		<button 
			class="tab-btn" 
			class:active={tab === 'papelera'}
			on:click={() => cambiarTab('papelera')}
			style="padding: 0.5rem 1rem; border: none; background: transparent; color: var(--color-text); font-weight: 600; border-bottom: 2px solid transparent; cursor: pointer;"
		>
			🗑️ Papelera ({papelera.length})
		</button>
	</div>

	{#if loading}
		<div class="empty">Cargando…</div>
	{:else if (tab === 'firmados' ? firmados : papelera).length === 0}
		<div class="empty">
			{#if tab === 'firmados'}
				No hay reportes firmados registrados.
			{:else}
				Papelera vacía.
			{/if}
		</div>
	{:else}
		<p style="color: var(--color-text-muted); font-size: 0.8rem; margin-bottom: 0.5rem;">
			Mostrando <strong>{(tab === 'firmados' ? firmados : papelera).length}</strong> de <strong>{lista.length}</strong> reportes globales.
		</p>

		<div class="list">
			{#each (tab === 'firmados' ? firmados : papelera) as r (r.IdReporte)}
				<button class="list-card" on:click={() => verDetalle(r)}>
					<div style="flex: 1;">
						<div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
							<span style="font-weight: 800; color: var(--color-primary-light);">{r.Folio}</span>
							{@html estatusHtml(r.Estatus)}
							{#if r.Eliminado === 1 || r.Eliminado === true}
								<span class="badge" style="background:#EF4444;">🗑️ Papelera</span>
							{/if}
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
	.tab-btn.active { color: var(--color-primary-light); border-bottom-color: var(--color-primary-light); }
	.tab-btn:hover:not(.active) { color: var(--color-text-muted); }
</style>