<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';

	// REGISTRO DE REPORTES (Admin) — clon del HUB views/registro_reportes.py
	// Lista global de TODOS los reportes, busca, ve detalle, PDF, elimina, sube fotos (máx 6).
	// Permiso: acceso_registro_reportes

	let lista = $state([]);
	let loading = $state(true);
	let error = $state('');
	let msg = $state('');
	let busqueda = $state('');
	let busy = $state(false);

	let selReporte = $state(null);
	let fotosSubiendo = $state([]);
	let fotosPreview = $state([]);
	let maxFotos = 6;

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
		selReporte = r;
		fotosSubiendo = [];
		fotosPreview = [];
	}

	async function verPDF() {
		if (!selReporte) return;
		const token = auth.getToken();
		window.open(`/api/reportes/${selReporte.IdReporte}/pdf?token=${encodeURIComponent(token)}`, '_blank');
	}

	async function eliminar() {
		if (!selReporte) return;
		if (!confirm(`¿Eliminar el reporte ${selReporte.Folio}? Esta acción no se puede deshacer.`)) return;
		error = '';
		msg = '';
		busy = true;
		try {
			const res = await fetch(`/api/reportes/${selReporte.IdReporte}`, { method: 'DELETE', headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al eliminar.');
			msg = '✅ Reporte eliminado.';
			selReporte = null;
			await cargar();
		} catch (e) {
			error = e.message || 'Error al eliminar.';
		} finally {
			busy = false;
		}
	}

	// Fotos
	async function handleFotosSelect(e) {
		const files = Array.from(e.target.files || []);
		const existentes = await getFotos(selReporte.IdReporte);
		const actuales = existentes.length;
		const hueco = maxFotos - actuales;
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

	async function getFotos(idReporte) {
		try {
			const res = await fetch(`/api/reportes/${idReporte}/fotos`, { headers: auth.authHeader() });
			return res.ok ? await res.json() : [];
		} catch { return []; }
	}

	async function guardarFotos() {
		if (!selReporte || fotosSubiendo.length === 0) return;
		error = '';
		msg = '';
		busy = true;
		try {
			// Obtener fotos existentes para conservar orden
			const existentes = await getFotos(selReporte.IdReporte);
			const todas = existentes.map(f => ({ base64: f.base64, orden: f.orden }))
				.concat(fotosSubiendo.map((b, i) => ({ base64: b, orden: (existentes.length || 0) + i + 1 })));
			const res = await fetch(`/api/reportes/${selReporte.IdReporte}/fotos`, {
				method: 'POST',
				headers: apiHeaders(),
				body: JSON.stringify({ fotos: todas.map(f => f.base64) })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error guardando fotos.');
			msg = `🎉 ${fotosSubiendo.length} foto(s) guardada(s).`;
			fotosSubiendo = [];
			fotosPreview = [];
			await cargar();
			// Recargar fotos del reporte seleccionado
			const fotos = await getFotos(selReporte.IdReporte);
			selReporte = { ...selReporte, _fotos: fotos };
		} catch (e) {
			error = e.message || 'Error guardando fotos.';
		} finally {
			busy = false;
		}
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

	<!-- Detalle -->
	{#if selReporte}
		<div class="modal-overlay" on:click={() => selReporte = null}>
			<div class="modal" on:click={(e) => e.stopPropagation()}>
				<div class="modal-header">
					<h3>📋 Detalle del Reporte: <span style="color:var(--color-primary-light);">{selReporte.Folio}</span></h3>
					<button class="btn btn-sm btn-ghost" on:click={() => selReporte = null}>✕</button>
				</div>
				<div class="modal-body">
					<div class="grid-2" style="font-size: 0.9rem;">
						<div><strong>Cliente:</strong> <code>{selReporte.Cliente}</code></div>
						<div><strong>Contacto:</strong> {selReporte.Contacto || 'N/A'}</div>
						<div><strong>Correo Contacto:</strong> {selReporte.CorreoContacto || 'N/A'}</div>
						<div><strong>Cotización Asociada:</strong> {selReporte.Cotizacion || '*Sin cotización vinculada*'}</div>
						<div><strong>Estatus:</strong> {@html estatusHtml(selReporte.Estatus)}</div>
						<div><strong>Inicio:</strong> {formatearFecha(selReporte.FechaHoraInicio)}</div>
						<div><strong>Fin:</strong> {formatearFecha(selReporte.FechaHoraFin)}</div>
						<div><strong>Traslado:</strong> {selReporte.TiempoTraslado || 0} h</div>
						<div><strong>Comida:</strong> {selReporte.TiempoComida ? 'Sí' : 'No'}</div>
						<div><strong>Técnico:</strong> <strong>{selReporte.Tecnico}</strong></div>
						<div><strong>Máquina/Línea:</strong> {selReporte.MaquinaLinea || '—'}</div>
					</div>

					<hr style="border-color: var(--color-border); margin: 0.75rem 0;" />

					<div><strong>🛠️ Descripción del Servicio:</strong></div>
					<div class="info-box" style="margin-top: 0.25rem;">{selReporte.DescripcionServicio || '*Sin descripción registrada.*'}</div>

					{#if selReporte.Notas}
						<div style="margin-top: 0.75rem;"><strong>📝 Notas:</strong></div>
						<div class="info-box" style="margin-top: 0.25rem;">{selReporte.Notas}</div>
					{/if}

					{#if selReporte.FirmaConformidad}
						<div style="margin-top: 0.75rem;"><strong>✍️ Firma de Conformidad:</strong></div>
						<img src="data:image/png;base64,{selReporte.FirmaConformidad}" alt="Firma" style="margin-top: 0.25rem; max-width: 280px; border: 1px solid var(--color-border); border-radius: 8px;" />
					{/if}

					<hr style="border-color: var(--color-border); margin: 0.75rem 0;" />

					<div><strong>📸 Evidencia Fotográfica ({selReporte._fotos?.length || 0}/6):</strong></div>

					{#if (selReporte._fotos?.length || 0) < maxFotos}
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

					{#if selReporte._fotos && selReporte._fotos.length > 0}
						<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 0.5rem; margin-top: 0.5rem;">
							{#each selReporte._fotos as f}
								<div style="position: relative; border: 1px solid var(--color-border); border-radius: 8px; overflow: hidden;">
									<img src="data:image/jpeg;base64,{f.base64}" alt="Foto {f.orden}" style="width: 100%; aspect-ratio: 4/3; object-fit: cover;" />
									<span class="badge" style="position: absolute; top: 4px; left: 4px; font-size: 0.7rem;">#{f.orden}</span>
								</div>
							{/each}
						</div>
					{/if}

					<hr style="border-color: var(--color-border); margin: 0.75rem 0;" />

					<div class="grid-3">
						<button class="btn btn-primary btn-sm" on:click={verPDF}>🔓 Ver PDF</button>
						<button class="btn btn-danger btn-sm" on:click={eliminar} disabled={busy}>🚨 Eliminar Reporte</button>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.subtitle { color: #94A3B8; font-size: 0.9rem; font-weight: 400; margin: 0; }
	.msg { padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 0.75rem; }
	.msg.err { background: rgba(239,68,68,0.1); color: #EF4444; }
	.msg.ok { background: rgba(34,197,94,0.1); color: #22C55E; }
	.info-box { padding: 0.75rem; background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid var(--color-border); white-space: pre-wrap; font-size: 0.85rem; }
	.badge { padding: 0.1rem 0.5rem; border-radius: 12px; font-weight: 600; font-size: 0.7rem; color: #fff; }
	.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 1rem; overflow: auto; }
	.modal { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 16px; max-width: 700px; width: 100%; max-height: 90vh; overflow: auto; }
	.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-bottom: 1px solid var(--color-border); }
	.modal-header h3 { margin: 0; font-size: 1.1rem; }
	.modal-body { padding: 1rem; }
	.btn-ghost { background: transparent; border: none; color: var(--color-text-muted); cursor: pointer; }
</style>