<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { online } from '$lib/stores/online.js';

	// Detalle completo de reporte (pantalla completa, sin modales)
	// Permiso: acceso_registro_reportes

	let { id } = $props();
	const idReporte = Number(id);

	let loading = $state(true);
	let error = $state('');
	let msg = $state('');
	let busy = $state(false);

	let reporte = $state({});
	let fotosSubiendo = $state([]);
	let fotosPreview = $state([]);
	const maxFotos = 6;

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

	async function cargar() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`/api/reportes/${idReporte}`, { headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al cargar.');
			reporte = data;

			// Cargar fotos
			const fRes = await fetch(`/api/reportes/${idReporte}/fotos`, { headers: auth.authHeader() });
			const fotos = fRes.ok ? await fRes.json() : [];
			reporte._fotos = fotos || [];
		} catch (e) {
			error = e.message === 'Sesión expirada' ? e.message : `Error: ${e.message}`;
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

	async function verPDF() {
		const token = auth.getToken();
		window.open(`/api/reportes/${idReporte}/pdf?token=${encodeURIComponent(token)}`, '_blank');
	}

	async function eliminar() {
		if (!confirm(`¿Eliminar el reporte ${reporte.Folio}? Esta acción no se puede deshacer.`)) return;
		error = '';
		msg = '';
		busy = true;
		try {
			const res = await fetch(`/api/reportes/${idReporte}`, { method: 'DELETE', headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al eliminar.');
			navigate('/registro_reportes', { replace: true });
		} catch (e) {
			error = e.message || 'Error al eliminar.';
			busy = false;
		}
	}

	// Fotos
	async function handleFotosSelect(e) {
		const files = Array.from(e.target.files || []);
		const existentes = reporte._fotos?.length || 0;
		const hueco = maxFotos - existentes;
		if (hueco <= 0) { error = 'Ya tiene 6 fotos (máximo).'; return; }
		const permitidos = files.slice(0, hueco);
		for (const f of permitidos) {
			if (!f.type.startsWith('image/')) continue;
			if (f.size > 5 * 1024 * 1024) continue;
			const reader = new FileReader();
			reader.onload = () => {
				fotosSubiendo.push(reader.result.split(',')[1]);
				fotosPreview.push(reader.result);
			};
			reader.readAsDataURL(f);
		}
		if (files.length > hueco) error = `Solo se permiten ${hueco} fotos más (máx 6).`;
	}

	async function guardarFotos() {
		if (fotosSubiendo.length === 0) return;
		error = '';
		msg = '';
		busy = true;
		try {
			const existentes = reporte._fotos || [];
			const todas = existentes.map(f => f.base64)
				.concat(fotosSubiendo);
			const res = await fetch(`/api/reportes/${idReporte}/fotos`, {
				method: 'POST',
				headers: apiHeaders(),
				body: JSON.stringify({ fotos: todas })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error guardando fotos.');
			msg = `🎉 ${fotosSubiendo.length} foto(s) guardada(s).`;
			fotosSubiendo = [];
			fotosPreview = [];
			await cargar();
		} catch (e) {
			error = e.message || 'Error guardando fotos.';
		} finally {
			busy = false;
		}
	}
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/registro_reportes')} title="Volver">⬅️</button>
		<h1>📋 {reporte.Folio || 'Cargando…'}</h1>
	</div>

	{#if loading}
		<div class="empty">Cargando…</div>
	{:else}
		{#if error}
			<div class="msg err">{error}</div>
		{/if}
		{#if msg}
			<div class="msg ok">{msg}</div>
		{/if}

		<!-- Datos principales -->
		<div class="card" style="margin-bottom: 0.75rem;">
			<div class="card-title">📄 Datos del reporte</div>

			<div class="grid-2" style="font-size: 0.9rem;">
				<div><strong>Folio:</strong> {reporte.Folio}</div>
				<div><strong>Estatus:</strong> {@html estatusHtml(reporte.Estatus)}</div>
				<div><strong>Cliente:</strong> {reporte.Cliente}</div>
				<div><strong>Fecha:</strong> {formatearFecha(reporte.Fecha)}</div>
				<div><strong>Contacto:</strong> {reporte.Contacto || 'N/A'}</div>
				<div><strong>Correo:</strong> {reporte.CorreoContacto || 'N/A'}</div>
				<div><strong>Cotización Asociada:</strong> {reporte.Cotizacion || '*Sin cotización vinculada*'}</div>
				<div><strong>Técnico:</strong> <strong>{reporte.Tecnico}</strong></div>
				<div><strong>Máquina/Línea:</strong> {reporte.MaquinaLinea || '—'}</div>
				<div><strong>Inicio:</strong> {formatearFecha(reporte.FechaHoraInicio)}</div>
				<div><strong>Fin:</strong> {formatearFecha(reporte.FechaHoraFin)}</div>
				<div><strong>Traslado:</strong> {reporte.TiempoTraslado || 0} h</div>
				<div><strong>Comida:</strong> {reporte.TiempoComida ? 'Sí' : 'No'}</div>
			</div>

			<hr style="border-color: var(--color-border); margin: 0.75rem 0;" />

			<div><strong>🛠️ Descripción del Servicio:</strong></div>
			<div class="info-box" style="margin-top: 0.25rem;">{reporte.DescripcionServicio || '*Sin descripción registrada.*'}</div>

			{#if reporte.Notas}
				<div style="margin-top: 0.75rem;"><strong>📝 Notas:</strong></div>
				<div class="info-box" style="margin-top: 0.25rem;">{reporte.Notas}</div>
			{/if}

			{#if reporte.FirmaConformidad}
				<div style="margin-top: 0.75rem;"><strong>✍️ Firma de Conformidad:</strong></div>
				<img src="data:image/png;base64,{reporte.FirmaConformidad}" alt="Firma" style="margin-top: 0.25rem; max-width: 280px; border: 1px solid var(--color-border); border-radius: 8px;" />
			{/if}
		</div>

		<!-- Fotos -->
		<div class="card" style="margin-bottom: 0.75rem;">
			<div class="card-title">📸 Evidencia Fotográfica ({(reporte._fotos?.length || 0)}/6)</div>

			{#if (reporte._fotos?.length || 0) < maxFotos}
				<input type="file" accept="image/*" multiple on:change={handleFotosSelect} class="input" style="margin: 0.5rem 0;" />
				{#if fotosPreview.length > 0}
					<div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem;">
						{#each fotosPreview as p}
							<img src={p} alt="Preview" style="width: 100px; height: 100px; object-fit: cover; border-radius: 8px; border: 1px solid var(--color-border);" />
						{/each}
					</div>
					<button class="btn btn-primary btn-sm" on:click={guardarFotos} disabled={busy}>💾 Guardar Fotos</button>
				{/if}
			{:else}
				<p style="font-size: 0.85rem; color: var(--color-text-muted); margin-top: 0.5rem;">ℹ️ Este reporte ya tiene el máximo de 6 fotos.</p>
			{/if}

			{#if reporte._fotos && reporte._fotos.length > 0}
				<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 0.5rem; margin-top: 0.5rem;">
					{#each reporte._fotos as f}
						<div style="position: relative; border: 1px solid var(--color-border); border-radius: 8px; overflow: hidden;">
							<img src="data:image/jpeg;base64,{f.base64}" alt="Foto {f.orden}" style="width: 100%; aspect-ratio: 4/3; object-fit: cover;" />
							<span class="badge" style="position: absolute; top: 4px; left: 4px; font-size: 0.7rem;">#{f.orden}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Acciones -->
		<div class="card">
			<div class="grid-2">
				<button class="btn btn-primary btn-block" on:click={verPDF}>🔓 Ver PDF</button>
				<button class="btn btn-danger btn-block" on:click={eliminar} disabled={busy}>🚨 Eliminar Reporte</button>
			</div>
		</div>
	{/if}
</div>

<style>
	.card-title { font-weight: 700; font-size: 1rem; margin-bottom: 0.25rem; }
	.msg { padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 0.75rem; }
	.msg.err { background: rgba(239,68,68,0.1); color: #EF4444; }
	.msg.ok { background: rgba(34,197,94,0.1); color: #22C55E; }
	.info-box { padding: 0.75rem; background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid var(--color-border); white-space: pre-wrap; font-size: 0.85rem; }
	.badge { padding: 0.1rem 0.5rem; border-radius: 12px; font-weight: 600; font-size: 0.7rem; color: #fff; }
</style>