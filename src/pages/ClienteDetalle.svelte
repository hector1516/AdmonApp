<script>
	import { onMount } from 'svelte';
	import { navigate } from '$lib/router.js';
	import { auth } from '$lib/stores/auth.js';
	import { clientes, clienteContactos } from '$lib/cotizacionesApi.js';

	// Detalle de cliente como el HUB + administración de sus contactos.
	// Los contactos son historial en las cotizaciones: editar = renombrar
	// en todas las cotizaciones del cliente.

	let { id } = $props();
	const idCliente = String(id || '').toUpperCase();

	let loading = $state(true);
	let error = $state('');
	let msg = $state('');
	let busy = $state(false);

	let nombre = $state('');
	let dias = $state(30);
	let contactos = $state([]);
	let editandoContacto = $state(null);
	let nuevoNombreContacto = $state('');

	function tieneAcceso() {
		try {
			const u = JSON.parse(localStorage.getItem('admon_user') || 'null');
			return !!(u && u.acceso_cotizaciones);
		} catch {
			return false;
		}
	}

	function apiHeaders() {
		return { 'Content-Type': 'application/json', ...auth.authHeader() };
	}

	async function cargarContactos() {
		try {
			contactos = await clienteContactos(idCliente);
		} catch {
			contactos = [];
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
			const lista = await clientes();
			const c = lista.find((x) => String(x.id_cliente || '').toUpperCase() === idCliente);
			if (!c) throw new Error('Cliente no encontrado.');
			nombre = c.nombre || '';
			dias = c.dias_pago ?? 30;
			await cargarContactos();
		} catch (e) {
			error = e.message === 'Sesión expirada' ? e.message : `No se pudo cargar (${e.message || 'sin conexión'}).`;
		} finally {
			loading = false;
		}
	});

	async function guardar() {
		if (!nombre.trim()) {
			error = 'La razón social no puede estar vacía.';
			return;
		}
		error = '';
		msg = '';
		busy = true;
		try {
			const res = await fetch(`/api/clientes/${idCliente}`, {
				method: 'PUT',
				headers: apiHeaders(),
				body: JSON.stringify({ nombre: nombre.trim(), dias_pago: parseInt(dias, 10) || 0 })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al actualizar.');
			msg = '✅ Cliente actualizado.';
		} catch (e) {
			error = e.message || 'Error al actualizar.';
		} finally {
			busy = false;
		}
	}

	async function eliminar() {
		if (!confirm(`¿Eliminar al cliente ${idCliente}? Si tiene cotizaciones asociadas no se podrá.`)) return;
		error = '';
		msg = '';
		busy = true;
		try {
			const res = await fetch(`/api/clientes/${idCliente}`, { method: 'DELETE', headers: auth.authHeader() });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al eliminar.');
			navigate('/clientes', { replace: true });
		} catch (e) {
			error = e.message || 'Error al eliminar.';
			busy = false;
		}
	}

	function empezarRenombre(c) {
		msg = '';
		error = '';
		editandoContacto = c;
		nuevoNombreContacto = c;
	}

	async function guardarRenombre() {
		const nuevo = nuevoNombreContacto.trim();
		if (!nuevo) {
			error = 'El nombre no puede estar vacío.';
			return;
		}
		if (nuevo === editandoContacto) {
			editandoContacto = null;
			return;
		}
		error = '';
		msg = '';
		busy = true;
		try {
			const res = await fetch(`/api/clientes/${idCliente}/contactos`, {
				method: 'PUT',
				headers: apiHeaders(),
				body: JSON.stringify({ anterior: editandoContacto, nuevo })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || 'Error al renombrar.');
			msg = `✅ Contacto actualizado en ${data.actualizados ?? 0} cotización(es).`;
			editandoContacto = null;
			await cargarContactos();
		} catch (e) {
			error = e.message || 'Error al renombrar. Revisa tu conexión (requiere red).';
		} finally {
			busy = false;
		}
	}
</script>

<div class="page">
	<div class="header">
		<button class="btn btn-sm btn-secondary" on:click={() => navigate('/clientes')} title="Volver">⬅️</button>
		<h1>📇 {idCliente}</h1>
	</div>

	{#if loading}
		<div class="empty">Cargando…</div>
	{:else}
		<div class="card" style="margin-bottom: 0.75rem;">
			<div class="card-title">✏️ Datos del cliente</div>
			<div class="field">
				<label for="cd-nombre">Razón social:</label>
				<input id="cd-nombre" class="input" bind:value={nombre} />
			</div>
			<div class="field">
				<label for="cd-dias">Días de pago:</label>
				<input id="cd-dias" type="number" class="input" min="0" bind:value={dias} />
			</div>
			<div class="grid-2" style="margin-bottom: 0.5rem;">
				<button class="btn btn-secondary btn-block" on:click={() => navigate('/clientes')}>❌ Cancelar</button>
				<button class="btn btn-primary btn-block" on:click={guardar} disabled={busy}>💾 Guardar</button>
			</div>
			<button class="btn btn-danger btn-block" on:click={eliminar} disabled={busy}>🚨 Eliminar cliente</button>
		</div>

		<div class="card">
			<div class="card-title">👥 Contactos del cliente ({contactos.length})</div>
			<p class="hint">Del historial de sus cotizaciones. Editar renombra el contacto en todas.</p>
			{#if contactos.length === 0}
				<p style="font-size: 0.85rem; color: var(--color-text-muted);">Sin contactos registrados.</p>
			{:else}
				<div class="list">
					{#each contactos as c}
						<div class="list-card" style="cursor: default;">
							{#if editandoContacto === c}
								<input
									class="input"
									bind:value={nuevoNombreContacto}
									placeholder="Nuevo nombre…"
									style="flex: 1;"
								/>
								<div style="display: flex; gap: 0.4rem; flex-shrink: 0;">
									<button class="btn btn-sm btn-secondary" on:click={() => (editandoContacto = null)}>❌</button>
									<button class="btn btn-sm btn-primary" on:click={guardarRenombre} disabled={busy}>💾</button>
								</div>
							{:else}
								<span style="flex: 1;">{c}</span>
								<button class="btn btn-sm btn-secondary" on:click={() => empezarRenombre(c)} title="Renombrar">✏️</button>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>

		{#if error}
			<div class="msg err" style="margin-top: 0.75rem;">{error}</div>
		{/if}
		{#if msg}
			<div class="msg ok" style="margin-top: 0.75rem;">{msg}</div>
		{/if}
	{/if}
</div>

<style>
	.card-title { font-weight: 700; font-size: 1rem; margin-bottom: 0.25rem; }
	.hint { font-size: 0.8rem; color: var(--color-text-muted); }
	.msg { padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 0.75rem; }
	.msg.err { background: rgba(239,68,68,0.1); color: #EF4444; }
	.msg.ok { background: rgba(34,197,94,0.1); color: #22C55E; }
	.card { margin-bottom: 0.75rem; }
</style>
